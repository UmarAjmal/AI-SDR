import enum
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import String, JSON, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.common.models.base import Base, generate_uuid


class ConversationEventType(str, enum.Enum):
    EMAIL_SENT = "EMAIL_SENT"
    INBOUND_RECEIVED = "INBOUND_RECEIVED"
    INTENT_CLASSIFIED = "INTENT_CLASSIFIED"
    REPLY_GENERATED = "REPLY_GENERATED"
    HANDOFF_TRIGGERED = "HANDOFF_TRIGGERED"
    LEAD_QUALIFIED = "LEAD_QUALIFIED"
    MEETING_BOOKED = "MEETING_BOOKED"
    OPT_OUT_DETECTED = "OPT_OUT_DETECTED"


class ConversationEvent(Base):
    """
    Immutable 5-Question Audit Trail recording:
    1. What happened? (event_type)
    2. Which rule allowed it? (rule_name / rule_matched)
    3. Which AI model & prompt version was used? (model_version, prompt_version)
    4. What knowledge chunks/data were retrieved? (knowledge_chunk_ids)
    5. What downstream state changed? (previous_state -> new_state)
    """
    __tablename__ = "conversation_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    thread_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("email_threads.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    lead_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("crm_leads.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    campaign_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    rule_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    knowledge_chunk_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    previous_state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    new_state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    data_payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    # Relationships
    workspace = relationship("Workspace", backref="conversation_events")
    thread = relationship("EmailThread", backref="conversation_events")
    lead = relationship("CRMLead", backref="conversation_events")
    campaign = relationship("Campaign", backref="conversation_events")

    def __init__(self, **kwargs: Any) -> None:
        # Backward-compatibility adapter for legacy code passing rule_matched or payload
        if "rule_matched" in kwargs and "rule_name" not in kwargs:
            kwargs["rule_name"] = kwargs.pop("rule_matched")
        elif "rule_matched" in kwargs and "rule_name" in kwargs:
            kwargs.pop("rule_matched")

        if "payload" in kwargs and "data_payload" not in kwargs:
            kwargs["data_payload"] = kwargs.pop("payload")
        elif "payload" in kwargs and "data_payload" in kwargs:
            kwargs.pop("payload")

        # Convert enum event_type to string value if needed
        if "event_type" in kwargs and hasattr(kwargs["event_type"], "value"):
            kwargs["event_type"] = kwargs["event_type"].value

        super().__init__(**kwargs)

    @property
    def rule_matched(self) -> str | None:
        return self.rule_name

    @rule_matched.setter
    def rule_matched(self, value: str | None) -> None:
        self.rule_name = value

    @property
    def payload(self) -> dict:
        return self.data_payload

    @payload.setter
    def payload(self, value: dict) -> None:
        self.data_payload = value
