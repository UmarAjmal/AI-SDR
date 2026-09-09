import enum
from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, JSON, DateTime, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.common.models.base import Base, TimestampMixin, generate_uuid

class CampaignState(str, enum.Enum):
    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    SCHEDULED = "SCHEDULED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"

class LeadSequenceState(str, enum.Enum):
    QUEUED = "QUEUED"
    WAITING = "WAITING"
    READY = "READY"
    SENT = "SENT"
    REPLIED = "REPLIED"
    PAUSED = "PAUSED"
    UNSUBSCRIBED = "UNSUBSCRIBED"
    BOUNCED = "BOUNCED"
    MEETING_BOOKED = "MEETING_BOOKED"
    QUALIFIED = "QUALIFIED"
    DISQUALIFIED = "DISQUALIFIED"
    HANDOFF = "HANDOFF"
    COMPLETED = "COMPLETED"

class Campaign(Base, TimestampMixin):
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[CampaignState] = mapped_column(
        Enum(CampaignState, name="campaign_state"),
        default=CampaignState.DRAFT,
        nullable=False,
        index=True
    )
    objective: Mapped[str] = mapped_column(String(255), default="DEMO_BOOKING", nullable=False)
    config_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    workspace = relationship("Workspace", backref="campaigns")
    steps = relationship("CampaignStep", back_populates="campaign", cascade="all, delete-orphan", order_by="CampaignStep.step_number")
    leads = relationship("CampaignLead", back_populates="campaign", cascade="all, delete-orphan")

class CampaignStep(Base):
    __tablename__ = "campaign_steps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    campaign_id: Mapped[str] = mapped_column(String(36), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)

    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    delay_days: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    delay_hours: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    prompt_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    template_config_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint("campaign_id", "step_number", name="uq_campaign_step_number"),
    )

    # Relationships
    campaign = relationship("Campaign", back_populates="steps")

class CampaignLead(Base, TimestampMixin):
    __tablename__ = "campaign_leads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    campaign_id: Mapped[str] = mapped_column(String(36), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    lead_id: Mapped[str] = mapped_column(String(36), ForeignKey("crm_leads.id", ondelete="CASCADE"), nullable=False, index=True)

    current_step_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    state: Mapped[LeadSequenceState] = mapped_column(
        Enum(LeadSequenceState, name="lead_sequence_state"),
        default=LeadSequenceState.QUEUED,
        nullable=False,
        index=True
    )
    next_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    __table_args__ = (
        UniqueConstraint("campaign_id", "lead_id", name="uq_campaign_lead_enrollment"),
    )

    # Relationships
    campaign = relationship("Campaign", back_populates="leads")
    lead = relationship("CRMLead", backref="campaign_enrollments")

from packages.common.models.telemetry import ConversationEvent, ConversationEventType  # noqa: E402
