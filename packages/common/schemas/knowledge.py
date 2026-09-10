from datetime import datetime
from pydantic import BaseModel, HttpUrl, Field, ConfigDict
from packages.common.models.knowledge import ScanStatus

class WebsiteScanCreateRequest(BaseModel):
    url: str = Field(..., description="Target company website URL to scan")

class WebsiteScanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    url: str
    status: ScanStatus
    pages_discovered: int
    pages_crawled: int
    pages_failed: int
    error_message: str | None
    created_at: datetime
    updated_at: datetime

class BusinessProfileUpdateRequest(BaseModel):
    company_name: str | None = None
    legal_name: str | None = None
    description: str | None = None
    offerings: list | dict | None = None
    value_propositions: list | dict | None = None
    industries: list[str] | None = None
    icp_hints: dict | None = None
    pricing: dict | None = None
    features: list | dict | None = None
    faqs: list | None = None
    proof: list | None = None
    brand_voice: dict | None = None
    claims_policy: dict | None = None
    ctas: list | None = None

class BusinessProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    company_name: str
    legal_name: str | None
    description: str | None
    offerings: list | dict
    value_propositions: list | dict
    industries: list
    icp_hints: dict
    pricing: dict | None
    features: list | dict
    faqs: list
    proof: list
    brand_voice: dict
    claims_policy: dict
    ctas: list
    version: int
    confidence_score: float
    is_active: bool
    created_at: datetime
    updated_at: datetime

    # Section 4.1 Provenance & Policy fields
    policies: list = []
    contact_info: dict = {}
    requires_human_review: bool = False
    review_reasons: list[str] = []
    structured_facts: list = []

class KnowledgeSearchRequest(BaseModel):
    query: str
    top_k: int = 3

class ChunkSearchResult(BaseModel):
    chunk_id: str
    document_id: str
    content: str
    source_url: str
    title: str | None
    score: float
