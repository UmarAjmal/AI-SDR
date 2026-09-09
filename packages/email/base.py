from abc import ABC, abstractmethod
from typing import Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone

@dataclass
class OutboundEmail:
    from_address: str
    to_address: str
    subject: str
    body_text: str
    body_html: Optional[str] = None
    thread_id: Optional[str] = None
    in_reply_to: Optional[str] = None
    references: list[str] = field(default_factory=list)
    custom_headers: dict[str, str] = field(default_factory=dict)

@dataclass
class SendResult:
    success: bool
    provider_message_id: Optional[str] = None
    status_code: int = 200
    error: Optional[str] = None
    raw_response: dict[str, Any] = field(default_factory=dict)

@dataclass
class InboundEmail:
    provider_message_id: str
    from_address: str
    to_address: str
    subject: str
    body_text: str
    body_html: Optional[str] = None
    in_reply_to: Optional[str] = None
    references: list[str] = field(default_factory=list)
    headers: dict[str, str] = field(default_factory=dict)
    received_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

class EmailProvider(ABC):
    @abstractmethod
    async def send_message(self, credentials: dict[str, Any], message: OutboundEmail) -> SendResult:
        """Sends an outbound RFC 2822 or API message through the provider."""
        pass

    @abstractmethod
    async def fetch_message(self, credentials: dict[str, Any], provider_msg_id: str) -> Optional[InboundEmail]:
        """Fetches an individual message from the provider by its ID."""
        pass

    @abstractmethod
    async def setup_webhook(self, credentials: dict[str, Any], callback_url: str) -> bool:
        """Sets up mailbox watch subscriptions or push notifications."""
        pass
