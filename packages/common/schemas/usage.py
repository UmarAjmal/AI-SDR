from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict
from packages.common.models.usage import UsageEventType

class UsageEventCreate(BaseModel):
    event_type: UsageEventType
    units: int = Field(default=1, ge=1)
    cost_estimate_usd: Decimal = Field(default=Decimal("0.000000"))
    metadata_json: dict = Field(default_factory=dict)

class UsageEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    event_type: UsageEventType
    units: int
    cost_estimate_usd: Decimal
    metadata_json: dict
    created_at: datetime

class UsageSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    workspace_id: str
    total_events: int
    total_units: int
    total_cost_usd: Decimal
    event_breakdown: dict[str, int]
    model_breakdown: dict[str, int] = Field(default_factory=dict)
    spending_limit_usd: Decimal | None = None
    spending_cap_exceeded: bool = False
    spending_percentage: float = 0.0
    cost_per_conversation_usd: Decimal = Field(default=Decimal("0.000000"))
    cost_per_meeting_usd: Decimal = Field(default=Decimal("0.000000"))
