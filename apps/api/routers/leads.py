from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from apps.api.core.database import get_db
from apps.api.core.dependencies import get_current_workspace_context, require_role, WorkspaceContext
from packages.common.models.workspace import WorkspaceRole
from packages.common.models.crm import CRMLead, CRMConnection, CRMSyncStatus
from packages.common.models.email import EmailMessage, EmailThread
from packages.common.schemas.crm import (
    CRMLeadResponse,
    CRMLeadListResponse,
    CRMLeadUpdateRequest,
    CRMLeadCreateRequest,
    CRMLeadOutcomeUpdateRequest
)
from packages.common.models.knowledge import BusinessProfile
from packages.lead_intelligence.scorer import LeadScorer
from apps.worker.tasks.crm_tasks import sync_crm_leads_task
from apps.worker.tasks.crm_sync import sync_lead_outcome_to_crm_task
from packages.ai.agents.qualification_agent import QualificationAgent

router = APIRouter(prefix="/leads", tags=["Canonical Lead Intelligence"])

@router.get("", response_model=CRMLeadListResponse)
async def list_canonical_leads(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    score_band: Optional[str] = Query(None, description="HOT (>=80), WARM (50-79), COLD (<50)"),
    qualification_status: Optional[str] = Query(None, description="QUALIFIED, DEVELOPING, UNQUALIFIED"),
    industry: Optional[str] = None,
    opt_out: Optional[bool] = None,
    search: Optional[str] = None,
    ctx: WorkspaceContext = Depends(get_current_workspace_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Lists canonical leads for the authenticated workspace with rich filtering and pagination.
    """
    query = select(CRMLead).where(CRMLead.workspace_id == ctx.workspace_id)

    # Qualification status filter
    if qualification_status:
        query = query.where(CRMLead.qualification_status == qualification_status.upper())

    # Score band filter
    if score_band:
        sb = score_band.upper()
        if sb == "HOT":
            query = query.where(CRMLead.total_score >= 80.0)
        elif sb == "WARM":
            query = query.where(CRMLead.total_score >= 50.0, CRMLead.total_score < 80.0)
        elif sb == "COLD":
            query = query.where(CRMLead.total_score < 50.0)

    # Industry filter
    if industry:
        query = query.where(CRMLead.industry.ilike(f"%{industry}%"))

    # Opt-out filter
    if opt_out is not None:
        query = query.where(CRMLead.opt_out == opt_out)

    # Search filter (across name, email, company, job title)
    if search:
        s = f"%{search}%"
        query = query.where(
            or_(
                CRMLead.email.ilike(s),
                CRMLead.first_name.ilike(s),
                CRMLead.last_name.ilike(s),
                CRMLead.company_name.ilike(s),
                CRMLead.job_title.ilike(s)
            )
        )

    # Total count query
    count_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar_one()

    # Sort descending by lead total score
    query = query.order_by(CRMLead.total_score.desc(), CRMLead.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    leads_res = await db.execute(query)
    items = leads_res.scalars().all()

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return CRMLeadListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

@router.post("", response_model=CRMLeadResponse, status_code=status.HTTP_201_CREATED)
async def create_canonical_lead(
    payload: CRMLeadCreateRequest,
    ctx: WorkspaceContext = Depends(require_role([WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.MEMBER])),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually creates a new lead, executes deterministic ICP scoring, and stores it in the workspace.
    """
    clean_email = payload.email.lower().strip()
    existing = await db.execute(
        select(CRMLead).where(
            CRMLead.email == clean_email,
            CRMLead.workspace_id == ctx.workspace_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="A lead with this email address already exists in your workspace")

    # Extract domain from email
    domain = clean_email.split("@")[-1] if "@" in clean_email else None

    # Fetch workspace business profile for target ICP alignment
    prof_res = await db.execute(
        select(BusinessProfile).where(BusinessProfile.workspace_id == ctx.workspace_id)
    )
    profile = prof_res.scalar_one_or_none()

    # Pre-populate lead object
    new_lead = CRMLead(
        workspace_id=ctx.workspace_id,
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=clean_email,
        phone=payload.phone,
        job_title=payload.job_title,
        company_name=payload.company_name,
        domain=domain,
        industry=payload.industry,
        employee_count=payload.employee_count,
        location=payload.location,
        lead_notes=payload.lead_notes,
        opt_out=False,
        do_not_contact=False,
        qualification_status="UNQUALIFIED"
    )

    # Deterministic Lead Scoring
    score_result = LeadScorer.evaluate_lead_score(new_lead, profile)
    new_lead.icp_score = score_result.icp_score
    new_lead.intent_score = score_result.intent_score
    new_lead.total_score = score_result.total_score
    new_lead.score_reasons_json = [
        {"category": r.category, "points": r.points, "reason": r.reason}
        for r in score_result.reasons
    ]

    db.add(new_lead)
    await db.commit()
    await db.refresh(new_lead)
    return new_lead

@router.get("/{lead_id}", response_model=CRMLeadResponse)
async def get_canonical_lead(
    lead_id: str,
    ctx: WorkspaceContext = Depends(get_current_workspace_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves detailed canonical lead profile, ICP score breakdown, and enrichment signals.
    """
    res = await db.execute(
        select(CRMLead).where(
            CRMLead.id == lead_id,
            CRMLead.workspace_id == ctx.workspace_id
        )
    )
    lead = res.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead

@router.put("/{lead_id}", response_model=CRMLeadResponse)
async def update_canonical_lead(
    lead_id: str,
    payload: CRMLeadUpdateRequest,
    ctx: WorkspaceContext = Depends(require_role([WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.MEMBER])),
    db: AsyncSession = Depends(get_db)
):
    """
    Updates lead information, notes, or toggles manual opt_out / do_not_contact suppression.
    """
    res = await db.execute(
        select(CRMLead).where(
            CRMLead.id == lead_id,
            CRMLead.workspace_id == ctx.workspace_id
        )
    )
    lead = res.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    update_dict = payload.model_dump(exclude_unset=True)
    for field, val in update_dict.items():
        setattr(lead, field, val)

    # If opt_out was set to true, also enforce do_not_contact
    if payload.opt_out is True:
        lead.do_not_contact = True

    await db.commit()
    await db.refresh(lead)
    return lead

@router.post("/import", status_code=status.HTTP_202_ACCEPTED)
async def trigger_leads_import(
    connection_id: Optional[str] = None,
    ctx: WorkspaceContext = Depends(require_role([WorkspaceRole.OWNER, WorkspaceRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """
    Initiates asynchronous CRM leads sync. If connection_id is omitted, syncs primary active connection.
    """
    if connection_id:
        res = await db.execute(
            select(CRMConnection).where(
                CRMConnection.id == connection_id,
                CRMConnection.workspace_id == ctx.workspace_id
            )
        )
        conn = res.scalar_one_or_none()
    else:
        res = await db.execute(
            select(CRMConnection).where(
                CRMConnection.workspace_id == ctx.workspace_id,
                CRMConnection.sync_status != CRMSyncStatus.REVOKED
            )
        )
        conn = res.scalars().first()

    if not conn:
        raise HTTPException(status_code=404, detail="No active CRM connection found to import from")

    conn.sync_status = CRMSyncStatus.SYNCING
    await db.commit()

    try:
        sync_crm_leads_task.delay(
            workspace_id=ctx.workspace_id,
            connection_id=conn.id
        )
    except Exception:
        pass

    return {
        "message": "Lead import initiated in background",
        "connection_id": conn.id,
        "provider": conn.provider
    }

@router.post("/{lead_id}/qualify", response_model=CRMLeadResponse)
async def trigger_lead_qualification(
    lead_id: str,
    ctx: WorkspaceContext = Depends(require_role([WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.MEMBER])),
    db: AsyncSession = Depends(get_db)
):
    """
    Evaluates AI Lead Qualification (NFAT Framework: Need, Fit, Authority, Timing).
    Updates qualification status and triggers CRM sync-back if qualified.
    """
    res = await db.execute(
        select(CRMLead).where(
            CRMLead.id == lead_id,
            CRMLead.workspace_id == ctx.workspace_id
        )
    )
    lead = res.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Fetch email messages for conversation history
    msg_res = await db.execute(
        select(EmailMessage).join(
            EmailThread, EmailMessage.thread_id == EmailThread.id
        ).where(
            EmailThread.lead_id == lead.id,
            EmailThread.workspace_id == ctx.workspace_id
        ).order_by(EmailMessage.created_at.asc())
    )
    messages = msg_res.scalars().all()

    if messages:
        thread_history = "\n".join([
            f"[{msg.direction.value.upper()}] {msg.body_text or ''}" for msg in messages
        ])
    else:
        thread_history = f"Lead {lead.first_name} {lead.last_name} ({lead.job_title} at {lead.company_name}). Notes: {lead.notes or 'No prior notes'}"

    # Evaluate via QualificationAgent
    qual_res = await QualificationAgent.evaluate_lead_qualification(
        lead=lead,
        thread_history=thread_history,
        workspace_id=ctx.workspace_id
    )

    lead.qualification_status = qual_res.qualification_status
    lead.qualification_details = qual_res.model_dump()
    lead.is_qualified = (qual_res.qualification_status == "QUALIFIED")

    await db.commit()
    await db.refresh(lead)

    # If qualified, trigger async CRM sync-back
    if lead.is_qualified:
        try:
            sync_lead_outcome_to_crm_task.delay(
                workspace_id=ctx.workspace_id,
                lead_id=str(lead.id)
            )
        except Exception:
            pass

    return lead

@router.post("/{lead_id}/outcome", response_model=CRMLeadResponse)
async def update_lead_outcome(
    lead_id: str,
    payload: CRMLeadOutcomeUpdateRequest,
    ctx: WorkspaceContext = Depends(require_role([WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.MEMBER])),
    db: AsyncSession = Depends(get_db)
):
    """
    Updates canonical lead outcome states: meeting_booked, is_qualified, disqualified, handoff_required.
    Triggers bidirectional CRM sync-back to reflect state in connected CRM.
    """
    res = await db.execute(
        select(CRMLead).where(
            CRMLead.id == lead_id,
            CRMLead.workspace_id == ctx.workspace_id
        )
    )
    lead = res.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    if payload.meeting_booked is not None:
        lead.meeting_booked = payload.meeting_booked
        if payload.meeting_booked:
            lead.qualification_status = "QUALIFIED"
            lead.is_qualified = True
    if payload.is_qualified is not None:
        lead.is_qualified = payload.is_qualified
        if payload.is_qualified:
            lead.qualification_status = "QUALIFIED"
    if payload.disqualified is not None:
        lead.disqualified = payload.disqualified
        if payload.disqualified:
            lead.qualification_status = "DISQUALIFIED"
            lead.is_qualified = False
    if payload.handoff_required is not None:
        lead.handoff_required = payload.handoff_required
    if payload.qualification_status is not None:
        lead.qualification_status = payload.qualification_status.upper()
        lead.is_qualified = (lead.qualification_status == "QUALIFIED")

    await db.commit()
    await db.refresh(lead)

    # Trigger async CRM sync-back
    try:
        sync_lead_outcome_to_crm_task.delay(
            workspace_id=ctx.workspace_id,
            lead_id=str(lead.id)
        )
    except Exception:
        async def _run_local_sync_back():
            try:
                from packages.crm.sync_service import CRMSyncService
                from apps.api.core.database import AsyncSessionLocal
                async with AsyncSessionLocal() as session:
                    await CRMSyncService.sync_lead_back_to_crm(
                        workspace_id=ctx.workspace_id,
                        lead_id=str(lead.id),
                        db=session
                    )
            except Exception:
                pass
        import asyncio
        asyncio.create_task(_run_local_sync_back())

    return lead

