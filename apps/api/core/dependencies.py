from typing import Sequence
from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, ConfigDict

from apps.api.core.database import get_db
from apps.api.core.security import decode_token
from packages.common.models.user import User, UserStatus
from packages.common.models.workspace import Workspace, WorkspaceMember, WorkspaceRole

security_bearer = HTTPBearer(auto_error=False)

class WorkspaceContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    workspace_id: str
    workspace_name: str
    user_id: str
    user_email: str
    role: WorkspaceRole

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_bearer),
    db: AsyncSession = Depends(get_db)
) -> User:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(credentials.credentials)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type (must be access token)",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token subject missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is suspended or inactive",
        )

    return user

async def get_current_workspace_context(
    user: User = Depends(get_current_user),
    x_workspace_id: str | None = Header(None, alias="X-Workspace-Id"),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
) -> WorkspaceContext:
    """
    CRITICAL ARCHITECTURAL RULE:
    Tenant identity must strictly be validated against active authenticated membership.
    Never trust unverified workspace_id.
    """
    # 1. Determine target workspace_id
    target_workspace_id = x_workspace_id

    # If not provided in header, try from JWT payload
    if not target_workspace_id and request:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                payload = decode_token(token)
                target_workspace_id = payload.get("workspace_id")
            except Exception:
                pass

    # Query memberships for the user
    query = (
        select(WorkspaceMember, Workspace)
        .join(Workspace, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user.id)
    )

    if target_workspace_id:
        query = query.where(WorkspaceMember.workspace_id == target_workspace_id)

    result = await db.execute(query)
    match = result.first()

    if not match:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User has no membership or access rights to the requested workspace",
        )

    membership, workspace = match

    return WorkspaceContext(
        workspace_id=workspace.id,
        workspace_name=workspace.name,
        user_id=user.id,
        user_email=user.email,
        role=membership.role,
    )

def require_role(allowed_roles: Sequence[WorkspaceRole | str]):
    """
    RBAC dependency factory enforcing minimum role requirements within the active workspace.
    """
    allowed_set = {r.value if isinstance(r, WorkspaceRole) else r for r in allowed_roles}

    async def role_checker(
        ctx: WorkspaceContext = Depends(get_current_workspace_context)
    ) -> WorkspaceContext:
        user_role = ctx.role.value if isinstance(ctx.role, WorkspaceRole) else ctx.role
        if user_role not in allowed_set:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires one of roles: {list(allowed_set)}. Current role: {user_role}",
            )
        return ctx

    return role_checker
