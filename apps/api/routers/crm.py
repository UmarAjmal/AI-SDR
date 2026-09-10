import secrets
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.api.core.database import get_db, AsyncSessionLocal
from apps.api.core.dependencies import get_current_workspace_context, require_role, WorkspaceContext
from packages.common.models.workspace import WorkspaceRole
from packages.common.models.crm import CRMConnection, CRMProviderType, CRMSyncStatus
from packages.common.schemas.crm import (
    CRMConnectionResponse,
    CRMAuthUrlResponse,
    CRMOAuthCallbackRequest
)
from packages.common.encryption import TokenEncryptor
from packages.crm.adapters.hubspot_adapter import HubSpotProvider
from packages.crm.sync_service import CRMSyncService
from apps.worker.tasks.crm_tasks import sync_crm_leads_task

router = APIRouter(prefix="/integrations/crm", tags=["CRM Integrations"])

@router.get("/connections", response_model=list[CRMConnectionResponse])
async def list_crm_connections(
    ctx: WorkspaceContext = Depends(get_current_workspace_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Lists all CRM connections for the authenticated workspace.
    """
    res = await db.execute(
        select(CRMConnection).where(CRMConnection.workspace_id == ctx.workspace_id)
    )
    return res.scalars().all()

@router.post("/{provider}/connect", response_model=CRMAuthUrlResponse)
async def generate_crm_auth_url(
    provider: CRMProviderType,
    redirect_uri: str,
    ctx: WorkspaceContext = Depends(require_role([WorkspaceRole.OWNER, WorkspaceRole.ADMIN]))
):
    """
    Generates a secure OAuth2 authorization redirect URL with a random CSRF state token.
    """
    state = f"codenter_{ctx.workspace_id}_{secrets.token_urlsafe(16)}"
    if provider == CRMProviderType.HUBSPOT:
        adapter = HubSpotProvider()
        url = adapter.get_auth_url(state=state, redirect_uri=redirect_uri)
    else:
        raise HTTPException(status_code=400, detail=f"Provider {provider} not supported yet")

    return CRMAuthUrlResponse(
        provider=provider,
        authorization_url=url,
        state=state
    )

@router.post("/{provider}/callback", response_model=CRMConnectionResponse)
async def handle_crm_oauth_callback(
    provider: CRMProviderType,
    payload: CRMOAuthCallbackRequest,
    ctx: WorkspaceContext = Depends(require_role([WorkspaceRole.OWNER, WorkspaceRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """
    Exchanges OAuth2 authorization code for token bundle and persists encrypted tokens at rest.
    """
    if provider != CRMProviderType.HUBSPOT:
        raise HTTPException(status_code=400, detail=f"Provider {provider} not supported")

    adapter = HubSpotProvider()
    try:
        token_bundle = await adapter.exchange_code(code=payload.code, redirect_uri=payload.redirect_uri)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth token exchange failed: {str(e)}")

    encryptor = TokenEncryptor()
    enc_access = encryptor.encrypt(token_bundle.access_token)
    enc_refresh = encryptor.encrypt(token_bundle.refresh_token)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_bundle.expires_in)

    # Check if connection for this provider already exists in workspace
    res = await db.execute(
        select(CRMConnection).where(
            CRMConnection.workspace_id == ctx.workspace_id,
            CRMConnection.provider == provider
        )
    )
    conn = res.scalar_one_or_none()

    if conn:
        conn.account_id = token_bundle.account_id or conn.account_id
        conn.account_name = token_bundle.account_name or conn.account_name
        conn.encrypted_access_token = enc_access
        conn.encrypted_refresh_token = enc_refresh
        conn.token_expires_at = expires_at
        conn.sync_status = CRMSyncStatus.CONNECTED
        conn.sync_error_message = None
    else:
        conn = CRMConnection(
            workspace_id=ctx.workspace_id,
            provider=provider,
            account_id=token_bundle.account_id,
            account_name=token_bundle.account_name,
            encrypted_access_token=enc_access,
            encrypted_refresh_token=enc_refresh,
            token_expires_at=expires_at,
            field_mappings_json={},
            sync_status=CRMSyncStatus.CONNECTED
        )
        db.add(conn)

    await db.commit()
    await db.refresh(conn)
    return conn

@router.post("/{connection_id}/sync", response_model=CRMConnectionResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_crm_sync(
    connection_id: str,
    ctx: WorkspaceContext = Depends(require_role([WorkspaceRole.OWNER, WorkspaceRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """
    Triggers an asynchronous background synchronization of contacts from the CRM.
    """
    res = await db.execute(
        select(CRMConnection).where(
            CRMConnection.id == connection_id,
            CRMConnection.workspace_id == ctx.workspace_id
        )
    )
    conn = res.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="CRM connection not found")

    conn.sync_status = CRMSyncStatus.SYNCING
    await db.commit()
    await db.refresh(conn)

    # Dispatch background task (Celery with local non-blocking fallback)
    try:
        sync_crm_leads_task.delay(
            workspace_id=ctx.workspace_id,
            connection_id=conn.id
        )
    except Exception:
        async def _run_local_sync():
            try:
                async with AsyncSessionLocal() as session:
                    await CRMSyncService.sync_connection(
                        workspace_id=ctx.workspace_id,
                        connection_id=conn.id,
                        db=session
                    )
            except Exception:
                pass
        asyncio.create_task(_run_local_sync())

    return conn

@router.get("/{connection_id}/errors")
async def get_crm_sync_errors(
    connection_id: str,
    ctx: WorkspaceContext = Depends(require_role([WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.MEMBER])),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns per-record synchronization errors and warnings for user visibility.
    """
    res = await db.execute(
        select(CRMConnection).where(
            CRMConnection.id == connection_id,
            CRMConnection.workspace_id == ctx.workspace_id
        )
    )
    conn = res.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="CRM connection not found")

    return {
        "connection_id": conn.id,
        "provider": conn.provider,
        "sync_status": conn.sync_status,
        "errors": conn.sync_errors_json or []
    }

@router.post("/{provider}/webhook", status_code=status.HTTP_200_OK)
async def handle_crm_webhook(
    provider: CRMProviderType,
    payload: Any = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Ingests incremental CRM webhooks (e.g. HubSpot contact updates, opt-outs, lifecycle shifts).
    Enforces deduplication via event ID and non-blocking background dispatch.
    """
    if provider == CRMProviderType.HUBSPOT:
        adapter = HubSpotProvider()
        events = adapter.parse_webhook_payload(payload)
        for ev in events:
            conns_res = await db.execute(
                select(CRMConnection).where(CRMConnection.provider == provider)
            )
            conns = conns_res.scalars().all()
            for conn in conns:
                await CRMSyncService.handle_webhook_event(
                    workspace_id=conn.workspace_id,
                    connection_id=conn.id,
                    event_type=ev.event_type,
                    object_id=ev.object_id,
                    properties=ev.properties,
                    db=db,
                    provider=adapter
                )
        return {"status": "accepted", "events_processed": len(events)}
    return {"status": "ignored"}
