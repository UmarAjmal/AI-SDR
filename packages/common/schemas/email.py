from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from packages.common.models.email import (
    EmailProviderType,
    MailboxHealthStatus,
    ThreadStatus,
    MessageDirection,
    DeliveryStatus,
    SuppressionReason
)

class EmailAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    provider: EmailProviderType
    email_address: str
    health_status: MailboxHealthStatus
    daily_send_limit: int
    current_day_sends: int
    last_send_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

class EmailAccountCreateRequest(BaseModel):
    provider: EmailProviderType
    email_address: str
    daily_send_limit: int = Field(default=40, ge=1, le=100)
    credentials_token: str

class EmailAccountUpdateRequest(BaseModel):
    daily_send_limit: Optional[int] = Field(None, ge=1, le=100)
    health_status: Optional[MailboxHealthStatus] = None

class EmailMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    thread_id: str
    provider_message_id: Optional[str] = None
    direction: MessageDirection
    from_address: str
    to_address: str
    subject: str
    body_text: str
    body_html: Optional[str] = None
    headers_json: dict[str, Any] = Field(default_factory=dict)
    delivery_status: DeliveryStatus
    sent_at: datetime
    created_at: datetime

class EmailThreadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    lead_id: Optional[str] = None
    campaign_id: Optional[str] = None
    subject: str
    status: ThreadStatus
    last_message_at: datetime
    created_at: datetime
    messages: list[EmailMessageResponse] = Field(default_factory=list)

class EmailSendRequest(BaseModel):
    account_id: str
    to_email: str
    subject: str
    body_text: str
    body_html: Optional[str] = None
    lead_id: Optional[str] = None
    campaign_id: Optional[str] = None
    thread_id: Optional[str] = None

class SuppressionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    email: Optional[str] = None
    domain: Optional[str] = None
    reason: SuppressionReason
    source: Optional[str] = None
    created_at: datetime

class SuppressionCreateRequest(BaseModel):
    email: Optional[str] = None
    domain: Optional[str] = None
    reason: SuppressionReason = SuppressionReason.MANUAL
    source: Optional[str] = "USER_MANUAL"
