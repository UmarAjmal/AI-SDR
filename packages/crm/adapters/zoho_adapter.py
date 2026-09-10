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

logger = logging.getLogger("codenter.crm.zoho")

class ZohoRateLimiter:
    """
    Token-bucket rate limiter enforcing Zoho CRM API limit (100 req/min or 15-20 req/s concurrency).
    """
    def __init__(self, max_tokens: int = 15, refill_time: float = 1.0):
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
                logger.warning(f"Zoho rate limit approaching; throttling for {sleep_needed:.2f}s")
                await asyncio.sleep(sleep_needed)
                self.tokens = 1.0
                self.last_update = time.monotonic()

            self.tokens -= 1.0

class ZohoProvider(CRMProvider):
    AUTH_URL = "https://accounts.zoho.com/oauth/v2/auth"
    TOKEN_URL = "https://accounts.zoho.com/oauth/v2/token"
    DEFAULT_BASE_API = "https://www.zohoapis.com/crm/v3"

    DEFAULT_SCOPES = [
        "ZohoCRM.modules.leads.ALL",
        "ZohoCRM.modules.contacts.ALL",
        "ZohoCRM.users.READ"
    ]

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        api_domain: str | None = None,
        mock_client: httpx.AsyncClient | None = None
    ):
        self.client_id = client_id or os.getenv("ZOHO_CLIENT_ID", "mock-zoho-client-id")
        self.client_secret = client_secret or os.getenv("ZOHO_CLIENT_SECRET", "mock-zoho-client-secret")
        self.base_api = (api_domain or os.getenv("ZOHO_API_DOMAIN", self.DEFAULT_BASE_API)).rstrip("/")
        if not self.base_api.endswith("/crm/v3") and not self.base_api.endswith("/crm/v6"):
            self.base_api = f"{self.base_api}/crm/v3"
        self.mock_client = mock_client
        self.rate_limiter = ZohoRateLimiter()

    def get_auth_url(self, state: str, redirect_uri: str) -> str:
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "scope": ",".join(self.DEFAULT_SCOPES),
            "redirect_uri": redirect_uri,
            "access_type": "offline",
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

            if "api_domain" in res:
                self.base_api = f"{res['api_domain'].rstrip('/')}/crm/v3"

            return TokenBundle(
                access_token=res["access_token"],
                refresh_token=res.get("refresh_token", ""),
                expires_in=res.get("expires_in", 3600),
                token_type=res.get("token_type", "Bearer"),
                account_id="zoho_org",
                account_name="Zoho CRM"
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

            if "api_domain" in res:
                self.base_api = f"{res['api_domain'].rstrip('/')}/crm/v3"

            return TokenBundle(
                access_token=res["access_token"],
                refresh_token=res.get("refresh_token", refresh_token),
                expires_in=res.get("expires_in", 3600),
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
        url = f"{self.base_api}/Leads"
        page = int(cursor) if cursor and cursor.isdigit() else 1
        params = {
            "page": page,
            "per_page": min(limit, 100)
        }
        headers = {
            "Authorization": f"Zoho-oauthtoken {access_token}" if not access_token.startswith("Bearer") else access_token,
            "Content-Type": "application/json"
        }
        if access_token.startswith("Bearer"):
            headers["Authorization"] = access_token
        elif not headers["Authorization"].startswith("Zoho-oauthtoken"):
            headers["Authorization"] = f"Zoho-oauthtoken {access_token}"

        client = self.mock_client or httpx.AsyncClient(timeout=20.0)
        owns_client = self.mock_client is None

        try:
            await self.rate_limiter.acquire()
            resp = await client.get(url, params=params, headers=headers)

            if resp.status_code == 429:
                retry_after = float(resp.headers.get("Retry-After", 2.0))
                logger.warning(f"Zoho 429 rate limit. Retrying in {retry_after}s.")
                await asyncio.sleep(retry_after)
                resp = await client.get(url, params=params, headers=headers)

            if resp.status_code == 204:
                # Zoho returns 204 No Content when no records exist
                return ContactBatch(contacts=[], next_cursor=None, has_more=False, total_count=0)

            resp.raise_for_status()
            data = resp.json()

            raw_leads = data.get("data") or []
            contacts: list[CanonicalContact] = []
            for item in raw_leads:
                contacts.append(LeadNormalizer.normalize_zoho_lead(item))

            info = data.get("info", {})
            has_more = info.get("more_records", False)
            next_cursor = str(page + 1) if has_more else None

            return ContactBatch(
                contacts=contacts,
                next_cursor=next_cursor,
                has_more=has_more,
                total_count=info.get("count", len(contacts))
            )
        finally:
            if owns_client:
                await client.aclose()

    async def get_contact_by_id(
        self,
        access_token: str,
        contact_id: str
    ) -> Optional[CanonicalContact]:
        url = f"{self.base_api}/Leads/{contact_id}"
        headers = {
            "Authorization": f"Zoho-oauthtoken {access_token}" if not access_token.startswith("Bearer") else access_token
        }

        client = self.mock_client or httpx.AsyncClient(timeout=15.0)
        owns_client = self.mock_client is None

        try:
            await self.rate_limiter.acquire()
            resp = await client.get(url, headers=headers)
            if resp.status_code in (404, 204):
                return None
            resp.raise_for_status()
            data = resp.json()
            leads = data.get("data") or []
            if not leads:
                return None
            return LeadNormalizer.normalize_zoho_lead(leads[0])
        finally:
            if owns_client:
                await client.aclose()

    async def update_contact(
        self,
        access_token: str,
        contact_id: str,
        fields: dict[str, Any]
    ) -> bool:
        url = f"{self.base_api}/Leads/{contact_id}"
        headers = {
            "Authorization": f"Zoho-oauthtoken {access_token}" if not access_token.startswith("Bearer") else access_token,
            "Content-Type": "application/json"
        }
        body = {"data": [fields]}

        client = self.mock_client or httpx.AsyncClient(timeout=15.0)
        owns_client = self.mock_client is None

        try:
            await self.rate_limiter.acquire()
            resp = await client.put(url, json=body, headers=headers)
            resp.raise_for_status()
            return resp.status_code in (200, 201, 202)
        finally:
            if owns_client:
                await client.aclose()

    def parse_webhook_payload(self, payload: Any) -> list[WebhookEvent]:
        events: list[WebhookEvent] = []
        if isinstance(payload, dict):
            channel_id = str(payload.get("channel_id") or "")
            events_data = payload.get("events") or [payload]
            for item in events_data:
                events.append(WebhookEvent(
                    event_id=channel_id or str(item.get("id") or ""),
                    event_type=str(item.get("event") or "update"),
                    object_id=str(item.get("id") or item.get("entity_id") or ""),
                    properties=item
                ))

        return events
