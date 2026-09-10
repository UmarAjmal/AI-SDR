from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from packages.common.models.workspace import WorkspaceRole

class WorkspaceCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    website_url: str = Field(..., min_length=3, max_length=512, description="Authoritative corporate website URL for AI training")
    domain: str | None = None
    settings: dict = Field(default_factory=dict)

class WorkspaceUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=100)
    website_url: str | None = None
    domain: str | None = None
    settings: dict | None = None

class WorkspaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    domain: str | None
    website_url: str | None = None
    settings: dict
    created_at: datetime
    updated_at: datetime

class WorkspaceMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    user_id: str
    role: WorkspaceRole
    created_at: datetime
