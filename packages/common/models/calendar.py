import enum
from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, JSON, DateTime, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.common.models.base import Base, TimestampMixin, generate_uuid

class CalendarProviderType(str, enum.Enum):
    GOOGLE = "GOOGLE"
    MICROSOFT = "MICROSOFT"

class AppointmentStatus(str, enum.Enum):
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    RESCHEDULED = "RESCHEDULED"

class CalendarConnection(Base, TimestampMixin):
    __tablename__ = "calendar_connections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[CalendarProviderType] = mapped_column(
        Enum(CalendarProviderType, name="calendar_provider_type"),
        nullable=False
    )
    account_email: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_access_token: Mapped[str] = mapped_column(String(1000), nullable=False)
    encrypted_refresh_token: Mapped[str] = mapped_column(String(1000), nullable=False)
    token_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sync_status: Mapped[str] = mapped_column(String(50), default="CONNECTED", nullable=False)
    
    # Working hours configuration (Mon-Fri 09:00 - 17:00 default)
    working_hours_json: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {
            "start_time": "09:00",
            "end_time": "17:00",
            "days": [0, 1, 2, 3, 4]  # 0=Monday, 4=Friday
        },
        nullable=False
    )
    buffer_minutes: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    timezone: Mapped[str] = mapped_column(String(100), default="UTC", nullable=False)

    # Relationships
    workspace = relationship("Workspace", backref="calendar_connections")
    appointments = relationship("Appointment", back_populates="connection", cascade="all, delete-orphan")

class Appointment(Base, TimestampMixin):
    __tablename__ = "appointments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    calendar_connection_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("calendar_connections.id", ondelete="SET NULL"), nullable=True, index=True)
    lead_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("crm_leads.id", ondelete="SET NULL"), nullable=True, index=True)
    campaign_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    attendee_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    host_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    
    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(AppointmentStatus, name="appointment_status"),
        default=AppointmentStatus.CONFIRMED,
        nullable=False,
        index=True
    )
    
    provider_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    meeting_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    workspace = relationship("Workspace", backref="appointments")
    connection = relationship("CalendarConnection", back_populates="appointments")
    lead = relationship("CRMLead", backref="appointments")
