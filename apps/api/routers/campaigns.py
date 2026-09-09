from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from packages.analytics.funnel import get_workspace_funnel, FunnelReport

from apps.api.core.database import get_db
from apps.api.core.dependencies import get_current_workspace_context, require_role, WorkspaceContext
from packages.common.models.workspace import WorkspaceRole
from packages.common.models.campaign import (
    Campaign,
    CampaignStep,
    CampaignLead,
    ConversationEvent,
    CampaignState,
    LeadSequenceState
)
from packages.common.models.crm import CRMLead
from packages.common.schemas.campaign import (
    CampaignResponse,
    CampaignCreateRequest,
    CampaignUpdateRequest,
    CampaignLeadResponse,
    CampaignEnrollRequest,
    ConversationEventResponse
)
from packages.campaign.state_machine import CampaignStateMachine
from packages.campaign.scheduler import CampaignScheduler

router = APIRouter(prefix="/campaigns", tags=["Campaigns & Sequences"])

@router.get("", response_model=list[CampaignResponse])
async def list_campaigns(
    ctx: WorkspaceContext = Depends(get_current_workspace_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Lists all campaigns with their sequence steps and lead count summaries for the workspace.
    """
    stmt = (
        select(Campaign)
        .options(selectinload(Campaign.steps), selectinload(Campaign.leads))
        .where(Campaign.workspace_id == ctx.workspace_id)
        .order_by(Campaign.created_at.desc())
    )
    res = await db.execute(stmt)
    campaigns = res.scalars().all()

    result = []
    for c in campaigns:
        total = len(c.leads)
        active = sum(1 for l in c.leads if l.state in [LeadSequenceState.QUEUED, LeadSequenceState.WAITING, LeadSequenceState.READY, LeadSequenceState.SENT])
        completed = sum(1 for l in c.leads if l.state == LeadSequenceState.COMPLETED)

        result.append(
            CampaignResponse(
                id=c.id,
                workspace_id=c.workspace_id,
                name=c.name,
                status=c.status,
                objective=c.objective,
                config_json=c.config_json,
                steps=c.steps,
                total_leads=total,
                active_leads=active,
                completed_leads=completed,
                created_at=c.created_at,
                updated_at=c.updated_at
            )
        )
    return result

@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    payload: CampaignCreateRequest,
    ctx: WorkspaceContext = Depends(require_role([WorkspaceRole.OWNER, WorkspaceRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """
    Creates a new campaign sequence with specified step definitions.
    """
    campaign = Campaign(
        workspace_id=ctx.workspace_id,
        name=payload.name,
        objective=payload.objective,
        config_json=payload.config_json,
        status=CampaignState.DRAFT
    )
    db.add(campaign)
    await db.flush()

    for step_data in payload.steps:
        step = CampaignStep(
            campaign_id=campaign.id,
            step_number=step_data.step_number,
            delay_days=step_data.delay_days,
            delay_hours=step_data.delay_hours,
            prompt_instructions=step_data.prompt_instructions,
            template_config_json=step_data.template_config_json
        )
        db.add(step)

    await db.commit()

    # Reload with steps
    res = await db.execute(
        select(Campaign)
        .options(selectinload(Campaign.steps), selectinload(Campaign.leads))
        .where(Campaign.id == campaign.id)
    )
    c = res.scalar_one()
    return CampaignResponse(
        id=c.id,
        workspace_id=c.workspace_id,
        name=c.name,
        status=c.status,
        objective=c.objective,
        config_json=c.config_json,
        steps=c.steps,
        total_leads=0,
        active_leads=0,
        completed_leads=0,
        created_at=c.created_at,
        updated_at=c.updated_at
    )

@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: str,
    ctx: WorkspaceContext = Depends(get_current_workspace_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves campaign detail, steps, and enrollment totals.
    """
    stmt = (
        select(Campaign)
        .options(selectinload(Campaign.steps), selectinload(Campaign.leads))
        .where(
            Campaign.id == campaign_id,
            Campaign.workspace_id == ctx.workspace_id
        )
    )
    res = await db.execute(stmt)
    c = res.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")

    total = len(c.leads)
    active = sum(1 for l in c.leads if l.state in [LeadSequenceState.QUEUED, LeadSequenceState.WAITING, LeadSequenceState.READY, LeadSequenceState.SENT])
    completed = sum(1 for l in c.leads if l.state == LeadSequenceState.COMPLETED)

    return CampaignResponse(
        id=c.id,
        workspace_id=c.workspace_id,
        name=c.name,
        status=c.status,
        objective=c.objective,
        config_json=c.config_json,
        steps=c.steps,
        total_leads=total,
        active_leads=active,
        completed_leads=completed,
        created_at=c.created_at,
        updated_at=c.updated_at
    )

@router.patch("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: str,
    payload: CampaignUpdateRequest,
    ctx: WorkspaceContext = Depends(require_role([WorkspaceRole.OWNER, WorkspaceRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """
    Updates campaign configuration or properties.
    """
    stmt = (
        select(Campaign)
        .options(selectinload(Campaign.steps), selectinload(Campaign.leads))
        .where(
            Campaign.id == campaign_id,
            Campaign.workspace_id == ctx.workspace_id
        )
    )
    res = await db.execute(stmt)
    c = res.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if payload.name is not None:
        c.name = payload.name
    if payload.objective is not None:
        c.objective = payload.objective
    if payload.config_json is not None:
        c.config_json = payload.config_json
    if payload.status is not None:
        c.status = payload.status

    await db.commit()
    await db.refresh(c)

    total = len(c.leads)
    active = sum(1 for l in c.leads if l.state in [LeadSequenceState.QUEUED, LeadSequenceState.WAITING, LeadSequenceState.READY, LeadSequenceState.SENT])
    completed = sum(1 for l in c.leads if l.state == LeadSequenceState.COMPLETED)

    return CampaignResponse(
        id=c.id,
        workspace_id=c.workspace_id,
        name=c.name,
        status=c.status,
        objective=c.objective,
        config_json=c.config_json,
        steps=c.steps,
        total_leads=total,
        active_leads=active,
        completed_leads=completed,
        created_at=c.created_at,
        updated_at=c.updated_at
    )

@router.post("/{campaign_id}/launch", response_model=CampaignResponse)
async def launch_campaign(
    campaign_id: str,
    ctx: WorkspaceContext = Depends(require_role([WorkspaceRole.OWNER, WorkspaceRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """
    Transitions campaign to RUNNING and schedules initial step release for enrolled leads.
    """
    stmt = (
        select(Campaign)
        .options(selectinload(Campaign.steps), selectinload(Campaign.leads).selectinload(CampaignLead.lead))
        .where(
            Campaign.id == campaign_id,
            Campaign.workspace_id == ctx.workspace_id
        )
    )
    res = await db.execute(stmt)
    c = res.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if not c.steps:
        raise HTTPException(status_code=400, detail="Cannot launch campaign with no sequence steps")

    c.status = CampaignState.RUNNING

    # Set initial schedule for QUEUED leads
    now_utc = datetime.now(timezone.utc)
    for cl in c.leads:
        if cl.state == LeadSequenceState.QUEUED and cl.next_action_at is None:
            lead_tz = (cl.lead.custom_fields_json or {}).get("timezone", "UTC") if cl.lead else "UTC"
            # Schedule release within business hours
            cl.next_action_at = CampaignScheduler.calculate_next_send_time(
                lead_timezone=lead_tz,
                delay_days=0,
                delay_hours=0
            )

    await db.commit()
    await db.refresh(c)

    total = len(c.leads)
    active = sum(1 for l in c.leads if l.state in [LeadSequenceState.QUEUED, LeadSequenceState.WAITING, LeadSequenceState.READY, LeadSequenceState.SENT])
    completed = sum(1 for l in c.leads if l.state == LeadSequenceState.COMPLETED)

    return CampaignResponse(
        id=c.id,
        workspace_id=c.workspace_id,
        name=c.name,
        status=c.status,
        objective=c.objective,
        config_json=c.config_json,
        steps=c.steps,
        total_leads=total,
        active_leads=active,
        completed_leads=completed,
        created_at=c.created_at,
        updated_at=c.updated_at
    )

@router.post("/{campaign_id}/pause", response_model=CampaignResponse)
async def pause_campaign(
    campaign_id: str,
    ctx: WorkspaceContext = Depends(require_role([WorkspaceRole.OWNER, WorkspaceRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """
    Pauses an active campaign sequence.
    """
    stmt = (
        select(Campaign)
        .options(selectinload(Campaign.steps), selectinload(Campaign.leads))
        .where(
            Campaign.id == campaign_id,
            Campaign.workspace_id == ctx.workspace_id
        )
    )
    res = await db.execute(stmt)
    c = res.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")

    c.status = CampaignState.PAUSED
    await db.commit()
    await db.refresh(c)

    total = len(c.leads)
    active = sum(1 for l in c.leads if l.state in [LeadSequenceState.QUEUED, LeadSequenceState.WAITING, LeadSequenceState.READY, LeadSequenceState.SENT])
    completed = sum(1 for l in c.leads if l.state == LeadSequenceState.COMPLETED)

    return CampaignResponse(
        id=c.id,
        workspace_id=c.workspace_id,
        name=c.name,
        status=c.status,
        objective=c.objective,
        config_json=c.config_json,
        steps=c.steps,
        total_leads=total,
        active_leads=active,
        completed_leads=completed,
        created_at=c.created_at,
        updated_at=c.updated_at
    )

@router.post("/{campaign_id}/resume", response_model=CampaignResponse)
async def resume_campaign(
    campaign_id: str,
    ctx: WorkspaceContext = Depends(require_role([WorkspaceRole.OWNER, WorkspaceRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """
    Resumes a paused campaign sequence.
    """
    stmt = (
        select(Campaign)
        .options(selectinload(Campaign.steps), selectinload(Campaign.leads))
        .where(
            Campaign.id == campaign_id,
            Campaign.workspace_id == ctx.workspace_id
        )
    )
    res = await db.execute(stmt)
    c = res.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")

    c.status = CampaignState.RUNNING
    await db.commit()
    await db.refresh(c)

    total = len(c.leads)
    active = sum(1 for l in c.leads if l.state in [LeadSequenceState.QUEUED, LeadSequenceState.WAITING, LeadSequenceState.READY, LeadSequenceState.SENT])
    completed = sum(1 for l in c.leads if l.state == LeadSequenceState.COMPLETED)

    return CampaignResponse(
        id=c.id,
        workspace_id=c.workspace_id,
        name=c.name,
        status=c.status,
        objective=c.objective,
        config_json=c.config_json,
        steps=c.steps,
        total_leads=total,
        active_leads=active,
        completed_leads=completed,
        created_at=c.created_at,
        updated_at=c.updated_at
    )

@router.post("/{campaign_id}/enroll", response_model=list[CampaignLeadResponse], status_code=status.HTTP_201_CREATED)
async def enroll_leads(
    campaign_id: str,
    payload: CampaignEnrollRequest,
    ctx: WorkspaceContext = Depends(require_role([WorkspaceRole.OWNER, WorkspaceRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """
    Enrolls a list of CRM leads into this campaign with initial QUEUED sequence state.
    """
    # Verify campaign exists
    camp_res = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.workspace_id == ctx.workspace_id)
    )
    campaign = camp_res.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    enrolled = []
    for lead_id in payload.lead_ids:
        # Check if already enrolled
        existing = await db.execute(
            select(CampaignLead).where(
                CampaignLead.campaign_id == campaign_id,
                CampaignLead.lead_id == lead_id
            )
        )
        if existing.scalar_one_or_none():
            continue

        lead_res = await db.execute(
            select(CRMLead).where(CRMLead.id == lead_id, CRMLead.workspace_id == ctx.workspace_id)
        )
        crm_lead = lead_res.scalar_one_or_none()
        if not crm_lead:
            continue

        cl = CampaignLead(
            workspace_id=ctx.workspace_id,
            campaign_id=campaign_id,
            lead_id=lead_id,
            current_step_number=1,
            state=LeadSequenceState.QUEUED,
            next_action_at=None
        )
        db.add(cl)
        enrolled.append(cl)

    await db.commit()

    # Re-query enrolled leads with relationship
    res_list = []
    for cl in enrolled:
        await db.refresh(cl)
        lead_res = await db.execute(select(CRMLead).where(CRMLead.id == cl.lead_id))
        crm_lead = lead_res.scalar_one_or_none()
        res_list.append(
            CampaignLeadResponse(
                id=cl.id,
                workspace_id=cl.workspace_id,
                campaign_id=cl.campaign_id,
                lead_id=cl.lead_id,
                current_step_number=cl.current_step_number,
                state=cl.state,
                next_action_at=cl.next_action_at,
                lead_first_name=crm_lead.first_name if crm_lead else None,
                lead_last_name=crm_lead.last_name if crm_lead else None,
                lead_email=crm_lead.email if crm_lead else None,
                lead_company=crm_lead.company_name if crm_lead else None,
                created_at=cl.created_at,
                updated_at=cl.updated_at
            )
        )
    return res_list

@router.get("/{campaign_id}/leads", response_model=list[CampaignLeadResponse])
async def list_campaign_leads(
    campaign_id: str,
    ctx: WorkspaceContext = Depends(get_current_workspace_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Lists all enrolled leads and their current progression state for a campaign.
    """
    stmt = (
        select(CampaignLead)
        .options(selectinload(CampaignLead.lead))
        .where(
            CampaignLead.campaign_id == campaign_id,
            CampaignLead.workspace_id == ctx.workspace_id
        )
        .order_by(CampaignLead.created_at.desc())
    )
    res = await db.execute(stmt)
    leads = res.scalars().all()

    return [
        CampaignLeadResponse(
            id=cl.id,
            workspace_id=cl.workspace_id,
            campaign_id=cl.campaign_id,
            lead_id=cl.lead_id,
            current_step_number=cl.current_step_number,
            state=cl.state,
            next_action_at=cl.next_action_at,
            lead_first_name=cl.lead.first_name if cl.lead else None,
            lead_last_name=cl.lead.last_name if cl.lead else None,
            lead_email=cl.lead.email if cl.lead else None,
            lead_company=cl.lead.company_name if cl.lead else None,
            created_at=cl.created_at,
            updated_at=cl.updated_at
        )
        for cl in leads
    ]

@router.get("/{campaign_id}/events", response_model=list[ConversationEventResponse])
async def list_campaign_events(
    campaign_id: str,
    ctx: WorkspaceContext = Depends(get_current_workspace_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Lists the immutable 5-question audit events emitted for this campaign.
    """
    stmt = (
        select(ConversationEvent)
        .where(
            ConversationEvent.campaign_id == campaign_id,
            ConversationEvent.workspace_id == ctx.workspace_id
        )
        .order_by(ConversationEvent.created_at.desc())
        .limit(100)
    )
    res = await db.execute(stmt)
    return res.scalars().all()

@router.get("/{campaign_id}/analytics", response_model=FunnelReport)
async def get_campaign_analytics(
    campaign_id: str,
    date_from: Optional[datetime] = Query(default=None),
    date_to: Optional[datetime] = Query(default=None),
    ctx: WorkspaceContext = Depends(get_current_workspace_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns real-time sales funnel and conversion analytics for a specific campaign.
    """
    camp_res = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.workspace_id == ctx.workspace_id
        )
    )
    campaign = camp_res.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    funnel_report = await get_workspace_funnel(
        workspace_id=ctx.workspace_id,
        campaign_id=campaign_id,
        date_from=date_from,
        date_to=date_to,
        db=db
    )
    return funnel_report
