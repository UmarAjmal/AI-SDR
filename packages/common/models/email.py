import enum
from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, Boolean, JSON, DateTime, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.common.models.base import Base, TimestampMixin, generate_uuid

class EmailProviderType(str, enum.Enum):
    GOOGLE = "GOOGLE"
    MICROSOFT = "MICROSOFT"
    SMTP = "SMTP"

class MailboxHealthStatus(str, enum.Enum):
    HEALTHY = "HEALTHY"
    PAUSED = "PAUSED"
    REVOKED = "REVOKED"
    WARMUP = "WARMUP"

class ThreadStatus(str, enum.Enum):
    OPEN = "OPEN"
    REPLIED = "REPLIED"
    CLOSED = "CLOSED"
    BOUNCED = "BOUNCED"

class MessageDirection(str, enum.Enum):
    OUTBOUND = "OUTBOUND"
    INBOUND = "INBOUND"

class DeliveryStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    BOUNCED = "BOUNCED"
    FAILED = "FAILED"

class SuppressionReason(str, enum.Enum):
    UNSUBSCRIBE = "UNSUBSCRIBE"
    HARD_BOUNCE = "HARD_BOUNCE"
    COMPLAINT = "COMPLAINT"
    MANUAL = "MANUAL"

class EmailAccount(Base, TimestampMixin):
    __tablename__ = "email_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)

    provider: Mapped[EmailProviderType] = mapped_column(
        Enum(EmailProviderType, name="email_provider_type"),
        default=EmailProviderType.GOOGLE,
        nullable=False
    )
    email_address: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    encrypted_credentials: Mapped[str] = mapped_column(Text, nullable=False)

    daily_send_limit: Mapped[int] = mapped_column(Integer, default=40, nullable=False)
    current_day_sends: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_send_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    health_status: Mapped[MailboxHealthStatus] = mapped_column(
        Enum(MailboxHealthStatus, name="mailbox_health_status"),
        default=MailboxHealthStatus.HEALTHY,
        nullable=False
    )

    # Relationships
    workspace = relationship("Workspace", backref="email_accounts")

class EmailThread(Base, TimestampMixin):
    __tablename__ = "email_threads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    lead_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("crm_leads.id", ondelete="SET NULL"), nullable=True, index=True)
    campaign_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[ThreadStatus] = mapped_column(
        Enum(ThreadStatus, name="thread_status"),
        default=ThreadStatus.OPEN,
        nullable=False
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    workspace = relationship("Workspace", backref="email_threads")
    lead = relationship("CRMLead", backref="email_threads")
    messages = relationship("EmailMessage", back_populates="thread", cascade="all, delete-orphan", order_by="EmailMessage.created_at")

class EmailMessage(Base):
    __tablename__ = "email_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    thread_id: Mapped[str] = mapped_column(String(36), ForeignKey("email_threads.id", ondelete="CASCADE"), nullable=False, index=True)

    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    direction: Mapped[MessageDirection] = mapped_column(
        Enum(MessageDirection, name="message_direction"),
        nullable=False
    )
    from_address: Mapped[str] = mapped_column(String(255), nullable=False)
    to_address: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    body_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    headers_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    delivery_status: Mapped[DeliveryStatus] = mapped_column(
        Enum(DeliveryStatus, name="delivery_status"),
        default=DeliveryStatus.SENT,
        nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    thread = relationship("EmailThread", back_populates="messages")

class SuppressionList(Base):
    __tablename__ = "suppression_list"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)

    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    reason: Mapped[SuppressionReason] = mapped_column(
        Enum(SuppressionReason, name="suppression_reason"),
        default=SuppressionReason.UNSUBSCRIBE,
        nullable=False
    )
    source: Mapped[str | None] = mapped_column(String(100), default="USER_MANUAL", nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "email", name="uq_suppression_workspace_email"),
    )
