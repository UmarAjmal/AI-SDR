from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from packages.common.models.crm import CRMProviderType, CRMSyncStatus

class CRMConnectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    provider: CRMProviderType
    account_id: Optional[str] = None
    account_name: Optional[str] = None
    sync_status: CRMSyncStatus
    last_sync_at: Optional[datetime] = None
    sync_error_message: Optional[str] = None
    sync_errors_json: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

class CRMAuthUrlResponse(BaseModel):
    provider: CRMProviderType
    authorization_url: str
    state: str

class CRMOAuthCallbackRequest(BaseModel):
    code: str
    state: str
    redirect_uri: str

class CRMDirectConnectRequest(BaseModel):
    provider: CRMProviderType
    api_key: str
    account_name: Optional[str] = None
    account_id: Optional[str] = None
    instance_url: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    refresh_token: Optional[str] = None

class CRMCredentialInfo(BaseModel):
    provider: CRMProviderType
    display_name: str
    auth_type: str
    key_name: str
    key_placeholder: str
    documentation_url: str
    description: str
    scopes_required: list[str]
    setup_steps: list[str]

class ScoreReasonSchema(BaseModel):
    category: str
    points: float
    reason: str

class LeadEnrichmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_summary: Optional[str] = None
    role_summary: Optional[str] = None
    detected_technologies: list[str] = Field(default_factory=list)
    signals_json: list[dict[str, Any]] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)
    enriched_at: datetime

class CRMLeadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    # Group 1: Identity
    id: str
    workspace_id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: str
    phone: Optional[str] = None
    job_title: Optional[str] = None

    # Group 2: Company
    company_name: Optional[str] = None
    domain: Optional[str] = None
    industry: Optional[str] = None
    employee_count: Optional[int] = None
    location: Optional[str] = None
    revenue_band: Optional[str] = None

    # Group 3: CRM
    crm_connection_id: Optional[str] = None
    crm_record_id: Optional[str] = None
    provider_record_id: Optional[str] = None
    provider: Optional[str] = "HUBSPOT"
    owner_id: Optional[str] = None
    lifecycle_stage: Optional[str] = None
    source: Optional[str] = "CRM_SYNC"

    # Group 4: Context
    lead_notes: Optional[str] = None
    custom_fields: dict[str, Any] = Field(default_factory=dict)
    previous_interactions: list[dict[str, Any]] = Field(default_factory=list)

    # Group 5: Enrichment
    enrichment: Optional[LeadEnrichmentResponse] = None
    company_summary: Optional[str] = None
    role_summary: Optional[str] = None
    signals: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)
    enriched_at: Optional[datetime] = None

    # Group 6: Scoring
    icp_score: float = 0.0
    intent_score: float = 0.0
    total_score: float = 0.0
    score_band: str = "COLD"
    score_reasons_json: list[dict[str, Any]] = Field(default_factory=list)
    reasons: list[dict[str, Any]] = Field(default_factory=list)

    # Group 7: Consent / Suppression
    opt_out: bool = False
    do_not_contact: bool = False
    bounce_status: str = "NONE"
    suppression_reason: Optional[str] = None

    # Group 8: Campaign
    campaign_id: Optional[str] = None
    campaign_membership: Optional[str] = None
    current_step: int = 0
    state: str = "DISCOVERED"
    next_action_at: Optional[datetime] = None

    # Group 9: Conversation
    thread_id: Optional[str] = None
    last_inbound_at: Optional[datetime] = None
    last_outbound_at: Optional[datetime] = None
    sentiment_intent: Optional[str] = None

    # Group 10: Outcome
    is_qualified: bool = False
    qualification_status: str = "UNQUALIFIED"
    qualification_details: dict[str, Any] = Field(default_factory=dict)
    meeting_booked: bool = False
    disqualified: bool = False
    handoff_required: bool = False

    created_at: datetime
    updated_at: datetime

class CRMLeadListResponse(BaseModel):
    items: list[CRMLeadResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

class CRMLeadUpdateRequest(BaseModel):
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
    opt_out: Optional[bool] = None
    do_not_contact: Optional[bool] = None
    suppression_reason: Optional[str] = None
    lead_notes: Optional[str] = None
    meeting_booked: Optional[bool] = None
    disqualified: Optional[bool] = None
    handoff_required: Optional[bool] = None

class CRMLeadCreateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: str
    phone: Optional[str] = None
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    domain: Optional[str] = None
    industry: Optional[str] = None
    employee_count: Optional[int] = None
    location: Optional[str] = None
    revenue_band: Optional[str] = None
    lead_notes: Optional[str] = None
    source: Optional[str] = "MANUAL"

class CRMLeadOutcomeUpdateRequest(BaseModel):
    is_qualified: Optional[bool] = None
    meeting_booked: Optional[bool] = None
    disqualified: Optional[bool] = None
    handoff_required: Optional[bool] = None
    qualification_status: Optional[str] = None
    note: Optional[str] = None

