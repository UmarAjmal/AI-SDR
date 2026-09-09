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

class ScoreReasonSchema(BaseModel):
    category: str
    points: float
    reason: str

class CRMLeadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    crm_connection_id: Optional[str] = None
    crm_record_id: Optional[str] = None
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
    lifecycle_stage: Optional[str] = None
    opt_out: bool
    do_not_contact: bool
    bounce_status: str
    icp_score: float
    intent_score: float
    total_score: float
    score_reasons_json: list[dict[str, Any]] = Field(default_factory=list)
    custom_fields: dict[str, Any] = Field(default_factory=dict)
    qualification_status: str = "UNQUALIFIED"
    qualification_details: dict[str, Any] = Field(default_factory=dict)
    is_qualified: bool = False
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
    industry: Optional[str] = None
    employee_count: Optional[int] = None
    location: Optional[str] = None
    opt_out: Optional[bool] = None
    do_not_contact: Optional[bool] = None
    lead_notes: Optional[str] = None

class CRMLeadCreateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: str
    phone: Optional[str] = None
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    industry: Optional[str] = None
    employee_count: Optional[int] = None
    location: Optional[str] = None
    lead_notes: Optional[str] = None

