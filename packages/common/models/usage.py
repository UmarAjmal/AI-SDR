import enum
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import String, Enum, ForeignKey, Integer, Numeric, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from packages.common.models.base import Base, generate_uuid

class UsageEventType(str, enum.Enum):
    MODEL_TOKENS = "MODEL_TOKENS"
    EMAIL_SENT = "EMAIL_SENT"
    BROWSER_RENDER = "BROWSER_RENDER"
    ENRICHMENT_CALL = "ENRICHMENT_CALL"

class UsageEvent(Base):
    __tablename__ = "usage_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[UsageEventType] = mapped_column(
        Enum(UsageEventType, name="usage_event_type"),
        nullable=False,
        index=True
    )
    units: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    cost_estimate_usd: Mapped[Decimal] = mapped_column(Numeric(10, 6), default=Decimal("0.000000"), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    # Relationships
    workspace = relationship("Workspace", back_populates="usage_events")
