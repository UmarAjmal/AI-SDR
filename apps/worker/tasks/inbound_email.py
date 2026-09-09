import asyncio
import logging
import hashlib
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from apps.worker.celery_app import celery_app
from apps.api.core.database import AsyncSessionLocal
from packages.common.models.email import (
    EmailThread,
    EmailMessage,
    SuppressionList,
    SuppressionReason,
    MessageDirection,
    DeliveryStatus,
    ThreadStatus,
    EmailAccount
)
from packages.common.models.crm import CRMLead
from packages.common.models.campaign import CampaignLead, LeadSequenceState, ConversationEvent
from packages.email.parser import EmailParser
from packages.compliance.opt_out_detector import OptOutDetector
from packages.campaign.state_machine import CampaignStateMachine
from packages.ai.intent_classifier import IntentClassifier
from packages.ai.reply_agent import GroundedReplyAgent
from packages.ai.taxonomy import IntentType
from packages.email.send_service import EmailSendService

logger = logging.getLogger("codenter.worker.inbound")

@celery_app.task(bind=True, name="apps.worker.tasks.inbound_email.process_inbound_email_task")
def process_inbound_email_task(self, workspace_id: str, raw_payload: dict, provider: str = "GOOGLE"):
    """
    Celery background worker task for processing ingested inbound emails:
    1. Extracts and cleans prospect message with EmailParser quote-history stripping.
    2. Matches CRMLead and EmailThread; deduplicates messages.
    3. Runs deterministic pre-LLM opt-out regex (100% recall) -> instant suppression and sequence halt.
    4. Classifies reply across 14-intent taxonomy.
    5. Invokes GroundedReplyAgent for verified auto-reply or routes to Human Review Inbox.
    """
    async def _async_process():
        async with AsyncSessionLocal() as session:
            # 1. Parse payload fields
            sender_raw = raw_payload.get("from_address", "")
            to_raw = raw_payload.get("to_address", "")
            subject = raw_payload.get("subject", "No Subject")
            raw_body = raw_payload.get("body_text", "")
            body_html = raw_payload.get("body_html")
            provider_msg_id = raw_payload.get("provider_message_id") or raw_payload.get("id")
            in_reply_to = raw_payload.get("in_reply_to")
            references = raw_payload.get("references", [])

            # Extract clean sender email
            parsed_mime = EmailParser.parse_raw_mime(
                f"From: {sender_raw}\nTo: {to_raw}\nSubject: {subject}\n\n{raw_body}"
            )
            sender_email = (parsed_mime.from_address or sender_raw).strip().lower()
            clean_body_text = EmailParser.strip_quote_history(raw_body)

            if not sender_email or "@" not in sender_email:
                logger.warning(f"Inbound email discarded: invalid sender '{sender_email}'")
                return {"status": "discarded", "reason": "invalid_sender"}

            # 2. Message Deduplication Check
            if provider_msg_id:
                dup_res = await session.execute(
                    select(EmailMessage).where(
                        EmailMessage.workspace_id == workspace_id,
                        EmailMessage.provider_message_id == provider_msg_id
                    )
                )
                if dup_res.scalar_one_or_none():
                    logger.info(f"Duplicate inbound message {provider_msg_id} skipped.")
                    return {"status": "skipped", "reason": "duplicate_message_id"}

            # 3. Match or Create CRMLead
            l_res = await session.execute(
                select(CRMLead).where(
                    CRMLead.workspace_id == workspace_id,
                    CRMLead.email == sender_email
                )
            )
            lead = l_res.scalar_one_or_none()
            if not lead:
                lead = CRMLead(
                    workspace_id=workspace_id,
                    email=sender_email,
                    first_name=sender_email.split("@")[0].capitalize(),
                    company_name=sender_email.split("@")[-1].split(".")[0].capitalize()
                )
                session.add(lead)
                await session.flush()

            # 4. Match or Create EmailThread
            th_stmt = (
                select(EmailThread)
                .where(
                    EmailThread.workspace_id == workspace_id,
                    EmailThread.lead_id == lead.id
                )
                .order_by(EmailThread.last_message_at.desc())
            )
            th_res = await session.execute(th_stmt)
            thread = th_res.scalars().first()

            now_utc = datetime.now(timezone.utc)
            if not thread:
                thread = EmailThread(
                    workspace_id=workspace_id,
                    lead_id=lead.id,
                    subject=subject,
                    status=ThreadStatus.REPLIED,
                    last_message_at=now_utc
                )
                session.add(thread)
                await session.flush()
            else:
                thread.status = ThreadStatus.REPLIED
                thread.last_message_at = now_utc

            # 5. Persist EmailMessage
            msg_record = EmailMessage(
                workspace_id=workspace_id,
                thread_id=thread.id,
                provider_message_id=provider_msg_id,
                direction=MessageDirection.INBOUND,
                from_address=sender_email,
                to_address=to_raw,
                subject=subject,
                body_text=clean_body_text,
                body_html=body_html,
                headers_json={"in_reply_to": in_reply_to, "references": references},
                delivery_status=DeliveryStatus.DELIVERED
            )
            session.add(msg_record)
            await session.flush()

            # 6. Check Active Campaign Enrollments
            cl_stmt = select(CampaignLead).where(
                CampaignLead.workspace_id == workspace_id,
                CampaignLead.lead_id == lead.id
            )
            cl_res = await session.execute(cl_stmt)
            campaign_leads = cl_res.scalars().all()

            # 7. CRITICAL: Deterministic Pre-LLM Opt-Out Interceptor
            if OptOutDetector.is_opt_out(clean_body_text):
                matched_phrase = OptOutDetector.extract_matched_phrase(clean_body_text)
                logger.critical(
                    f"Deterministic opt-out intercepted for {sender_email} ('{matched_phrase}'). "
                    f"Executing immediate suppression."
                )

                # Add to SuppressionList
                existing_supp = await session.execute(
                    select(SuppressionList).where(
                        SuppressionList.workspace_id == workspace_id,
                        SuppressionList.email == sender_email
                    )
                )
                if not existing_supp.scalar_one_or_none():
                    supp_entry = SuppressionList(
                        workspace_id=workspace_id,
                        email=sender_email,
                        reason=SuppressionReason.UNSUBSCRIBE,
                        source="INBOUND_REGEX_INTERCEPTOR"
                    )
                    session.add(supp_entry)

                # Update Lead Model
                lead.opt_out = True
                lead.do_not_contact = True

                # Halt all active campaign sequences immediately
                for cl in campaign_leads:
                    if cl.state not in {
                        LeadSequenceState.UNSUBSCRIBED,
                        LeadSequenceState.COMPLETED
                    }:
                        await CampaignStateMachine.transition_lead_state(
                            campaign_lead_id=cl.id,
                            new_state=LeadSequenceState.UNSUBSCRIBED,
                            reason=f"Prospect replied '{matched_phrase}'. Deterministic unsubscribe halt.",
                            db=session,
                            rule_matched="STOP_CONDITION_UNSUBSCRIBE"
                        )

                await session.commit()
                return {
                    "status": "suppressed",
                    "reason": "unsubscribe_detected",
                    "matched_phrase": matched_phrase
                }

            # 8. 14-Intent Taxonomy Classification
            classification = await IntentClassifier.classify_reply(
                text=clean_body_text,
                subject=subject,
                workspace_id=workspace_id
            )

            # Record Classification ConversationEvent
            event = ConversationEvent(
                workspace_id=workspace_id,
                lead_id=lead.id,
                campaign_id=thread.campaign_id,
                event_type="INBOUND_INTENT_CLASSIFICATION",
                rule_matched=f"TAXONOMY_INTENT_{classification.intent}",
                model_version="intent-classifier-v1.0",
                prompt_version="v1.0",
                knowledge_chunk_ids=[],
                previous_state=thread.status.value,
                new_state=classification.intent,
                payload={
                    "intent": classification.intent,
                    "confidence": classification.confidence,
                    "reasoning": classification.reasoning,
                    "requires_human_review": classification.requires_human_review
                }
            )
            session.add(event)

            # 9. State Transitions based on Intent
            if classification.intent == IntentType.AUTO_REPLY.value:
                logger.info(f"Auto-reply (OOO) from {sender_email}; sequence timing maintained.")
                await session.commit()
                return {"status": "auto_reply_ignored", "intent": "AUTO_REPLY"}

            if classification.intent == IntentType.NOT_INTERESTED.value:
                for cl in campaign_leads:
                    if cl.state in {LeadSequenceState.QUEUED, LeadSequenceState.WAITING, LeadSequenceState.SENT}:
                        await CampaignStateMachine.transition_lead_state(
                            campaign_lead_id=cl.id,
                            new_state=LeadSequenceState.COMPLETED,
                            reason="Prospect expressed lack of interest; sequence ended gracefully",
                            db=session,
                            rule_matched="STOP_CONDITION_NOT_INTERESTED"
                        )
                await session.commit()
                return {"status": "not_interested_halted", "intent": "NOT_INTERESTED"}

            # Mark Campaign Leads as REPLIED
            for cl in campaign_leads:
                if cl.state in {LeadSequenceState.QUEUED, LeadSequenceState.WAITING, LeadSequenceState.SENT}:
                    await CampaignStateMachine.transition_lead_state(
                        campaign_lead_id=cl.id,
                        new_state=LeadSequenceState.REPLIED,
                        reason=f"Inbound reply classified as {classification.intent}",
                        db=session,
                        rule_matched="INBOUND_REPLY_RECEIVED"
                    )

            # 10. Grounded Reply Agent Execution
            reply_draft = await GroundedReplyAgent.generate_grounded_reply(
                workspace_id=workspace_id,
                lead=lead,
                thread=thread,
                inbound_message=msg_record,
                classification=classification,
                db=session
            )

            # Auto-Send or Route to Human Review
            if reply_draft.requires_human_review:
                thread.status = ThreadStatus.OPEN
                logger.info(f"Draft for {sender_email} placed in Human Review Inbox ({reply_draft.reasoning})")
            else:
                # Find active mailbox to auto-send reply
                acc_stmt = select(EmailAccount).where(
                    EmailAccount.workspace_id == workspace_id,
                    EmailAccount.health_status == "HEALTHY",
                    EmailAccount.current_day_sends < EmailAccount.daily_send_limit
                )
                acc_res = await session.execute(acc_stmt)
                mailbox = acc_res.scalars().first()

                if mailbox:
                    try:
                        await EmailSendService.dispatch_email(
                            workspace_id=workspace_id,
                            account_id=mailbox.id,
                            to_email=sender_email,
                            subject=reply_draft.subject,
                            body_text=reply_draft.body,
                            lead_id=lead.id,
                            thread_id=thread.id,
                            in_reply_to=provider_msg_id,
                            references=references + ([provider_msg_id] if provider_msg_id else []),
                            db=session
                        )
                    except Exception as e:
                        logger.error(f"Failed to auto-send reply to {sender_email}: {e}")
                        thread.status = ThreadStatus.OPEN

            # 11. AI Lead Qualification Engine (NFAT Framework) & CRM Sync-back
            try:
                from packages.ai.agents.qualification_agent import QualificationAgent
                from packages.common.models.knowledge import BusinessProfile

                bp_stmt = select(BusinessProfile).where(
                    BusinessProfile.workspace_id == workspace_id,
                    BusinessProfile.is_active == True
                )
                bp_res = await session.execute(bp_stmt)
                active_profile = bp_res.scalars().first()

                qual_result = await QualificationAgent.evaluate_lead_qualification(
                    thread=thread,
                    lead=lead,
                    profile=active_profile,
                    db=session
                )

                lead.qualification_status = qual_result.qualification_status
                lead.qualification_details = qual_result.model_dump()
                lead.is_qualified = (qual_result.qualification_status == "QUALIFIED")

                if lead.is_qualified:
                    from apps.worker.tasks.crm_sync import sync_lead_outcome_to_crm_task
                    sync_lead_outcome_to_crm_task.delay(
                        workspace_id=workspace_id,
                        lead_id=lead.id
                    )
                    logger.info(f"Lead {lead.email} marked QUALIFIED; CRM sync task dispatched.")

            except Exception as q_err:
                logger.warning(f"Qualification evaluation failed for {lead.email}: {q_err}")

            await session.commit()
            return {
                "status": "processed",
                "intent": classification.intent,
                "confidence": classification.confidence,
                "requires_human_review": reply_draft.requires_human_review,
                "qualification_status": lead.qualification_status,
                "is_qualified": lead.is_qualified
            }

    try:
        loop = asyncio.get_running_loop()
        return loop.create_task(_async_process())
    except RuntimeError:
        return asyncio.run(_async_process())
