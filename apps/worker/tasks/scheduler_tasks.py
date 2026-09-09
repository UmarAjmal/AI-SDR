import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from apps.worker.celery_app import celery_app
from apps.api.core.database import AsyncSessionLocal
from packages.common.models.campaign import (
    Campaign,
    CampaignLead,
    CampaignState,
    LeadSequenceState
)
from packages.campaign.state_machine import CampaignStateMachine

logger = logging.getLogger("codenter.worker.scheduler")

@celery_app.task(bind=True, name="apps.worker.tasks.scheduler_tasks.evaluate_campaign_schedules_task")
def evaluate_campaign_schedules_task(self):
    """
    Periodic Celery Beat task that evaluates active campaigns and claims leads due for outbound dispatch.
    Uses atomic locking (SELECT ... FOR UPDATE SKIP LOCKED) to prevent concurrent workers from double-claiming.
    """
    async def _async_evaluate():
        now_utc = datetime.now(timezone.utc)
        dispatched_count = 0

        async with AsyncSessionLocal() as session:
            # Query leads due for action whose campaign is RUNNING
            # Claim with FOR UPDATE SKIP LOCKED
            stmt = (
                select(CampaignLead)
                .join(Campaign, CampaignLead.campaign_id == Campaign.id)
                .where(
                    Campaign.status == CampaignState.RUNNING,
                    CampaignLead.state.in_([LeadSequenceState.QUEUED, LeadSequenceState.WAITING]),
                    or_(
                        CampaignLead.next_action_at <= now_utc,
                        and_(CampaignLead.state == LeadSequenceState.QUEUED, CampaignLead.next_action_at.is_(None))
                    )
                )
                .with_for_update(skip_locked=True)
                .limit(50)  # batch size
            )

            res = await session.execute(stmt)
            claimed_leads = res.scalars().all()

            if not claimed_leads:
                return {"dispatched": 0, "message": "No leads due for dispatch"}

            logger.info(f"Scheduler claimed {len(claimed_leads)} leads for campaign sequence execution")

            from apps.worker.tasks.send_email_tasks import send_campaign_email_task

            for lead_enrollment in claimed_leads:
                try:
                    # Transition to READY
                    await CampaignStateMachine.transition_lead_state(
                        campaign_lead_id=lead_enrollment.id,
                        new_state=LeadSequenceState.READY,
                        reason="Scheduled release time reached; dispatching email task",
                        db=session
                    )

                    # Trigger worker email send task
                    send_campaign_email_task.delay(
                        workspace_id=lead_enrollment.workspace_id,
                        campaign_lead_id=lead_enrollment.id
                    )
                    dispatched_count += 1
                except Exception as e:
                    logger.error(f"Failed to process scheduled lead {lead_enrollment.id}: {e}")

            await session.commit()
            return {"dispatched": dispatched_count}

    try:
        loop = asyncio.get_running_loop()
        return loop.create_task(_async_evaluate())
    except RuntimeError:
        return asyncio.run(_async_evaluate())
