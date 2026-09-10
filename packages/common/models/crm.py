import enum
from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, Float, Boolean, JSON, DateTime, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.common.models.base import Base, TimestampMixin, generate_uuid

class CRMProviderType(str, enum.Enum):
    HUBSPOT = "HUBSPOT"
    SALESFORCE = "SALESFORCE"
    PIPEDRIVE = "PIPEDRIVE"
    ZOHO = "ZOHO"

class CRMSyncStatus(str, enum.Enum):
    CONNECTED = "CONNECTED"
    SYNCING = "SYNCING"
    PAUSED = "PAUSED"
    REVOKED = "REVOKED"
    ERROR = "ERROR"

class CRMConnection(Base, TimestampMixin):
    __tablename__ = "crm_connections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    
    provider: Mapped[CRMProviderType] = mapped_column(
        Enum(CRMProviderType, name="crm_provider_type"),
        default=CRMProviderType.HUBSPOT,
        nullable=False
    )
    account_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    account_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    encrypted_access_token: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_refresh_token: Mapped[str] = mapped_column(Text, nullable=False)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    field_mappings_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    sync_status: Mapped[CRMSyncStatus] = mapped_column(
        Enum(CRMSyncStatus, name="crm_sync_status"),
        default=CRMSyncStatus.CONNECTED,
        nullable=False
    )
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sync_cursor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sync_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    sync_errors_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    # Relationships
    workspace = relationship("Workspace", backref="crm_connections")
    leads = relationship("CRMLead", back_populates="connection", cascade="all, delete-orphan")

class CRMLead(Base, TimestampMixin):
    """
    Section 5.2 Canonical Lead Model covering all 10 core intelligence groups:
    Identity, Company, CRM, Context, Enrichment, Scoring, Consent/Suppression,
    Campaign, Conversation, and Outcome.
    """
    __tablename__ = "crm_leads"

    # Group 1: Identity
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    job_title: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Group 2: Company
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    industry: Mapped[str | None] = mapped_column(String(255), nullable=True)
    employee_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    revenue_band: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Group 3: CRM
    crm_connection_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("crm_connections.id", ondelete="SET NULL"), nullable=True, index=True)
    crm_record_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    provider: Mapped[str | None] = mapped_column(String(50), default="HUBSPOT", nullable=True)
    owner_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lifecycle_stage: Mapped[str | None] = mapped_column(String(100), default="lead", nullable=True)
    source: Mapped[str | None] = mapped_column(String(100), default="CRM_SYNC", nullable=True)

    # Group 4: Context
    lead_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    custom_fields: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    previous_interactions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    # Group 6: Scoring (0-100) & Explainable Reasons (Section 5.3)
    icp_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    intent_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False, index=True)
    score_band: Mapped[str] = mapped_column(String(20), default="COLD", nullable=False, index=True)
    score_reasons_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    # Group 7: Consent / Suppression & Deliverability Safeguards
    opt_out: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    do_not_contact: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    bounce_status: Mapped[str] = mapped_column(String(50), default="NONE", nullable=False)
    suppression_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Group 8: Campaign Membership & Execution State (Section 5.2)
    campaign_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    campaign_membership: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_step: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    state: Mapped[str] = mapped_column(String(50), default="DISCOVERED", nullable=False, index=True)
    next_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Group 9: Conversation & Sentiment
    thread_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    last_inbound_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_outbound_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sentiment_intent: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Group 10: Outcome & NFAT Qualification Engine
    is_qualified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    qualification_status: Mapped[str] = mapped_column(String(50), default="UNQUALIFIED", nullable=False, index=True)
    qualification_details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    meeting_booked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    disqualified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    handoff_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    @property
    def provider_record_id(self) -> str | None:
        return self.crm_record_id

    @provider_record_id.setter
    def provider_record_id(self, val: str | None):
        self.crm_record_id = val

    @property
    def reasons(self) -> list:
        return self.score_reasons_json

    __table_args__ = (
        UniqueConstraint("workspace_id", "email", name="uq_crm_leads_workspace_email"),
    )

    # Relationships
    workspace = relationship("Workspace", backref="crm_leads")
    connection = relationship("CRMConnection", back_populates="leads")
    enrichment = relationship("LeadEnrichment", uselist=False, back_populates="lead", cascade="all, delete-orphan", lazy="selectin")

class LeadEnrichment(Base):
    __tablename__ = "lead_enrichments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    lead_id: Mapped[str] = mapped_column(String(36), ForeignKey("crm_leads.id", ondelete="CASCADE"), nullable=False, unique=True)

    company_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    role_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_technologies: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    signals_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    source_urls: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    enriched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    lead = relationship("CRMLead", back_populates="enrichment")
