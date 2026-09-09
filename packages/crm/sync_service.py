import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from packages.common.models.crm import CRMConnection, CRMLead, CRMSyncStatus, CRMProviderType
from packages.common.models.knowledge import BusinessProfile
from packages.common.encryption import TokenEncryptor
from packages.crm.base import CRMProvider
from packages.crm.adapters.hubspot_adapter import HubSpotProvider
from packages.lead_intelligence.scorer import LeadScorer

logger = logging.getLogger("codenter.crm.sync")

class CRMSyncService:
    @classmethod
    async def sync_connection(
        cls,
        workspace_id: str,
        connection_id: str,
        db: AsyncSession,
        provider: Optional[CRMProvider] = None,
        max_contacts: int = 500
    ) -> CRMConnection:
        """
        Executes bidirectional synchronization and lead normalization for a CRM connection.
        Enforces tenant isolation, token envelope encryption, deduplication, and deterministic scoring.
        """
        res = await db.execute(
            select(CRMConnection).where(
                CRMConnection.id == connection_id,
                CRMConnection.workspace_id == workspace_id
            )
        )
        conn = res.scalar_one_or_none()
        if not conn:
            raise ValueError(f"CRMConnection {connection_id} not found in workspace {workspace_id}")

        conn.sync_status = CRMSyncStatus.SYNCING
        conn.sync_error_message = None
        await db.commit()

        encryptor = TokenEncryptor()

        # Decrypt tokens
        try:
            access_token = encryptor.decrypt(conn.encrypted_access_token)
            refresh_token = encryptor.decrypt(conn.encrypted_refresh_token)
        except Exception as e:
            logger.error(f"Failed to decrypt credentials for CRM connection {conn.id}: {e}")
            conn.sync_status = CRMSyncStatus.ERROR
            conn.sync_error_message = f"Decryption error: {str(e)}"
            await db.commit()
            return conn

        # Instantiate provider if not passed
        if provider is None:
            if conn.provider == CRMProviderType.HUBSPOT:
                provider = HubSpotProvider()
            else:
                conn.sync_status = CRMSyncStatus.ERROR
                conn.sync_error_message = f"Provider {conn.provider} adapter not implemented"
                await db.commit()
                return conn

        # Check token expiration & refresh if needed
        now = datetime.now(timezone.utc)
        if conn.token_expires_at and conn.token_expires_at <= now + timedelta(minutes=5):
            logger.info(f"Refreshing token for CRM connection {conn.id}")
            try:
                new_bundle = await provider.refresh_tokens(refresh_token)
                access_token = new_bundle.access_token
                refresh_token = new_bundle.refresh_token
                conn.encrypted_access_token = encryptor.encrypt(access_token)
                conn.encrypted_refresh_token = encryptor.encrypt(refresh_token)
                conn.token_expires_at = now + timedelta(seconds=new_bundle.expires_in)
                await db.commit()
            except Exception as e:
                logger.error(f"Token refresh failed for CRM connection {conn.id}: {e}")
                conn.sync_status = CRMSyncStatus.REVOKED
                conn.sync_error_message = "OAuth refresh token revoked or expired. Please re-authenticate."
                await db.commit()
                return conn

        # Retrieve active BusinessProfile for grounded lead scoring
        prof_res = await db.execute(
            select(BusinessProfile).where(
                BusinessProfile.workspace_id == workspace_id,
                BusinessProfile.is_active == True
            )
        )
        profile = prof_res.scalar_one_or_none()

        cursor = conn.sync_cursor
        total_imported = 0

        try:
            while total_imported < max_contacts:
                batch_limit = min(100, max_contacts - total_imported)
                batch = await provider.fetch_contacts(access_token=access_token, cursor=cursor, limit=batch_limit)

                for contact in batch.contacts:
                    norm_email = contact.email.strip().lower()
                    if not norm_email:
                        continue

                    # Score contact deterministically
                    score_res = LeadScorer.evaluate_lead_score(contact, profile)

                    # Deduplication check: (workspace_id, email)
                    existing_res = await db.execute(
                        select(CRMLead).where(
                            CRMLead.workspace_id == workspace_id,
                            CRMLead.email == norm_email
                        )
                    )
                    existing_lead = existing_res.scalar_one_or_none()

                    if existing_lead:
                        # Update in place without duplicating
                        existing_lead.crm_connection_id = conn.id
                        existing_lead.crm_record_id = contact.crm_record_id or existing_lead.crm_record_id
                        existing_lead.first_name = contact.first_name or existing_lead.first_name
                        existing_lead.last_name = contact.last_name or existing_lead.last_name
                        existing_lead.phone = contact.phone or existing_lead.phone
                        existing_lead.job_title = contact.job_title or existing_lead.job_title
                        existing_lead.company_name = contact.company_name or existing_lead.company_name
                        existing_lead.domain = contact.domain or existing_lead.domain
                        existing_lead.industry = contact.industry or existing_lead.industry
                        existing_lead.employee_count = contact.employee_count or existing_lead.employee_count
                        existing_lead.location = contact.location or existing_lead.location
                        existing_lead.revenue_band = contact.revenue_band or existing_lead.revenue_band
                        existing_lead.lifecycle_stage = contact.lifecycle_stage or existing_lead.lifecycle_stage
                        existing_lead.owner_id = contact.owner_id or existing_lead.owner_id
                        existing_lead.lead_notes = contact.lead_notes or existing_lead.lead_notes
                        existing_lead.custom_fields = {**existing_lead.custom_fields, **contact.custom_fields}

                        # Suppression propagation
                        if contact.opt_out:
                            existing_lead.opt_out = True
                        if contact.do_not_contact:
                            existing_lead.do_not_contact = True

                        # Update scores
                        existing_lead.icp_score = score_res.icp_score
                        existing_lead.intent_score = score_res.intent_score
                        existing_lead.total_score = score_res.total_score
                        existing_lead.score_reasons_json = score_res.to_dict()["reasons"]

                    else:
                        new_lead = CRMLead(
                            workspace_id=workspace_id,
                            crm_connection_id=conn.id,
                            crm_record_id=contact.crm_record_id,
                            first_name=contact.first_name,
                            last_name=contact.last_name,
                            email=norm_email,
                            phone=contact.phone,
                            job_title=contact.job_title,
                            company_name=contact.company_name,
                            domain=contact.domain,
                            industry=contact.industry,
                            employee_count=contact.employee_count,
                            location=contact.location,
                            revenue_band=contact.revenue_band,
                            lifecycle_stage=contact.lifecycle_stage,
                            owner_id=contact.owner_id,
                            lead_notes=contact.lead_notes,
                            custom_fields=contact.custom_fields,
                            opt_out=contact.opt_out,
                            do_not_contact=contact.do_not_contact,
                            bounce_status="NONE",
                            icp_score=score_res.icp_score,
                            intent_score=score_res.intent_score,
                            total_score=score_res.total_score,
                            score_reasons_json=score_res.to_dict()["reasons"]
                        )
                        db.add(new_lead)

                    total_imported += 1

                await db.flush()

                if not batch.has_more or not batch.next_cursor:
                    cursor = None
                    break
                cursor = batch.next_cursor

            conn.sync_cursor = cursor
            conn.last_sync_at = datetime.now(timezone.utc)
            conn.sync_status = CRMSyncStatus.CONNECTED
            await db.commit()
            await db.refresh(conn)
            logger.info(f"CRM sync finished successfully for connection {conn.id}. Total contacts processed: {total_imported}")
            return conn

        except Exception as e:
            logger.error(f"Error during CRM sync for connection {conn.id}: {e}")
            conn.sync_status = CRMSyncStatus.ERROR
            conn.sync_error_message = str(e)
            await db.commit()
            await db.refresh(conn)
            return conn
