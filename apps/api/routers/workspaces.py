from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.api.core.database import get_db
from apps.api.core.dependencies import get_current_user, get_current_workspace_context, require_role, WorkspaceContext
from packages.common.models.user import User
from packages.common.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from packages.common.models.audit import AuditLog
from packages.common.schemas.workspace import WorkspaceCreateRequest, WorkspaceUpdateRequest, WorkspaceResponse

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])

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
    workspace = Workspace(
        name=payload.name,
        domain=payload.domain,
        settings=payload.settings
    )
    db.add(workspace)
    await db.flush()

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user.id,
        role=WorkspaceRole.OWNER
    )
    db.add(member)

    audit = AuditLog(
        workspace_id=workspace.id,
        actor_id=user.id,
        actor_email=user.email,
        action="WORKSPACE_CREATED",
        resource_type="workspace",
        resource_id=workspace.id,
        payload={"name": workspace.name}
    )
    db.add(audit)
    await db.commit()
    await db.refresh(workspace)

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
