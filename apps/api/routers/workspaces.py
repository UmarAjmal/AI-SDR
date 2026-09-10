import asyncio
import logging
import urllib.parse
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.api.core.database import get_db, AsyncSessionLocal
from apps.api.core.dependencies import get_current_user, get_current_workspace_context, require_role, WorkspaceContext
from packages.common.models.user import User
from packages.common.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from packages.common.models.knowledge import WebsiteScan, ScanStatus
from packages.common.models.audit import AuditLog
from packages.common.schemas.workspace import WorkspaceCreateRequest, WorkspaceUpdateRequest, WorkspaceResponse
from packages.website_intelligence.crawler_service import WebsiteCrawlerService
from apps.worker.tasks.crawler_tasks import run_website_scan_task

logger = logging.getLogger("codenter.workspaces")

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])

async def _background_website_scan(workspace_id: str, scan_id: str, base_url: str):
    """Fallback local asynchronous execution of the Website Intelligence crawl pipeline."""
    try:
        async with AsyncSessionLocal() as session:
            await WebsiteCrawlerService.run_scan(
                workspace_id=workspace_id,
                scan_id=scan_id,
                base_url=base_url,
                db=session
            )
            logger.info(f"Background website crawl and business profile extraction complete for {base_url}")
    except Exception as e:
        logger.error(f"Background website scan error for {base_url}: {e}")

@router.get("", response_model=list[WorkspaceResponse])
async def list_user_workspaces(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Workspace)
        .join(WorkspaceMember, Workspace.id == WorkspaceMember.workspace_id)
        .where(WorkspaceMember.user_id == user.id)
    )
    return result.scalars().all()

@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    payload: WorkspaceCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. Normalize Website URL and extract clean domain
    raw_url = payload.website_url.strip()
    if not raw_url.startswith("http://") and not raw_url.startswith("https://"):
        raw_url = f"https://{raw_url}"
    
    parsed = urllib.parse.urlparse(raw_url)
    extracted_domain = parsed.netloc.lower()
    if extracted_domain.startswith("www."):
        extracted_domain = extracted_domain[4:]
    
    domain_val = payload.domain or extracted_domain

    # 2. Persist Workspace in Supabase
    workspace = Workspace(
        name=payload.name,
        domain=domain_val,
        website_url=raw_url,
        settings=payload.settings
    )
    db.add(workspace)
    await db.flush()

    # 3. Add current user as OWNER member
    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user.id,
        role=WorkspaceRole.OWNER
    )
    db.add(member)

    # 4. Record Audit Log
    audit = AuditLog(
        workspace_id=workspace.id,
        actor_id=user.id,
        actor_email=user.email,
        action="WORKSPACE_CREATED",
        resource_type="workspace",
        resource_id=workspace.id,
        payload={"name": workspace.name, "website_url": raw_url, "domain": domain_val}
    )
    db.add(audit)

    # 5. Initialize Section 4 Website Scan for Golden Path Step 2
    scan = WebsiteScan(
        workspace_id=workspace.id,
        url=raw_url,
        status=ScanStatus.PENDING
    )
    db.add(scan)
    await db.commit()
    await db.refresh(workspace)

    # 6. Immediately trigger the Crawl Pipeline in the background non-blockingly
    asyncio.create_task(_background_website_scan(workspace.id, scan.id, raw_url))
    logger.info(f"Spawned background crawl task for new workspace {workspace.id} ({raw_url})")

    return workspace

@router.get("/current", response_model=WorkspaceResponse)
async def get_current_workspace(
    ctx: WorkspaceContext = Depends(get_current_workspace_context),
    db: AsyncSession = Depends(get_db)
):
    # CRITICAL: Always scoped to current workspace context
    result = await db.execute(select(Workspace).where(Workspace.id == ctx.workspace_id))
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Active workspace not found")
    return workspace

@router.put("/current", response_model=WorkspaceResponse)
async def update_current_workspace(
    payload: WorkspaceUpdateRequest,
    ctx: WorkspaceContext = Depends(require_role([WorkspaceRole.OWNER, WorkspaceRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Workspace).where(Workspace.id == ctx.workspace_id))
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Active workspace not found")

    if payload.name is not None:
        workspace.name = payload.name
    if payload.website_url is not None:
        raw_url = payload.website_url.strip()
        if not raw_url.startswith("http://") and not raw_url.startswith("https://"):
            raw_url = f"https://{raw_url}"
        workspace.website_url = raw_url
        if payload.domain is None:
            parsed = urllib.parse.urlparse(raw_url)
            dom = parsed.netloc.lower()
            if dom.startswith("www."):
                dom = dom[4:]
            workspace.domain = dom
    if payload.domain is not None:
        workspace.domain = payload.domain
    if payload.settings is not None:
        workspace.settings = {**workspace.settings, **payload.settings}

    audit = AuditLog(
        workspace_id=ctx.workspace_id,
        actor_id=ctx.user_id,
        actor_email=ctx.user_email,
        action="WORKSPACE_UPDATED",
        resource_type="workspace",
        resource_id=workspace.id,
        payload=payload.model_dump(exclude_unset=True)
    )
    db.add(audit)
    await db.commit()
    await db.refresh(workspace)

    return workspace
