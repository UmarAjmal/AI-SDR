import asyncio
import logging
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.worker.celery_app import celery_app
from apps.api.core.database import AsyncSessionLocal
from packages.common.models.crm import CRMLead, CRMConnection, CRMSyncStatus, CRMProviderType
from packages.common.models.audit import AuditLog
from packages.common.models.campaign import ConversationEvent
from packages.common.encryption import TokenEncryptor
from packages.crm.adapters.hubspot_adapter import HubSpotProvider

logger = logging.getLogger("codenter.worker.crm_sync")

@celery_app.task(bind=True, name="apps.worker.tasks.crm_sync.sync_lead_outcome_to_crm_task", max_retries=3)
def sync_lead_outcome_to_crm_task(self, workspace_id: str, lead_id: str):
    """
    Bi-directional CRM Sync-back Celery Task:
    1. Loads lead and verifies qualification outcome.
    2. Loads active CRM connection & decrypts credentials.
    3. Formats vendor-specific contact update payload.
    4. Dispatches update to CRM vendor (HubSpot/Salesforce) with retry & exponential backoff on 5xx.
    5. Records immutable audit log. Local qualification data is never dropped.
    """
    async def _async_sync():
        async with AsyncSessionLocal() as session:
            # 1. Fetch CRMLead
            l_stmt = select(CRMLead).where(
                CRMLead.id == lead_id,
                CRMLead.workspace_id == workspace_id
            )
            l_res = await session.execute(l_stmt)
            lead = l_res.scalar_one_or_none()
            if not lead:
                logger.warning(f"Lead {lead_id} not found in workspace {workspace_id}")
                return {"status": "error", "reason": "lead_not_found"}

            # 2. Find active CRM Connection
            conn = None
            if lead.crm_connection_id:
                c_stmt = select(CRMConnection).where(
                    CRMConnection.id == lead.crm_connection_id,
                    CRMConnection.workspace_id == workspace_id
                )
                c_res = await session.execute(c_stmt)
                conn = c_res.scalar_one_or_none()

            if not conn:
                fallback_stmt = select(CRMConnection).where(
                    CRMConnection.workspace_id == workspace_id,
                    CRMConnection.sync_status == CRMSyncStatus.CONNECTED
                )
                fb_res = await session.execute(fallback_stmt)
                conn = fb_res.scalars().first()

            if not conn or not lead.crm_record_id:
                logger.info(
                    f"Skipping CRM sync for lead {lead.email}: "
                    f"{'No connected CRM' if not conn else 'No crm_record_id'}"
                )
                return {
                    "status": "skipped",
                    "reason": "no_crm_connection" if not conn else "no_crm_record_id"
                }

            # 3. Decrypt token & prepare payload
            encryptor = TokenEncryptor()
            token = encryptor.decrypt(conn.encrypted_access_token)

            details = lead.qualification_details or {}
            reasons_str = ", ".join(details.get("reason_codes", []))
            summary_str = (
                f"NFAT Status: {lead.qualification_status} | "
                f"Authority: {details.get('authority', 'UNKNOWN')} | "
                f"Timing: {details.get('timing', 'UNKNOWN')} | "
                f"Need: {details.get('need', 'N/A')} | "
                f"Reasons: {reasons_str}"
            )

            payload = {
                "lifecyclestage": "marketingqualifiedlead" if lead.is_qualified else (lead.lifecycle_stage or "lead"),
                "hs_lead_status": "QUALIFIED" if lead.is_qualified else "IN_PROGRESS",
                "ai_sdr_qualification_status": lead.qualification_status,
                "ai_sdr_fit_score": str(details.get("fit_score", int(lead.icp_score))),
                "ai_sdr_qualification_summary": summary_str
            }

            # 4. Invoke Provider
            provider = HubSpotProvider()
            try:
                success = await provider.update_contact(
                    access_token=token,
                    contact_id=lead.crm_record_id,
                    fields=payload
                )
            except Exception as e:
                logger.error(f"CRM sync error for lead {lead.email} on HubSpot: {e}")
                # Retry with exponential backoff; do not lose local qualification
                raise self.retry(exc=e, countdown=2 ** self.request.retries)

            if not success:
                logger.warning(f"CRM update returned non-success for lead {lead.email}")
                raise self.retry(
                    exc=Exception("HubSpot update returned False"),
                    countdown=2 ** self.request.retries
                )

            audit = AuditLog(
                workspace_id=workspace_id,
                action="CRM_OUTCOME_SYNC",
                resource_type="CRMLead",
                resource_id=lead.id,
                payload={
                    "provider": conn.provider.value,
                    "crm_record_id": lead.crm_record_id,
                    "qualification_status": lead.qualification_status,
                    "synced_fields": list(payload.keys())
                }
            )
            session.add(audit)

            event = ConversationEvent(
                workspace_id=workspace_id,
                lead_id=lead.id,
                event_type="CRM_OUTCOME_SYNC",
                rule_matched="BI_DIRECTIONAL_CRM_SYNC_BACK",
                model_version="nfat-sync-v1.0",
                prompt_version="v1.0",
                knowledge_chunk_ids=[],
                previous_state="LOCAL_QUALIFIED",
                new_state="CRM_SYNCED",
                payload=payload
            )
            session.add(event)
            await session.commit()

            logger.info(f"Successfully synced lead {lead.email} qualification back to {conn.provider.value}")
            return {
                "status": "success",
                "lead_id": lead.id,
                "crm_record_id": lead.crm_record_id,
                "qualification_status": lead.qualification_status
            }

    try:
        loop = asyncio.get_running_loop()
        return loop.create_task(_async_sync())
    except RuntimeError:
        return asyncio.run(_async_sync())
