import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from packages.common.models.usage import UsageEvent, UsageEventType
from packages.common.models.workspace import Workspace
from packages.common.models.campaign import Campaign, CampaignState
from packages.common.models.audit import AuditLog

logger = logging.getLogger("codenter.ai.metering")

# Pricing matrix per 1,000,000 units / tokens (USD)
MODEL_PRICING_TABLE = {
    "claude-3-5-sonnet-20241022": {"prompt": Decimal("3.00"), "completion": Decimal("15.00"), "blended": Decimal("9.00")},
    "claude-3-5-sonnet": {"prompt": Decimal("3.00"), "completion": Decimal("15.00"), "blended": Decimal("9.00")},
    "gpt-4o": {"prompt": Decimal("5.00"), "completion": Decimal("15.00"), "blended": Decimal("10.00")},
    "gpt-4o-mini": {"prompt": Decimal("0.15"), "completion": Decimal("0.60"), "blended": Decimal("0.375")},
    "text-embedding-3-small": {"prompt": Decimal("0.02"), "completion": Decimal("0.02"), "blended": Decimal("0.02")},
    "text-embedding-3-large": {"prompt": Decimal("0.13"), "completion": Decimal("0.13"), "blended": Decimal("0.13")},
}

# Unit costs for non-token operational events (USD per unit)
EVENT_UNIT_COSTS = {
    UsageEventType.EMAIL_SENT.value: Decimal("0.001"),
    UsageEventType.BROWSER_RENDER.value: Decimal("0.005"),
    UsageEventType.ENRICHMENT_CALL.value: Decimal("0.020"),
    UsageEventType.MODEL_TOKENS.value: Decimal("0.000009"),  # Fallback default
}


def calculate_cost(
    event_type: str,
    units: int = 1,
    model: Optional[str] = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
) -> Decimal:
    """
    Calculates cost in USD as a Decimal rounded to 6 decimal places.
    Supports split prompt/completion token calculation, model-based calculation,
    or event-type unit pricing.
    """
    if units <= 0 and prompt_tokens <= 0 and completion_tokens <= 0:
        return Decimal("0.000000")

    # If detailed prompt/completion tokens are provided with a known model:
    if model and (prompt_tokens > 0 or completion_tokens > 0):
        normalized_model = model.lower()
        pricing = MODEL_PRICING_TABLE.get(normalized_model, MODEL_PRICING_TABLE["claude-3-5-sonnet"])
        prompt_cost = (Decimal(str(prompt_tokens)) / Decimal("1000000")) * pricing["prompt"]
        completion_cost = (Decimal(str(completion_tokens)) / Decimal("1000000")) * pricing["completion"]
        total = prompt_cost + completion_cost
        return total.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

    # If model is provided with total units:
    if model:
        normalized_model = model.lower()
        pricing = MODEL_PRICING_TABLE.get(normalized_model, MODEL_PRICING_TABLE["claude-3-5-sonnet"])
        rate = pricing.get("blended", Decimal("9.00"))
        total = (Decimal(str(units)) / Decimal("1000000")) * rate
        return total.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

    # Fallback to event-type unit pricing
    normalized_event = event_type.value if hasattr(event_type, "value") else str(event_type).upper()
    unit_cost = EVENT_UNIT_COSTS.get(normalized_event, Decimal("0.000000"))
    total = Decimal(str(units)) * unit_cost
    return total.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


async def enforce_spending_limits(workspace_id: str, db: AsyncSession) -> dict[str, Any]:
    """
    Checks total workspace spend against spending limits configured on Workspace.settings.
    If spending cap is exceeded, pauses all active campaigns in the workspace and logs an AuditLog.
    """
    # 1. Query total expenditure
    spend_query = select(func.coalesce(func.sum(UsageEvent.cost_estimate_usd), 0)).where(
        UsageEvent.workspace_id == workspace_id
    )
    res = await db.execute(spend_query)
    current_spend = Decimal(str(res.scalar_one()))

    # 2. Fetch workspace
    ws_query = select(Workspace).where(Workspace.id == workspace_id)
    ws_res = await db.execute(ws_query)
    workspace = ws_res.scalar_one_or_none()

    if not workspace:
        return {
            "spending_cap_exceeded": False,
            "current_spend_usd": current_spend,
            "spending_limit_usd": None,
            "paused_campaign_count": 0,
        }

    settings = workspace.settings or {}
    spending_limit = settings.get("spending_limit_usd")
    if spending_limit is not None:
        limit_decimal = Decimal(str(spending_limit))
    else:
        # Default unlimited unless explicitly set
        limit_decimal = None

    if limit_decimal is not None and current_spend >= limit_decimal:
        logger.warning(
            f"Workspace {workspace_id} spending cap exceeded: {current_spend} >= {limit_decimal}. Pausing campaigns."
        )

        # Pause active campaigns
        camp_query = select(Campaign).where(
            Campaign.workspace_id == workspace_id,
            Campaign.status.in_([CampaignState.RUNNING, CampaignState.SCHEDULED])
        )
        camp_res = await db.execute(camp_query)
        active_campaigns = camp_res.scalars().all()

        paused_ids = []
        for camp in active_campaigns:
            camp.status = CampaignState.PAUSED
            paused_ids.append(camp.id)

        # Create audit log
        audit_log = AuditLog(
            workspace_id=workspace_id,
            action="SPENDING_CAP_EXCEEDED_CAMPAIGNS_PAUSED",
            resource_type="WORKSPACE",
            resource_id=workspace_id,
            payload={
                "current_spend_usd": str(current_spend),
                "spending_limit_usd": str(limit_decimal),
                "paused_campaign_ids": paused_ids,
            }
        )
        db.add(audit_log)
        await db.commit()

        return {
            "spending_cap_exceeded": True,
            "current_spend_usd": current_spend,
            "spending_limit_usd": limit_decimal,
            "paused_campaign_count": len(paused_ids),
            "paused_campaign_ids": paused_ids,
        }

    return {
        "spending_cap_exceeded": False,
        "current_spend_usd": current_spend,
        "spending_limit_usd": limit_decimal,
        "paused_campaign_count": 0,
        "paused_campaign_ids": [],
    }


async def record_usage(
    workspace_id: str,
    event_type: str | UsageEventType,
    units: int = 1,
    model: Optional[str] = None,
    metadata: Optional[dict] = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    db: Optional[AsyncSession] = None,
) -> UsageEvent:
    """
    Calculates estimated cost in USD based on model pricing table or unit pricing,
    persists to usage_events table, and verifies workspace spending caps.
    """
    # 1. Resolve UsageEventType
    if isinstance(event_type, UsageEventType):
        resolved_etype = event_type
    else:
        str_val = str(event_type).upper()
        if "TOKEN" in str_val or model:
            resolved_etype = UsageEventType.MODEL_TOKENS
        elif "EMAIL" in str_val:
            resolved_etype = UsageEventType.EMAIL_SENT
        elif "BROWSER" in str_val or "RENDER" in str_val:
            resolved_etype = UsageEventType.BROWSER_RENDER
        elif "ENRICH" in str_val:
            resolved_etype = UsageEventType.ENRICHMENT_CALL
        else:
            resolved_etype = UsageEventType.MODEL_TOKENS

    # 2. Compute cost
    cost = calculate_cost(
        event_type=resolved_etype.value,
        units=units,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )

    # 3. Build metadata
    meta = dict(metadata or {})
    if model:
        meta["model"] = model
    if prompt_tokens > 0:
        meta["prompt_tokens"] = prompt_tokens
    if completion_tokens > 0:
        meta["completion_tokens"] = completion_tokens

    event = UsageEvent(
        workspace_id=workspace_id,
        event_type=resolved_etype,
        units=units,
        cost_estimate_usd=cost,
        metadata_json=meta,
    )

    if db is not None:
        db.add(event)
        await db.commit()
        await db.refresh(event)

        # Check spending limits and enforce pause if necessary
        await enforce_spending_limits(workspace_id=workspace_id, db=db)

    return event
