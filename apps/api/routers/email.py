from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from apps.api.core.database import get_db
from apps.api.core.dependencies import get_current_workspace_context, require_role, WorkspaceContext
from packages.common.models.workspace import WorkspaceRole
from packages.common.models.email import (
    EmailAccount,
    EmailThread,
    EmailMessage,
    SuppressionList,
    EmailProviderType,
    MailboxHealthStatus,
    ThreadStatus
)
from packages.common.schemas.email import (
    EmailAccountResponse,
    EmailAccountCreateRequest,
    EmailAccountUpdateRequest,
    EmailThreadResponse,
    EmailMessageResponse,
    EmailSendRequest,
    SuppressionResponse,
    SuppressionCreateRequest
)
from packages.common.encryption import TokenEncryptor
from packages.email.send_service import EmailSendService, EmailDeliveryError

router = APIRouter(prefix="/email", tags=["Email & Deliverability"])

# ----------------- Mailbox Accounts -----------------

@router.get("/accounts", response_model=list[EmailAccountResponse])
async def list_email_accounts(
    ctx: WorkspaceContext = Depends(get_current_workspace_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Lists all connected mailboxes with health and daily quotas for the authenticated workspace.
    """
    res = await db.execute(
        select(EmailAccount).where(EmailAccount.workspace_id == ctx.workspace_id)
    )
    return res.scalars().all()

@router.post("/accounts", response_model=EmailAccountResponse, status_code=status.HTTP_201_CREATED)
async def connect_email_account(
    payload: EmailAccountCreateRequest,
    ctx: WorkspaceContext = Depends(require_role([WorkspaceRole.OWNER, WorkspaceRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """
    Connects a new outbound mailbox (Google Workspace or Microsoft 365) and encrypts credentials.
    """
    # Check if mailbox already registered in workspace
    existing = await db.execute(
        select(EmailAccount).where(
            EmailAccount.workspace_id == ctx.workspace_id,
            EmailAccount.email_address == payload.email_address
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Mailbox {payload.email_address} is already connected")

    encryptor = TokenEncryptor()
    enc_cred = encryptor.encrypt(payload.credentials_token)

    account = EmailAccount(
        workspace_id=ctx.workspace_id,
        provider=payload.provider,
        email_address=payload.email_address,
        encrypted_credentials=enc_cred,
        health_status=MailboxHealthStatus.HEALTHY,
        daily_send_limit=payload.daily_send_limit,
        current_day_sends=0
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account

@router.patch("/accounts/{account_id}", response_model=EmailAccountResponse)
async def update_email_account(
    account_id: str,
    payload: EmailAccountUpdateRequest,
    ctx: WorkspaceContext = Depends(require_role([WorkspaceRole.OWNER, WorkspaceRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """
    Updates mailbox configuration (daily cap, pause/resume health).
    """
    res = await db.execute(
        select(EmailAccount).where(
            EmailAccount.id == account_id,
            EmailAccount.workspace_id == ctx.workspace_id
        )
    )
    account = res.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Email account not found")

    if payload.daily_send_limit is not None:
        account.daily_send_limit = payload.daily_send_limit
    if payload.health_status is not None:
        account.health_status = payload.health_status

    await db.commit()
    await db.refresh(account)
    return account

@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_email_account(
    account_id: str,
    ctx: WorkspaceContext = Depends(require_role([WorkspaceRole.OWNER, WorkspaceRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """
    Disconnects and deletes an email account.
    """
    res = await db.execute(
        select(EmailAccount).where(
            EmailAccount.id == account_id,
            EmailAccount.workspace_id == ctx.workspace_id
        )
    )
    account = res.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Email account not found")

    await db.delete(account)
    await db.commit()
    return None

# ----------------- Threads & Messages (Inbox) -----------------

@router.get("/threads", response_model=list[EmailThreadResponse])
async def list_email_threads(
    lead_id: Optional[str] = None,
    campaign_id: Optional[str] = None,
    thread_status: Optional[ThreadStatus] = None,
    ctx: WorkspaceContext = Depends(get_current_workspace_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Lists conversation email threads for the workspace with optional filtering.
    """
    query = select(EmailThread).where(EmailThread.workspace_id == ctx.workspace_id)
    if lead_id:
        query = query.where(EmailThread.lead_id == lead_id)
    if campaign_id:
        query = query.where(EmailThread.campaign_id == campaign_id)
    if thread_status:
        query = query.where(EmailThread.status == thread_status)

    query = query.order_by(EmailThread.last_message_at.desc())
    res = await db.execute(query)
    return res.scalars().all()

@router.get("/threads/{thread_id}", response_model=EmailThreadResponse)
async def get_email_thread_detail(
    thread_id: str,
    ctx: WorkspaceContext = Depends(get_current_workspace_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves full thread conversation timeline with all inbound and outbound messages.
    """
    res = await db.execute(
        select(EmailThread)
        .options(selectinload(EmailThread.messages))
        .where(
            EmailThread.id == thread_id,
            EmailThread.workspace_id == ctx.workspace_id
        )
    )
    thread = res.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=404, detail="Email thread not found")
    return thread

# ----------------- Direct Outbound Send -----------------

@router.post("/send", response_model=EmailMessageResponse, status_code=status.HTTP_201_CREATED)
async def send_direct_email(
    payload: EmailSendRequest,
    ctx: WorkspaceContext = Depends(require_role([WorkspaceRole.OWNER, WorkspaceRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """
    Dispatches an outbound email through EmailSendService enforcing daily limits,
    distributed locks, and suppression lists.
    """
    try:
        msg = await EmailSendService.dispatch_email(
            workspace_id=ctx.workspace_id,
            account_id=payload.account_id,
            to_email=payload.to_email,
            subject=payload.subject,
            body_text=payload.body_text,
            body_html=payload.body_html,
            lead_id=payload.lead_id,
            campaign_id=payload.campaign_id,
            thread_id=payload.thread_id,
            db=db
        )
        return msg
    except EmailDeliveryError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected send failure: {str(e)}")

# ----------------- Suppression List -----------------

@router.get("/suppression", response_model=list[SuppressionResponse])
async def list_suppression_list(
    ctx: WorkspaceContext = Depends(get_current_workspace_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Lists all suppressed email addresses and domains for the workspace.
    """
    res = await db.execute(
        select(SuppressionList)
        .where(SuppressionList.workspace_id == ctx.workspace_id)
        .order_by(SuppressionList.created_at.desc())
    )
    return res.scalars().all()

@router.post("/suppression", response_model=SuppressionResponse, status_code=status.HTTP_201_CREATED)
async def add_to_suppression_list(
    payload: SuppressionCreateRequest,
    ctx: WorkspaceContext = Depends(require_role([WorkspaceRole.OWNER, WorkspaceRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """
    Adds an email address or wildcard domain to the suppression list.
    """
    if not payload.email and not payload.domain:
        raise HTTPException(status_code=400, detail="Either 'email' or 'domain' must be provided")

    # Clean domain/email
    email_clean = payload.email.lower().strip() if payload.email else None
    domain_clean = payload.domain.lower().strip() if payload.domain else None

    item = SuppressionList(
        workspace_id=ctx.workspace_id,
        email=email_clean,
        domain=domain_clean,
        reason=payload.reason,
        source=payload.source or "USER_MANUAL"
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item

@router.delete("/suppression/{suppression_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_suppression_entry(
    suppression_id: str,
    ctx: WorkspaceContext = Depends(require_role([WorkspaceRole.OWNER, WorkspaceRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """
    Removes an address or domain from the suppression list.
    """
    res = await db.execute(
        select(SuppressionList).where(
            SuppressionList.id == suppression_id,
            SuppressionList.workspace_id == ctx.workspace_id
        )
    )
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Suppression entry not found")

    await db.delete(item)
    await db.commit()
    return None
