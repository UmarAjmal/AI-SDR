import os
import time
import asyncio
import logging
import urllib.parse
from typing import Optional, Any
import httpx

from packages.crm.base import (
    CRMProvider,
    TokenBundle,
    ContactBatch,
    CanonicalContact,
    WebhookEvent
)
from packages.crm.normalizer import LeadNormalizer

logger = logging.getLogger("codenter.crm.hubspot")

class HubSpotRateLimiter:
    """
    Token-bucket rate limiter enforcing HubSpot standard limit (100 requests per 10 seconds).
    """
    def __init__(self, max_tokens: int = 100, refill_time: float = 10.0):
        self.max_tokens = max_tokens
        self.refill_time = refill_time
        self.tokens = float(max_tokens)
        self.last_update = time.monotonic()
        self.lock = asyncio.Lock()

    async def acquire(self):
        async with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.tokens = min(self.max_tokens, self.tokens + (elapsed * (self.max_tokens / self.refill_time)))
            self.last_update = now

            if self.tokens < 1.0:
                sleep_needed = (1.0 - self.tokens) * (self.refill_time / self.max_tokens)
                logger.warning(f"HubSpot rate limit approaching; throttling for {sleep_needed:.2f}s")
                await asyncio.sleep(sleep_needed)
                self.tokens = 1.0
                self.last_update = time.monotonic()

            self.tokens -= 1.0

class HubSpotProvider(CRMProvider):
    AUTH_URL = "https://app.hubspot.com/oauth/authorize"
    TOKEN_URL = "https://api.hubapi.com/oauth/v1/token"
    BASE_API = "https://api.hubapi.com/crm/v3"

    DEFAULT_SCOPES = [
        "crm.objects.contacts.read",
        "crm.objects.contacts.write",
        "crm.schemas.contacts.read",
    ]

    CONTACT_PROPERTIES = [
        "firstname", "lastname", "email", "phone", "mobilephone", "jobtitle",
        "company", "domain", "website", "industry", "numberofemployees", "numemployees",
        "city", "state", "country", "annualrevenue", "lifecyclestage", "hs_lead_status",
        "hs_email_optout", "hubspot_owner_id", "notes_last_contacted"
    ]

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        mock_client: httpx.AsyncClient | None = None
    ):
        self.client_id = client_id or os.getenv("HUBSPOT_CLIENT_ID", "mock-hubspot-client-id")
        self.client_secret = client_secret or os.getenv("HUBSPOT_CLIENT_SECRET", "mock-hubspot-client-secret")
        self.mock_client = mock_client
        self.rate_limiter = HubSpotRateLimiter()

    def get_auth_url(self, state: str, redirect_uri: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(self.DEFAULT_SCOPES),
            "state": state
        }
        return f"{self.AUTH_URL}?{urllib.parse.urlencode(params)}"

    async def exchange_code(self, code: str, redirect_uri: str) -> TokenBundle:
        data = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": redirect_uri,
            "code": code
        }
        client = self.mock_client or httpx.AsyncClient(timeout=15.0)
        owns_client = self.mock_client is None

        try:
            await self.rate_limiter.acquire()
            resp = await client.post(self.TOKEN_URL, data=data)
            resp.raise_for_status()
            res = resp.json()

            # Optional: decode portal ID or account ID if provided
            account_id = str(res.get("hub_id") or res.get("portal_id") or "")
            account_name = f"HubSpot Portal {account_id}" if account_id else "HubSpot Account"

            return TokenBundle(
                access_token=res["access_token"],
                refresh_token=res["refresh_token"],
                expires_in=res.get("expires_in", 21600),
                token_type=res.get("token_type", "Bearer"),
                account_id=account_id,
                account_name=account_name
            )
        finally:
            if owns_client:
                await client.aclose()

    async def refresh_tokens(self, refresh_token: str) -> TokenBundle:
        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token
        }
        client = self.mock_client or httpx.AsyncClient(timeout=15.0)
        owns_client = self.mock_client is None

        try:
            await self.rate_limiter.acquire()
            resp = await client.post(self.TOKEN_URL, data=data)
            resp.raise_for_status()
            res = resp.json()

            return TokenBundle(
                access_token=res["access_token"],
                refresh_token=res.get("refresh_token", refresh_token),
                expires_in=res.get("expires_in", 21600),
                token_type=res.get("token_type", "Bearer")
            )
        finally:
            if owns_client:
                await client.aclose()

    async def fetch_contacts(
        self,
        access_token: str,
        cursor: Optional[str] = None,
        limit: int = 100
    ) -> ContactBatch:
        url = f"{self.BASE_API}/objects/contacts"
        params: dict[str, Any] = {
            "limit": limit,
            "properties": ",".join(self.CONTACT_PROPERTIES)
        }
        if cursor:
            params["after"] = cursor

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        client = self.mock_client or httpx.AsyncClient(timeout=20.0)
        owns_client = self.mock_client is None

        try:
            await self.rate_limiter.acquire()
            resp = await client.get(url, params=params, headers=headers)
            
            # Handle rate limit retry
            if resp.status_code == 429:
                retry_after = float(resp.headers.get("Retry-After", 2.0))
                logger.warning(f"HubSpot 429 rate limit reached. Waiting {retry_after}s before retry.")
                await asyncio.sleep(retry_after)
                resp = await client.get(url, params=params, headers=headers)

            resp.raise_for_status()
            data = resp.json()

            raw_results = data.get("results", [])
            contacts: list[CanonicalContact] = []
            for item in raw_results:
                contacts.append(LeadNormalizer.normalize_hubspot_contact(item))

            paging = data.get("paging", {})
            next_cursor = paging.get("next", {}).get("after")
            has_more = next_cursor is not None

            return ContactBatch(
                contacts=contacts,
                next_cursor=next_cursor,
                has_more=has_more,
                total_count=len(contacts)
            )
        finally:
            if owns_client:
                await client.aclose()

    async def get_contact_by_id(
        self,
        access_token: str,
        contact_id: str
    ) -> Optional[CanonicalContact]:
        url = f"{self.BASE_API}/objects/contacts/{contact_id}"
        params = {"properties": ",".join(self.CONTACT_PROPERTIES)}
        headers = {"Authorization": f"Bearer {access_token}"}

        client = self.mock_client or httpx.AsyncClient(timeout=15.0)
        owns_client = self.mock_client is None

        try:
            await self.rate_limiter.acquire()
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return LeadNormalizer.normalize_hubspot_contact(resp.json())
        finally:
            if owns_client:
                await client.aclose()

    async def update_contact(
        self,
        access_token: str,
        contact_id: str,
        fields: dict[str, Any]
    ) -> bool:
        url = f"{self.BASE_API}/objects/contacts/{contact_id}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        client = self.mock_client or httpx.AsyncClient(timeout=15.0)
        owns_client = self.mock_client is None

        try:
            await self.rate_limiter.acquire()
            resp = await client.patch(url, json={"properties": fields}, headers=headers)
            resp.raise_for_status()
            return resp.status_code in (200, 204)
        finally:
            if owns_client:
                await client.aclose()

    def parse_webhook_payload(self, payload: Any) -> list[WebhookEvent]:
        events: list[WebhookEvent] = []
        if isinstance(payload, list):
            raw_list = payload
        elif isinstance(payload, dict):
            raw_list = payload.get("events", [payload])
        else:
            return events

        for item in raw_list:
            event_id = str(item.get("eventId") or item.get("id") or "")
            event_type = str(item.get("subscriptionType") or item.get("eventType") or "")
            object_id = str(item.get("objectId") or "")
            properties = item.get("properties", {})
            events.append(WebhookEvent(
                event_id=event_id,
                event_type=event_type,
                object_id=object_id,
                properties=properties
            ))

        return events
