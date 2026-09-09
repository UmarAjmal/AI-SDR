from decimal import Decimal
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from apps.api.core.database import get_db
from apps.api.core.dependencies import get_current_workspace_context, WorkspaceContext
from packages.common.models.usage import UsageEvent
from packages.common.schemas.usage import UsageSummaryResponse, UsageEventCreate, UsageEventResponse

router = APIRouter(prefix="/usage", tags=["Usage & Metering"])

from packages.common.models.workspace import Workspace
from packages.common.models.calendar import Appointment, AppointmentStatus
from packages.common.models.email import EmailMessage, MessageDirection

@router.get("/summary", response_model=UsageSummaryResponse)
async def get_usage_summary(
    ctx: WorkspaceContext = Depends(get_current_workspace_context),
    db: AsyncSession = Depends(get_db)
):
    # CRITICAL: Always strictly filter by ctx.workspace_id
    events_query = select(UsageEvent).where(UsageEvent.workspace_id == ctx.workspace_id)
    result = await db.execute(events_query)
    events = result.scalars().all()

    total_events = len(events)
    total_units = sum(e.units for e in events)
    total_cost = sum((e.cost_estimate_usd for e in events), Decimal("0.000000"))

    breakdown: dict[str, int] = {}
    model_breakdown: dict[str, int] = {}
    for e in events:
        etype = e.event_type.value
        breakdown[etype] = breakdown.get(etype, 0) + e.units
        meta = e.metadata_json or {}
        if "model" in meta:
            m_name = meta["model"]
            model_breakdown[m_name] = model_breakdown.get(m_name, 0) + e.units

    # Fetch workspace spending limits
    ws_res = await db.execute(select(Workspace).where(Workspace.id == ctx.workspace_id))
    ws = ws_res.scalar_one_or_none()
    spending_limit = None
    spending_exceeded = False
    spending_pct = 0.0

    if ws and ws.settings:
        raw_limit = ws.settings.get("spending_limit_usd")
        if raw_limit is not None:
            spending_limit = Decimal(str(raw_limit))
            if spending_limit > Decimal("0"):
                spending_pct = float(round((total_cost / spending_limit) * Decimal("100"), 2))
                spending_exceeded = total_cost >= spending_limit

    # Cost per conversation and meeting
    inbound_res = await db.execute(
        select(func.count(EmailMessage.id)).where(
            EmailMessage.workspace_id == ctx.workspace_id,
            EmailMessage.direction == MessageDirection.INBOUND
        )
    )
    inbound_count = inbound_res.scalar_one_or_none() or 0
    cost_per_conv = (total_cost / Decimal(str(inbound_count))).quantize(Decimal("0.000001")) if inbound_count > 0 else Decimal("0.000000")

    appt_res = await db.execute(
        select(func.count(Appointment.id)).where(
            Appointment.workspace_id == ctx.workspace_id,
            Appointment.status != AppointmentStatus.CANCELLED
        )
    )
    appt_count = appt_res.scalar_one_or_none() or 0
    cost_per_meeting = (total_cost / Decimal(str(appt_count))).quantize(Decimal("0.000001")) if appt_count > 0 else Decimal("0.000000")

    return UsageSummaryResponse(
        workspace_id=ctx.workspace_id,
        total_events=total_events,
        total_units=total_units,
        total_cost_usd=total_cost,
        event_breakdown=breakdown,
        model_breakdown=model_breakdown,
        spending_limit_usd=spending_limit,
        spending_cap_exceeded=spending_exceeded,
        spending_percentage=spending_pct,
        cost_per_conversation_usd=cost_per_conv,
        cost_per_meeting_usd=cost_per_meeting
    )

@router.post("/events", response_model=UsageEventResponse, status_code=status.HTTP_201_CREATED)
async def log_usage_event(
    payload: UsageEventCreate,
    ctx: WorkspaceContext = Depends(get_current_workspace_context),
    db: AsyncSession = Depends(get_db)
):
    event = UsageEvent(
        workspace_id=ctx.workspace_id,
        event_type=payload.event_type,
        units=payload.units,
        cost_estimate_usd=payload.cost_estimate_usd,
        metadata_json=payload.metadata_json
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event
