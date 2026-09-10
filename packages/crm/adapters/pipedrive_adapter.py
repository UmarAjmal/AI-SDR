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

logger = logging.getLogger("codenter.crm.pipedrive")

class PipedriveRateLimiter:
    """
    Token-bucket rate limiter enforcing Pipedrive standard API limit (40-80 req/2s).
    """
    def __init__(self, max_tokens: int = 40, refill_time: float = 2.0):
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
                logger.warning(f"Pipedrive rate limit approaching; throttling for {sleep_needed:.2f}s")
                await asyncio.sleep(sleep_needed)
                self.tokens = 1.0
                self.last_update = time.monotonic()

            self.tokens -= 1.0

class PipedriveProvider(CRMProvider):
    AUTH_URL = "https://oauth.pipedrive.com/oauth/authorize"
    TOKEN_URL = "https://oauth.pipedrive.com/oauth/token"
    BASE_API = "https://api.pipedrive.com/v1"

    DEFAULT_SCOPES = ["contacts:read", "contacts:full"]

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        mock_client: httpx.AsyncClient | None = None
    ):
        self.client_id = client_id or os.getenv("PIPEDRIVE_CLIENT_ID", "mock-pipedrive-client-id")
        self.client_secret = client_secret or os.getenv("PIPEDRIVE_CLIENT_SECRET", "mock-pipedrive-client-secret")
        self.mock_client = mock_client
        self.rate_limiter = PipedriveRateLimiter()

    def get_auth_url(self, state: str, redirect_uri: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "state": state
        }
        return f"{self.AUTH_URL}?{urllib.parse.urlencode(params)}"

    async def exchange_code(self, code: str, redirect_uri: str) -> TokenBundle:
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri
        }
        auth = (self.client_id, self.client_secret)
        client = self.mock_client or httpx.AsyncClient(timeout=15.0)
        owns_client = self.mock_client is None

        try:
            await self.rate_limiter.acquire()
            resp = await client.post(self.TOKEN_URL, data=data, auth=auth)
            resp.raise_for_status()
            res = resp.json()

            account_id = str(res.get("company_id") or "")
            account_name = f"Pipedrive Company #{account_id}" if account_id else "Pipedrive Account"

            return TokenBundle(
                access_token=res["access_token"],
                refresh_token=res.get("refresh_token", ""),
                expires_in=res.get("expires_in", 3600),
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
            "refresh_token": refresh_token
        }
        auth = (self.client_id, self.client_secret)
        client = self.mock_client or httpx.AsyncClient(timeout=15.0)
        owns_client = self.mock_client is None

        try:
            await self.rate_limiter.acquire()
            resp = await client.post(self.TOKEN_URL, data=data, auth=auth)
            resp.raise_for_status()
            res = resp.json()

            return TokenBundle(
                access_token=res["access_token"],
                refresh_token=res.get("refresh_token", refresh_token),
                expires_in=res.get("expires_in", 3600),
                token_type=res.get("token_type", "Bearer")
            )
        finally:
            if owns_client:
                await client.aclose()

    def _prepare_headers_and_params(self, access_token: str, params: dict[str, Any]) -> tuple[dict[str, str], dict[str, Any]]:
        """
        Pipedrive supports both Bearer token (OAuth) and Personal API Token (query param or header).
        """
        headers = {
            "Content-Type": "application/json"
        }
        p = dict(params)
        # If token is 40-char hex (Personal API Token), send via query param or header
        if len(access_token) == 40 and not access_token.startswith("eyJ"):
            p["api_token"] = access_token
        else:
            headers["Authorization"] = f"Bearer {access_token}"
        return headers, p

    async def fetch_contacts(
        self,
        access_token: str,
        cursor: Optional[str] = None,
        limit: int = 100
    ) -> ContactBatch:
        url = f"{self.BASE_API}/persons"
        params: dict[str, Any] = {
            "limit": min(limit, 100),
            "start": int(cursor) if cursor and cursor.isdigit() else 0
        }
        headers, query_params = self._prepare_headers_and_params(access_token, params)

        client = self.mock_client or httpx.AsyncClient(timeout=20.0)
        owns_client = self.mock_client is None

        try:
            await self.rate_limiter.acquire()
            resp = await client.get(url, params=query_params, headers=headers)

            if resp.status_code == 429:
                retry_after = float(resp.headers.get("Retry-After", 2.0))
                logger.warning(f"Pipedrive 429 rate limit reached. Retrying in {retry_after}s.")
                await asyncio.sleep(retry_after)
                resp = await client.get(url, params=query_params, headers=headers)

            resp.raise_for_status()
            data = resp.json()

            raw_persons = data.get("data") or []
            contacts: list[CanonicalContact] = []
            for item in raw_persons:
                if isinstance(item, dict):
                    contacts.append(LeadNormalizer.normalize_pipedrive_person(item))

            pagination = data.get("additional_data", {}).get("pagination", {})
            has_more = pagination.get("more_items_in_collection", False)
            next_cursor = str(pagination.get("next_start")) if has_more and pagination.get("next_start") is not None else None

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
        url = f"{self.BASE_API}/persons/{contact_id}"
        headers, query_params = self._prepare_headers_and_params(access_token, {})

        client = self.mock_client or httpx.AsyncClient(timeout=15.0)
        owns_client = self.mock_client is None

        try:
            await self.rate_limiter.acquire()
            resp = await client.get(url, params=query_params, headers=headers)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()
            person_data = data.get("data")
            if not person_data:
                return None
            return LeadNormalizer.normalize_pipedrive_person(person_data)
        finally:
            if owns_client:
                await client.aclose()

    async def update_contact(
        self,
        access_token: str,
        contact_id: str,
        fields: dict[str, Any]
    ) -> bool:
        url = f"{self.BASE_API}/persons/{contact_id}"
        headers, query_params = self._prepare_headers_and_params(access_token, {})

        client = self.mock_client or httpx.AsyncClient(timeout=15.0)
        owns_client = self.mock_client is None

        try:
            await self.rate_limiter.acquire()
            resp = await client.put(url, json=fields, params=query_params, headers=headers)
            resp.raise_for_status()
            return resp.status_code in (200, 201)
        finally:
            if owns_client:
                await client.aclose()

    def parse_webhook_payload(self, payload: Any) -> list[WebhookEvent]:
        events: list[WebhookEvent] = []
        if isinstance(payload, dict):
            event_type = str(payload.get("event") or payload.get("action") or "")
            current_data = payload.get("current") or {}
            object_id = str(current_data.get("id") or payload.get("meta", {}).get("id") or "")
            event_id = str(payload.get("meta", {}).get("webhook_id") or object_id)

            events.append(WebhookEvent(
                event_id=event_id,
                event_type=event_type,
                object_id=object_id,
                properties=current_data
            ))

        return events
