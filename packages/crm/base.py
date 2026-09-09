from abc import ABC, abstractmethod
from typing import Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone

@dataclass
class TokenBundle:
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"
    account_id: Optional[str] = None
    account_name: Optional[str] = None

@dataclass
class CanonicalContact:
    email: str
    crm_record_id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    domain: Optional[str] = None
    industry: Optional[str] = None
    employee_count: Optional[int] = None
    location: Optional[str] = None
    revenue_band: Optional[str] = None
    lifecycle_stage: Optional[str] = None
    owner_id: Optional[str] = None
    lead_notes: Optional[str] = None
    custom_fields: dict[str, Any] = field(default_factory=dict)
    opt_out: bool = False
    do_not_contact: bool = False

@dataclass
class ContactBatch:
    contacts: list[CanonicalContact]
    next_cursor: Optional[str] = None
    has_more: bool = False
    total_count: Optional[int] = None

@dataclass
class WebhookEvent:
    event_id: str
    event_type: str
    object_id: str
    properties: dict[str, Any]
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

class CRMProvider(ABC):
    @abstractmethod
    def get_auth_url(self, state: str, redirect_uri: str) -> str:
        """Generates the OAuth2 authorization redirect URL with CSRF state token."""
        pass

    @abstractmethod
    async def exchange_code(self, code: str, redirect_uri: str) -> TokenBundle:
        """Exchanges an authorization code for an OAuth2 TokenBundle."""
        pass

    @abstractmethod
    async def refresh_tokens(self, refresh_token: str) -> TokenBundle:
        """Refreshes expired access tokens using a refresh token."""
        pass

    @abstractmethod
    async def fetch_contacts(
        self,
        access_token: str,
        cursor: Optional[str] = None,
        limit: int = 100
    ) -> ContactBatch:
        """Fetches a paginated batch of contacts from the CRM."""
        pass

    @abstractmethod
    async def get_contact_by_id(
        self,
        access_token: str,
        contact_id: str
    ) -> Optional[CanonicalContact]:
        """Retrieves a single contact by its CRM record ID."""
        pass

    @abstractmethod
    async def update_contact(
        self,
        access_token: str,
        contact_id: str,
        fields: dict[str, Any]
    ) -> bool:
        """Updates contact properties in the CRM."""
        pass

    @abstractmethod
    def parse_webhook_payload(self, payload: Any) -> list[WebhookEvent]:
        """Parses vendor-specific webhook payloads into normalized WebhookEvents."""
        pass
