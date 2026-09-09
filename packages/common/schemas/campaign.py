from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from packages.common.models.campaign import CampaignState, LeadSequenceState

class CampaignStepCreateRequest(BaseModel):
    step_number: int
    delay_days: int = Field(default=3, ge=0)
    delay_hours: int = Field(default=0, ge=0, le=23)
    prompt_instructions: Optional[str] = None
    template_config_json: dict[str, Any] = Field(default_factory=dict)

class CampaignStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    campaign_id: str
    step_number: int
    delay_days: int
    delay_hours: int
    prompt_instructions: Optional[str] = None
    template_config_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

class CampaignCreateRequest(BaseModel):
    name: str
    objective: str = "DEMO_BOOKING"
    config_json: dict[str, Any] = Field(default_factory=dict)
    steps: list[CampaignStepCreateRequest] = Field(default_factory=list)

class CampaignUpdateRequest(BaseModel):
    name: Optional[str] = None
    objective: Optional[str] = None
    config_json: Optional[dict[str, Any]] = None
    status: Optional[CampaignState] = None

class CampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    name: str
    status: CampaignState
    objective: str
    config_json: dict[str, Any] = Field(default_factory=dict)
    steps: list[CampaignStepResponse] = Field(default_factory=list)
    total_leads: int = 0
    active_leads: int = 0
    completed_leads: int = 0
    created_at: datetime
    updated_at: datetime

class CampaignLeadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    campaign_id: str
    lead_id: str
    current_step_number: int
    state: LeadSequenceState
    next_action_at: Optional[datetime] = None
    lead_first_name: Optional[str] = None
    lead_last_name: Optional[str] = None
    lead_email: Optional[str] = None
    lead_company: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class CampaignEnrollRequest(BaseModel):
    lead_ids: list[str]

class ConversationEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    lead_id: Optional[str] = None
    campaign_id: Optional[str] = None
    event_type: str
    rule_matched: Optional[str] = None
    model_version: Optional[str] = None
    prompt_version: Optional[str] = None
    knowledge_chunk_ids: list[str] = Field(default_factory=list)
    previous_state: Optional[str] = None
    new_state: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
