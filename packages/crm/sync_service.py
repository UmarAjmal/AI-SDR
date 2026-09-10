import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from packages.common.models.crm import CRMConnection, CRMLead, CRMSyncStatus, CRMProviderType
from packages.common.models.knowledge import BusinessProfile
from packages.common.encryption import TokenEncryptor
from packages.crm.base import CRMProvider
from packages.crm.adapters.hubspot_adapter import HubSpotProvider
from packages.crm.adapters.salesforce_adapter import SalesforceProvider
from packages.crm.adapters.pipedrive_adapter import PipedriveProvider
from packages.crm.adapters.zoho_adapter import ZohoProvider
from packages.lead_intelligence.scorer import LeadScorer

logger = logging.getLogger("codenter.crm.sync")

class CRMSyncService:
    @classmethod
    def get_provider(cls, conn: CRMConnection) -> CRMProvider:
        field_maps = conn.field_mappings_json or {}
        if conn.provider == CRMProviderType.HUBSPOT:
            return HubSpotProvider()
        elif conn.provider == CRMProviderType.SALESFORCE:
            instance_url = field_maps.get("instance_url")
            return SalesforceProvider(instance_url=instance_url)
        elif conn.provider == CRMProviderType.PIPEDRIVE:
            return PipedriveProvider()
        elif conn.provider == CRMProviderType.ZOHO:
            api_domain = field_maps.get("api_domain")
            return ZohoProvider(api_domain=api_domain)
        raise ValueError(f"Provider {conn.provider} adapter not implemented")

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
        Tracks per-record sync errors for full user visibility.
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
            refresh_token = encryptor.decrypt(conn.encrypted_refresh_token) if conn.encrypted_refresh_token else ""
        except Exception as e:
            logger.error(f"Failed to decrypt credentials for CRM connection {conn.id}: {e}")
            conn.sync_status = CRMSyncStatus.ERROR
            conn.sync_error_message = f"Decryption error: {str(e)}"
            await db.commit()
            return conn

        # Instantiate provider if not passed
        if provider is None:
            try:
                provider = cls.get_provider(conn)
            except Exception as e:
                conn.sync_status = CRMSyncStatus.ERROR
                conn.sync_error_message = str(e)
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
        sync_errors: list[dict] = list(conn.sync_errors_json or [])

        try:
            while total_imported < max_contacts:
                batch_limit = min(100, max_contacts - total_imported)
                batch = await provider.fetch_contacts(access_token=access_token, cursor=cursor, limit=batch_limit)

                for contact in batch.contacts:
                    try:
                        norm_email = contact.email.strip().lower() if contact.email else ""
                        if not norm_email or "@" not in norm_email:
                            sync_errors.append({
                                "record_id": contact.crm_record_id,
                                "email": getattr(contact, "email", "N/A"),
                                "error": "Invalid or missing email format; contact skipped",
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            })
                            continue

                        # Score contact deterministically
                        score_res = LeadScorer.evaluate_lead_score(contact, profile)

                        # Respect CRM ownership, lifecycle stage & stop rules
                        # Stop condition 6: CRM indicates active sales deal / opportunity
                        is_active_deal = False
                        lifecycle = (contact.lifecycle_stage or "").lower()
                        if lifecycle in ("customer", "opportunity", "closed_won", "evangelist"):
                            is_active_deal = True

                        suppression_reason = None
                        lead_state = "DISCOVERED"
                        if contact.opt_out:
                            suppression_reason = "CRM_OPTOUT"
                            lead_state = "SUPPRESSED"
                        elif contact.do_not_contact:
                            suppression_reason = "CRM_DO_NOT_CONTACT"
                            lead_state = "SUPPRESSED"
                        elif is_active_deal:
                            suppression_reason = "CRM_ACTIVE_DEAL"
                            lead_state = "DISQUALIFIED"

                        provider_str = conn.provider.value if hasattr(conn.provider, "value") else str(conn.provider)
                        source_str = (contact.custom_fields or {}).get("source") or "CRM_IMPORT"

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
                            existing_lead.provider = provider_str
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
                            existing_lead.custom_fields = {**(existing_lead.custom_fields or {}), **(contact.custom_fields or {})}

                            # Suppression propagation
                            if contact.opt_out:
                                existing_lead.opt_out = True
                                existing_lead.suppression_reason = "CRM_OPTOUT"
                                existing_lead.state = "SUPPRESSED"
                            if contact.do_not_contact:
                                existing_lead.do_not_contact = True
                                existing_lead.suppression_reason = "CRM_DO_NOT_CONTACT"
                                existing_lead.state = "SUPPRESSED"
                            if is_active_deal:
                                existing_lead.suppression_reason = "CRM_ACTIVE_DEAL"
                                existing_lead.is_qualified = False
                                existing_lead.qualification_status = "CRM_ACTIVE_DEAL"

                            # Update scores
                            existing_lead.icp_score = score_res.icp_score
                            existing_lead.intent_score = score_res.intent_score
                            existing_lead.total_score = score_res.total_score
                            existing_lead.score_band = score_res.score_band
                            existing_lead.score_reasons_json = score_res.to_dict()["reasons"]

                        else:
                            new_lead = CRMLead(
                                workspace_id=workspace_id,
                                crm_connection_id=conn.id,
                                crm_record_id=contact.crm_record_id,
                                provider=provider_str,
                                source=source_str,
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
                                custom_fields=contact.custom_fields or {},
                                opt_out=contact.opt_out,
                                do_not_contact=contact.do_not_contact,
                                suppression_reason=suppression_reason,
                                state=lead_state,
                                bounce_status="NONE",
                                icp_score=score_res.icp_score,
                                intent_score=score_res.intent_score,
                                total_score=score_res.total_score,
                                score_band=score_res.score_band,
                                score_reasons_json=score_res.to_dict()["reasons"]
                            )
                            if is_active_deal:
                                new_lead.is_qualified = False
                                new_lead.qualification_status = "CRM_ACTIVE_DEAL"
                            db.add(new_lead)

                        total_imported += 1

                    except Exception as rec_err:
                        logger.warning(f"Error processing CRM contact {getattr(contact, 'crm_record_id', 'unknown')}: {rec_err}")
                        sync_errors.append({
                            "record_id": getattr(contact, "crm_record_id", None),
                            "email": getattr(contact, "email", None),
                            "error": str(rec_err),
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })

                await db.flush()

                if not batch.has_more or not batch.next_cursor:
                    cursor = None
                    break
                cursor = batch.next_cursor

            conn.sync_cursor = cursor
            conn.last_sync_at = datetime.now(timezone.utc)
            conn.sync_status = CRMSyncStatus.CONNECTED
            conn.sync_errors_json = sync_errors[-100:]  # Retain last 100 per-record errors
            await db.commit()
            await db.refresh(conn)
            logger.info(f"CRM sync finished successfully for connection {conn.id}. Total contacts processed: {total_imported}, errors: {len(sync_errors)}")
            return conn

        except Exception as e:
            logger.error(f"Error during CRM sync for connection {conn.id}: {e}")
            conn.sync_status = CRMSyncStatus.ERROR
            conn.sync_error_message = str(e)
            conn.sync_errors_json = sync_errors[-100:]
            await db.commit()
            await db.refresh(conn)
            return conn

    @classmethod
    async def sync_lead_back_to_crm(
        cls,
        workspace_id: str,
        lead_id: str,
        db: AsyncSession,
        provider: Optional[CRMProvider] = None
    ) -> bool:
        """
        Pushes canonical lead status updates (meeting booked, qualification, suppression/opt-out)
        back into connected CRM provider for bidirectional updates.
        """
        res = await db.execute(
            select(CRMLead).where(
                CRMLead.id == lead_id,
                CRMLead.workspace_id == workspace_id
            )
        )
        lead = res.scalar_one_or_none()
        if not lead or not lead.crm_record_id:
            logger.info(f"Lead {lead_id} does not have a CRM record ID for sync-back")
            return False

        # Find associated connection
        conn_res = await db.execute(
            select(CRMConnection).where(
                CRMConnection.id == lead.crm_connection_id,
                CRMConnection.workspace_id == workspace_id
            )
        )
        conn = conn_res.scalar_one_or_none()
        if not conn:
            # Fallback to any connected CRM in workspace
            fb_res = await db.execute(
                select(CRMConnection).where(
                    CRMConnection.workspace_id == workspace_id,
                    CRMConnection.sync_status == CRMSyncStatus.CONNECTED
                )
            )
            conn = fb_res.scalars().first()

        if not conn or conn.sync_status == CRMSyncStatus.REVOKED:
            logger.warning(f"No active CRM connection found for workspace {workspace_id}")
            return False

        encryptor = TokenEncryptor()
        try:
            token = encryptor.decrypt(conn.encrypted_access_token)
        except Exception as e:
            logger.error(f"Failed to decrypt token for CRM sync-back: {e}")
            return False

        if provider is None:
            try:
                provider = cls.get_provider(conn)
            except Exception as e:
                logger.error(f"Cannot resolve provider for CRM connection {conn.id}: {e}")
                return False

        payload: dict[str, Any] = {}
        if conn.provider == CRMProviderType.HUBSPOT:
            if lead.opt_out or lead.do_not_contact:
                payload["hs_email_optout"] = "true"
            if lead.meeting_booked:
                payload["hs_lead_status"] = "CONNECTED"
                payload["lifecyclestage"] = "salesqualifiedlead"
            elif lead.is_qualified:
                payload["hs_lead_status"] = "QUALIFIED"
                payload["lifecyclestage"] = "marketingqualifiedlead"
            elif lead.disqualified:
                payload["hs_lead_status"] = "UNQUALIFIED"
            if lead.lead_notes:
                payload["notes_last_contacted"] = datetime.now(timezone.utc).isoformat()
        elif conn.provider == CRMProviderType.SALESFORCE:
            if lead.opt_out or lead.do_not_contact:
                payload["HasOptedOutOfEmail"] = True
                payload["DoNotCall"] = True
            if lead.meeting_booked:
                payload["Status"] = "Closed - Converted"
            elif lead.is_qualified:
                payload["Status"] = "Working - Contacted"
            elif lead.disqualified:
                payload["Status"] = "Closed - Not Converted"
            if lead.lead_notes:
                payload["Description"] = lead.lead_notes
        elif conn.provider == CRMProviderType.PIPEDRIVE:
            if lead.opt_out or lead.do_not_contact:
                payload["marketing_status"] = "opted_out"
        elif conn.provider == CRMProviderType.ZOHO:
            if lead.opt_out or lead.do_not_contact:
                payload["Email_Opt_Out"] = True
            if lead.meeting_booked:
                payload["Lead_Status"] = "Contacted"
            elif lead.is_qualified:
                payload["Lead_Status"] = "Pre-Qualified"
            elif lead.disqualified:
                payload["Lead_Status"] = "Lost Lead"
            if lead.lead_notes:
                payload["Description"] = lead.lead_notes

        try:
            success = await provider.update_contact(
                access_token=token,
                contact_id=lead.crm_record_id,
                fields=payload
            )
            return bool(success)
        except Exception as e:
            logger.error(f"Failed to sync lead {lead_id} back to CRM: {e}")
            return False

    @classmethod
    async def handle_webhook_event(
        cls,
        workspace_id: str,
        connection_id: str,
        event_type: str,
        object_id: str,
        properties: dict[str, Any],
        db: AsyncSession,
        provider: Optional[CRMProvider] = None
    ) -> Optional[CRMLead]:
        """
        Handles incremental CRM updates received via webhook events.
        Enforces deduplication and deterministic lead scoring.
        """
        res = await db.execute(
            select(CRMConnection).where(
                CRMConnection.id == connection_id,
                CRMConnection.workspace_id == workspace_id
            )
        )
        conn = res.scalar_one_or_none()
        if not conn:
            return None

        # Find existing lead by crm_record_id
        lead_res = await db.execute(
            select(CRMLead).where(
                CRMLead.workspace_id == workspace_id,
                CRMLead.crm_record_id == object_id
            )
        )
        lead = lead_res.scalar_one_or_none()

        if lead:
            # Apply incremental property updates
            if "hs_email_optout" in properties:
                opt_out = str(properties["hs_email_optout"]).lower() == "true"
                lead.opt_out = opt_out
                if opt_out:
                    lead.do_not_contact = True
                    lead.suppression_reason = "CRM_OPTOUT"
                    lead.state = "SUPPRESSED"
            if "lifecyclestage" in properties:
                stage = str(properties["lifecyclestage"]).lower()
                lead.lifecycle_stage = stage
                if stage in ("customer", "opportunity", "closed_won"):
                    lead.suppression_reason = "CRM_ACTIVE_DEAL"
                    lead.is_qualified = False
                    lead.qualification_status = "CRM_ACTIVE_DEAL"

            await db.commit()
            await db.refresh(lead)
            return lead

        return None
