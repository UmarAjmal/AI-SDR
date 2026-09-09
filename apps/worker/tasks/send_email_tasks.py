import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from apps.worker.celery_app import celery_app
from apps.worker.middleware import retry_with_jitter
from apps.api.core.database import AsyncSessionLocal
from packages.common.models.campaign import (
    Campaign,
    CampaignStep,
    CampaignLead,
    CampaignState,
    LeadSequenceState
)
from packages.common.models.crm import CRMLead
from packages.common.models.email import (
    EmailAccount,
    MailboxHealthStatus
)
from packages.campaign.state_machine import CampaignStateMachine
from packages.campaign.scheduler import CampaignScheduler
from packages.email.send_service import EmailSendService, EmailDeliveryError
from packages.email.suppression import SuppressionChecker

logger = logging.getLogger("codenter.worker.send_email")

@celery_app.task(bind=True, name="apps.worker.tasks.send_email_tasks.send_campaign_email_task")
@retry_with_jitter(max_retries=2, base_delay=5.0)
def send_campaign_email_task(self, workspace_id: str, campaign_lead_id: str):
    """
    Celery background worker task for dispatching an email in a campaign sequence step.
    Verifies campaign and lead state, checks stop conditions, generates personalized content,
    dispatches via EmailSendService with distributed locking, advances sequence step,
    and calculates next_action_at using prospect timezone.
    """
    async def _async_send():
        async with AsyncSessionLocal() as session:
            # 1. Fetch CampaignLead with Campaign and CRMLead
            stmt = (
                select(CampaignLead)
                .options(
                    selectinload(CampaignLead.campaign).selectinload(Campaign.steps),
                    selectinload(CampaignLead.lead)
                )
                .where(
                    CampaignLead.id == campaign_lead_id,
                    CampaignLead.workspace_id == workspace_id
                )
            )
            res = await session.execute(stmt)
            campaign_lead = res.scalar_one_or_none()

            if not campaign_lead:
                logger.warning(f"Campaign lead enrollment {campaign_lead_id} not found in workspace {workspace_id}")
                return {"status": "skipped", "reason": "lead_not_found"}

            campaign = campaign_lead.campaign
            lead = campaign_lead.lead

            # 2. Check Campaign status
            if campaign.status != CampaignState.RUNNING:
                logger.info(f"Campaign {campaign.id} is {campaign.status.value}, skipping email send for lead {lead.id}")
                return {"status": "skipped", "reason": f"campaign_status_{campaign.status.value}"}

            # 3. Check Lead Stop Conditions
            if campaign_lead.state in {
                LeadSequenceState.UNSUBSCRIBED,
                LeadSequenceState.BOUNCED,
                LeadSequenceState.MEETING_BOOKED,
                LeadSequenceState.QUALIFIED,
                LeadSequenceState.DISQUALIFIED,
                LeadSequenceState.HANDOFF,
                LeadSequenceState.COMPLETED
            }:
                logger.info(f"Lead enrollment {campaign_lead.id} is in terminal state {campaign_lead.state.value}, aborting send")
                return {"status": "skipped", "reason": f"terminal_state_{campaign_lead.state.value}"}

            # Check lead opt-out or suppression list
            if lead.is_opted_out or await SuppressionChecker.is_email_suppressed(workspace_id, lead.email, session):
                await CampaignStateMachine.transition_lead_state(
                    campaign_lead_id=campaign_lead.id,
                    new_state=LeadSequenceState.UNSUBSCRIBED,
                    reason="Suppression or opt-out detected prior to send",
                    db=session,
                    rule_matched="STOP_CONDITION_UNSUBSCRIBE"
                )
                return {"status": "halted", "reason": "suppressed_or_opted_out"}

            # 4. Resolve Current Step
            steps_dict = {s.step_number: s for s in campaign.steps}
            current_step = steps_dict.get(campaign_lead.current_step_number)
            if not current_step:
                # No step found, sequence completed
                await CampaignStateMachine.transition_lead_state(
                    campaign_lead_id=campaign_lead.id,
                    new_state=LeadSequenceState.COMPLETED,
                    reason=f"No step found for step number {campaign_lead.current_step_number}",
                    db=session,
                    rule_matched="STOP_CONDITION_MAX_STEPS"
                )
                return {"status": "completed", "reason": "all_steps_finished"}

            # 5. Pick active EmailAccount for workspace
            acc_stmt = select(EmailAccount).where(
                EmailAccount.workspace_id == workspace_id,
                EmailAccount.health_status.in_([MailboxHealthStatus.HEALTHY, MailboxHealthStatus.WARMING]),
                EmailAccount.current_day_sends < EmailAccount.daily_send_limit
            ).order_by(EmailAccount.current_day_sends.asc())
            acc_res = await session.execute(acc_stmt)
            email_account = acc_res.scalars().first()

            if not email_account:
                logger.warning(f"No active email accounts with quota available in workspace {workspace_id}")
                return {"status": "deferred", "reason": "no_available_mailbox"}

            # 6. Render Subject and Body via AI Grounded Personalization or Template
            tpl = current_step.template_config_json or {}
            first_name = lead.first_name or "there"
            last_name = lead.last_name or ""
            lead_company = lead.company_name or "your team"

            if current_step.prompt_instructions:
                from packages.ai.generation_service import AIPersonalizationService
                from packages.ai.schemas import RecommendedAction

                ai_draft, telemetry, _ = await AIPersonalizationService.generate_outbound_draft(
                    workspace_id=workspace_id,
                    lead_id=lead.id,
                    campaign_step_id=current_step.id,
                    db=session
                )

                # Hallucination & Confidence Gate: Halt send if human review is required
                if ai_draft.recommended_action == RecommendedAction.HUMAN_REVIEW or ai_draft.confidence < 0.85:
                    logger.warning(
                        f"AI Draft for lead {lead.id} flagged for HUMAN_REVIEW ({ai_draft.risk_flags}). Halting auto-send."
                    )
                    await CampaignStateMachine.transition_lead_state(
                        campaign_lead_id=campaign_lead.id,
                        new_state=LeadSequenceState.HANDOFF,
                        reason=f"AI Draft held for Human Review: {', '.join(ai_draft.risk_flags) if ai_draft.risk_flags else 'Confidence < 0.85'}",
                        db=session,
                        rule_matched="HALLUCINATION_GATE_HUMAN_REVIEW"
                    )
                    return {"status": "held_for_human_review", "risk_flags": ai_draft.risk_flags}

                subject = ai_draft.subject
                body_text = ai_draft.body
                body_html = None
            else:
                subject_template = tpl.get("subject", "Introduction from {{company_name}}")
                body_template = tpl.get("body_text", "Hi {{first_name}},\n\nI noticed your work at {{company}}.")
                html_template = tpl.get("body_html")

                subject = subject_template.replace("{{first_name}}", first_name).replace("{{company}}", lead_company).replace("{{company_name}}", lead_company)
                body_text = body_template.replace("{{first_name}}", first_name).replace("{{last_name}}", last_name).replace("{{company}}", lead_company).replace("{{title}}", lead.title or "")
                body_html = html_template.replace("{{first_name}}", first_name).replace("{{company}}", lead_company) if html_template else None

            # 7. Transition to READY before dispatch
            if campaign_lead.state != LeadSequenceState.READY:
                await CampaignStateMachine.transition_lead_state(
                    campaign_lead_id=campaign_lead.id,
                    new_state=LeadSequenceState.READY,
                    reason=f"Preparing dispatch for step {campaign_lead.current_step_number}",
                    db=session
                )

            # 8. Dispatch Email via EmailSendService
            try:
                msg_record = await EmailSendService.dispatch_email(
                    workspace_id=workspace_id,
                    account_id=email_account.id,
                    to_email=lead.email,
                    subject=subject,
                    body_text=body_text,
                    body_html=body_html,
                    lead_id=lead.id,
                    campaign_id=campaign.id,
                    db=session
                )
            except EmailDeliveryError as e:
                logger.error(f"Failed to dispatch email for lead {lead.id}: {e}")
                raise

            # 9. Transition to SENT
            await CampaignStateMachine.transition_lead_state(
                campaign_lead_id=campaign_lead.id,
                new_state=LeadSequenceState.SENT,
                reason=f"Dispatched email message {msg_record.id} for step {campaign_lead.current_step_number}",
                db=session,
                payload={"message_id": msg_record.id, "provider_message_id": msg_record.provider_message_id}
            )

            # 10. Advance Step or Complete
            next_step_number = campaign_lead.current_step_number + 1
            next_step = steps_dict.get(next_step_number)

            if next_step:
                campaign_lead.current_step_number = next_step_number
                # Calculate next send time in recipient timezone
                lead_tz = (lead.custom_fields_json or {}).get("timezone", "UTC")
                next_action = CampaignScheduler.calculate_next_send_time(
                    lead_timezone=lead_tz,
                    delay_days=next_step.delay_days,
                    delay_hours=next_step.delay_hours
                )
                campaign_lead.next_action_at = next_action
                await CampaignStateMachine.transition_lead_state(
                    campaign_lead_id=campaign_lead.id,
                    new_state=LeadSequenceState.WAITING,
                    reason=f"Advanced to step {next_step_number}, next send scheduled at {next_action.isoformat()}",
                    db=session
                )
                logger.info(f"Lead enrollment {campaign_lead.id} scheduled for step {next_step_number} at {next_action}")
            else:
                campaign_lead.next_action_at = None
                await CampaignStateMachine.transition_lead_state(
                    campaign_lead_id=campaign_lead.id,
                    new_state=LeadSequenceState.COMPLETED,
                    reason="All sequence steps finished",
                    db=session,
                    rule_matched="STOP_CONDITION_MAX_STEPS"
                )
                logger.info(f"Lead enrollment {campaign_lead.id} completed all sequence steps")

            await session.commit()
            return {"status": "success", "message_id": msg_record.id, "step": current_step.step_number}

    try:
        loop = asyncio.get_running_loop()
        return loop.create_task(_async_send())
    except RuntimeError:
        return asyncio.run(_async_send())
