import enum
from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict

class RecommendedAction(str, enum.Enum):
    SEND = "SEND"
    HUMAN_REVIEW = "HUMAN_REVIEW"

class OutboundEmailDraft(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    subject: str = Field(description="Personalized email subject line")
    body: str = Field(description="Concise email body in plain text or clean semantic HTML")
    personalization_facts: list[str] = Field(default_factory=list, description="Specific lead/company facts referenced")
    cta: str = Field(description="Clear, frictionless call-to-action")
    claims_used: list[str] = Field(default_factory=list, description="Factual claims and metrics quoted")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    risk_flags: list[str] = Field(default_factory=list, description="Risk flags such as unverified claims or prohibited guarantees")
    recommended_action: RecommendedAction = Field(default=RecommendedAction.SEND, description="SEND or HUMAN_REVIEW")

class ModelUsageTelemetry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    model: str
    prompt_version: str = "v1.0"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    workspace_id: Optional[str] = None
    fallback_triggered: bool = False

class ClaimVerificationResult(BaseModel):
    is_grounded: bool
    verified_claims: list[str] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    prohibited_claims: list[str] = Field(default_factory=list)
    fake_research_detected: bool = False
    confidence: float = 1.0
    recommended_action: RecommendedAction = RecommendedAction.SEND
    risk_flags: list[str] = Field(default_factory=list)

class IntentClassificationResult(BaseModel):
    intent: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    suggested_action: str
    extracted_entities: dict[str, Any] = Field(default_factory=dict)
    requires_human_review: bool = False

class InboundReplyDraft(BaseModel):
    subject: str
    body: str
    citations: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    requires_human_review: bool = False
    reasoning: str = ""

class DraftGenerationRequest(BaseModel):
    lead_id: str
    campaign_step_id: Optional[str] = None
    custom_instructions: Optional[str] = None

class DraftGenerationResponse(BaseModel):
    draft: OutboundEmailDraft
    telemetry: ModelUsageTelemetry
    knowledge_chunk_ids: list[str] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
