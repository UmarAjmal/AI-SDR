from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.api.core.database import get_db
from apps.api.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from apps.api.core.dependencies import get_current_user
from packages.common.models.user import User, UserStatus
from packages.common.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from packages.common.models.audit import AuditLog
from packages.common.schemas.auth import UserRegisterRequest, UserLoginRequest, TokenResponse, UserResponse
from packages.common.encryption import encryptor
from packages.common.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserRegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    # Check if user already exists
    existing = await db.execute(select(User).where(User.email == payload.email.lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists"
        )

    # 1. Create User
    new_user = User(
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        status=UserStatus.ACTIVE
    )
    db.add(new_user)
    await db.flush()

    # 2. Create Default Workspace (derived automatically if not provided)
    ws_name = payload.workspace_name
    if not ws_name or not ws_name.strip():
        if payload.company_name and payload.company_name.strip():
            ws_name = payload.company_name.strip()
        elif payload.first_name and payload.first_name.strip():
            ws_name = f"{payload.first_name.strip()}'s Workspace"
        else:
            domain_part = payload.email.split("@")[0].replace(".", " ").title()
            ws_name = f"{domain_part}'s Workspace"

    new_workspace = Workspace(
        name=ws_name,
        domain=payload.email.split("@")[-1] if "@" in payload.email else None,
        settings={"theme": "cobalt", "onboarding_completed": False}
    )
    db.add(new_workspace)
    await db.flush()

    # 3. Add Member as OWNER
    member = WorkspaceMember(
        workspace_id=new_workspace.id,
        user_id=new_user.id,
        role=WorkspaceRole.OWNER
    )
    db.add(member)

    # 4. Audit Log
    audit = AuditLog(
        workspace_id=new_workspace.id,
        actor_id=new_user.id,
        actor_email=new_user.email,
        action="USER_REGISTERED",
        resource_type="workspace",
        resource_id=new_workspace.id,
        payload={"workspace_name": new_workspace.name}
    )
    db.add(audit)
    await db.commit()

    # 5. Generate Tokens
    token_data = {
        "sub": new_user.id,
        "email": new_user.email,
        "workspace_id": new_workspace.id,
        "role": WorkspaceRole.OWNER.value
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token({"sub": new_user.id})

    # Set encrypted refresh token in HttpOnly cookie
    encrypted_refresh = encryptor.encrypt(refresh_token)
    response.set_cookie(
        key="sdr_refresh_token",
        value=encrypted_refresh,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=7 * 24 * 3600
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=new_user.id,
        active_workspace_id=new_workspace.id,
        active_role=WorkspaceRole.OWNER.value
    )

@router.post("/login", response_model=TokenResponse)
async def login(
    payload: UserLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == payload.email.lower()))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email address or password"
        )

    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is suspended"
        )

    # Find primary workspace
    member_result = await db.execute(
        select(WorkspaceMember, Workspace)
        .join(Workspace, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user.id)
        .order_by(WorkspaceMember.created_at.asc())
    )
    first_membership = member_result.first()

    if not first_membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User has no workspace assigned"
        )

    membership, workspace = first_membership

    token_data = {
        "sub": user.id,
        "email": user.email,
        "workspace_id": workspace.id,
        "role": membership.role.value
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token({"sub": user.id})

    # Set encrypted refresh token in HttpOnly cookie
    encrypted_refresh = encryptor.encrypt(refresh_token)
    response.set_cookie(
        key="sdr_refresh_token",
        value=encrypted_refresh,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=7 * 24 * 3600
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user.id,
        active_workspace_id=workspace.id,
        active_role=membership.role.value
    )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    response: Response,
    sdr_refresh_token: str | None = Cookie(None),
    db: AsyncSession = Depends(get_db)
):
    if not sdr_refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token cookie missing"
        )

    try:
        raw_refresh_token = encryptor.decrypt(sdr_refresh_token)
        payload = decode_token(raw_refresh_token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or corrupted refresh token: {str(e)}"
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Provided token is not a refresh token"
        )

    user_id = payload.get("sub")
    user_res = await db.execute(select(User).where(User.id == user_id))
    user = user_res.scalar_one_or_none()

    if not user or user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with token no longer active"
        )

    member_res = await db.execute(
        select(WorkspaceMember)
        .where(WorkspaceMember.user_id == user.id)
        .order_by(WorkspaceMember.created_at.asc())
    )
    membership = member_res.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=403, detail="No active workspace membership")

    new_token_data = {
        "sub": user.id,
        "email": user.email,
        "workspace_id": membership.workspace_id,
        "role": membership.role.value
    }
    new_access_token = create_access_token(new_token_data)

    return TokenResponse(
        access_token=new_access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user.id,
        active_workspace_id=membership.workspace_id,
        active_role=membership.role.value
    )

@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return user

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="sdr_refresh_token")
    return {"status": "success", "message": "Logged out successfully"}
