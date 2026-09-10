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

logger = logging.getLogger("codenter.crm.salesforce")

class SalesforceRateLimiter:
    """
    Token-bucket rate limiter enforcing Salesforce API limits.
    Default allows 25 requests per second with burst capacity.
    """
    def __init__(self, max_tokens: int = 25, refill_time: float = 1.0):
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
                logger.warning(f"Salesforce rate limit approaching; throttling for {sleep_needed:.2f}s")
                await asyncio.sleep(sleep_needed)
                self.tokens = 1.0
                self.last_update = time.monotonic()

            self.tokens -= 1.0

class SalesforceProvider(CRMProvider):
    AUTH_URL = "https://login.salesforce.com/services/oauth2/authorize"
    TOKEN_URL = "https://login.salesforce.com/services/oauth2/token"
    DEFAULT_API_VERSION = "v59.0"

    DEFAULT_SCOPES = ["api", "refresh_token", "offline_access"]

    LEAD_FIELDS = [
        "Id", "FirstName", "LastName", "Email", "Phone", "MobilePhone",
        "Title", "Company", "Website", "Industry", "NumberOfEmployees",
        "City", "State", "Country", "AnnualRevenue", "Status", "OwnerId",
        "Description", "HasOptedOutOfEmail", "DoNotCall"
    ]

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        instance_url: str | None = None,
        api_version: str = DEFAULT_API_VERSION,
        mock_client: httpx.AsyncClient | None = None
    ):
        self.client_id = client_id or os.getenv("SALESFORCE_CLIENT_ID", "mock-salesforce-client-id")
        self.client_secret = client_secret or os.getenv("SALESFORCE_CLIENT_SECRET", "mock-salesforce-client-secret")
        self.instance_url = (instance_url or os.getenv("SALESFORCE_INSTANCE_URL", "https://login.salesforce.com")).rstrip("/")
        self.api_version = api_version
        self.mock_client = mock_client
        self.rate_limiter = SalesforceRateLimiter()

    def get_auth_url(self, state: str, redirect_uri: str) -> str:
        params = {
            "response_type": "code",
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
        client = self.mock_client or httpx.AsyncClient(timeout=20.0)
        owns_client = self.mock_client is None

        try:
            await self.rate_limiter.acquire()
            resp = await client.post(self.TOKEN_URL, data=data)
            resp.raise_for_status()
            res = resp.json()

            instance_url = res.get("instance_url")
            if instance_url:
                self.instance_url = instance_url.rstrip("/")

            account_id = str(res.get("id") or "")
            account_name = f"Salesforce ({self.instance_url})"

            return TokenBundle(
                access_token=res["access_token"],
                refresh_token=res.get("refresh_token", ""),
                expires_in=res.get("expires_in", 7200),
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
        client = self.mock_client or httpx.AsyncClient(timeout=20.0)
        owns_client = self.mock_client is None

        try:
            await self.rate_limiter.acquire()
            resp = await client.post(self.TOKEN_URL, data=data)
            resp.raise_for_status()
            res = resp.json()

            instance_url = res.get("instance_url")
            if instance_url:
                self.instance_url = instance_url.rstrip("/")

            return TokenBundle(
                access_token=res["access_token"],
                refresh_token=res.get("refresh_token", refresh_token),
                expires_in=res.get("expires_in", 7200),
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
        """
        Fetches Leads from Salesforce using REST API SOQL Query.
        Handles both initial SOQL query and nextRecordsUrl pagination cursor.
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        client = self.mock_client or httpx.AsyncClient(timeout=25.0)
        owns_client = self.mock_client is None

        try:
            await self.rate_limiter.acquire()

            if cursor and (cursor.startswith("/") or cursor.startswith("http")):
                # Cursor is nextRecordsUrl
                url = cursor if cursor.startswith("http") else f"{self.instance_url}{cursor}"
                resp = await client.get(url, headers=headers)
            else:
                fields_str = ", ".join(self.LEAD_FIELDS)
                query = f"SELECT {fields_str} FROM Lead ORDER BY CreatedDate DESC LIMIT {limit}"
                url = f"{self.instance_url}/services/data/{self.api_version}/query"
                resp = await client.get(url, params={"q": query}, headers=headers)

            if resp.status_code == 429:
                retry_after = float(resp.headers.get("Retry-After", 2.0))
                logger.warning(f"Salesforce 429 rate limit. Throttling for {retry_after}s.")
                await asyncio.sleep(retry_after)
                resp = await client.get(url, headers=headers)

            resp.raise_for_status()
            data = resp.json()

            raw_records = data.get("records", [])
            contacts: list[CanonicalContact] = []
            for item in raw_records:
                contacts.append(LeadNormalizer.normalize_salesforce_lead(item))

            next_url = data.get("nextRecordsUrl")
            has_more = not data.get("done", True) and bool(next_url)

            return ContactBatch(
                contacts=contacts,
                next_cursor=next_url if has_more else None,
                has_more=has_more,
                total_count=data.get("totalSize", len(contacts))
            )
        finally:
            if owns_client:
                await client.aclose()

    async def get_contact_by_id(
        self,
        access_token: str,
        contact_id: str
    ) -> Optional[CanonicalContact]:
        url = f"{self.instance_url}/services/data/{self.api_version}/sobjects/Lead/{contact_id}"
        headers = {"Authorization": f"Bearer {access_token}"}

        client = self.mock_client or httpx.AsyncClient(timeout=15.0)
        owns_client = self.mock_client is None

        try:
            await self.rate_limiter.acquire()
            resp = await client.get(url, headers=headers)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return LeadNormalizer.normalize_salesforce_lead(resp.json())
        finally:
            if owns_client:
                await client.aclose()

    async def update_contact(
        self,
        access_token: str,
        contact_id: str,
        fields: dict[str, Any]
    ) -> bool:
        url = f"{self.instance_url}/services/data/{self.api_version}/sobjects/Lead/{contact_id}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        client = self.mock_client or httpx.AsyncClient(timeout=15.0)
        owns_client = self.mock_client is None

        try:
            await self.rate_limiter.acquire()
            resp = await client.patch(url, json=fields, headers=headers)
            resp.raise_for_status()
            return resp.status_code in (200, 204)
        finally:
            if owns_client:
                await client.aclose()

    def parse_webhook_payload(self, payload: Any) -> list[WebhookEvent]:
        events: list[WebhookEvent] = []
        if isinstance(payload, list):
            items = payload
        elif isinstance(payload, dict):
            items = payload.get("events", [payload])
        else:
            return events

        for item in items:
            event_id = str(item.get("replayId") or item.get("id") or "")
            event_type = str(item.get("changeType") or item.get("eventType") or "updated")
            entity_id = str(item.get("recordId") or item.get("entityId") or "")
            properties = item.get("fields", item)
            events.append(WebhookEvent(
                event_id=event_id,
                event_type=event_type,
                object_id=entity_id,
                properties=properties
            ))

        return events
