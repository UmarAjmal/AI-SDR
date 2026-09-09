from datetime import datetime
from pydantic import BaseModel, ConfigDict

class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    actor_id: str | None
    actor_email: str | None
    action: str
    resource_type: str
    resource_id: str | None
    payload: dict
    created_at: datetime

class AuditLogCreate(BaseModel):
    workspace_id: str
    actor_id: str | None = None
    actor_email: str | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    payload: dict = {}
