import logging
from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from packages.common.models.campaign import (
    CampaignLead,
    Campaign,
    CampaignState,
    LeadSequenceState,
    ConversationEvent
)

logger = logging.getLogger("codenter.campaign.state_machine")

class InvalidStateTransitionError(Exception):
    pass

TERMINAL_STATES = {
    LeadSequenceState.UNSUBSCRIBED,
    LeadSequenceState.BOUNCED,
    LeadSequenceState.MEETING_BOOKED,
    LeadSequenceState.QUALIFIED,
    LeadSequenceState.DISQUALIFIED,
    LeadSequenceState.HANDOFF,
    LeadSequenceState.COMPLETED,
}

VALID_TRANSITIONS: dict[LeadSequenceState, set[LeadSequenceState]] = {
    LeadSequenceState.QUEUED: {
        LeadSequenceState.WAITING,
        LeadSequenceState.READY,
        LeadSequenceState.PAUSED,
        LeadSequenceState.DISQUALIFIED,
        LeadSequenceState.UNSUBSCRIBED,
    },
    LeadSequenceState.WAITING: {
        LeadSequenceState.READY,
        LeadSequenceState.PAUSED,
        LeadSequenceState.REPLIED,
        LeadSequenceState.UNSUBSCRIBED,
        LeadSequenceState.BOUNCED,
        LeadSequenceState.MEETING_BOOKED,
        LeadSequenceState.QUALIFIED,
        LeadSequenceState.DISQUALIFIED,
        LeadSequenceState.HANDOFF,
        LeadSequenceState.COMPLETED,
    },
    LeadSequenceState.READY: {
        LeadSequenceState.SENT,
        LeadSequenceState.PAUSED,
        LeadSequenceState.DISQUALIFIED,
        LeadSequenceState.UNSUBSCRIBED,
        LeadSequenceState.BOUNCED,
    },
    LeadSequenceState.SENT: {
        LeadSequenceState.WAITING,
        LeadSequenceState.REPLIED,
        LeadSequenceState.UNSUBSCRIBED,
        LeadSequenceState.BOUNCED,
        LeadSequenceState.MEETING_BOOKED,
        LeadSequenceState.QUALIFIED,
        LeadSequenceState.DISQUALIFIED,
        LeadSequenceState.HANDOFF,
        LeadSequenceState.COMPLETED,
        LeadSequenceState.PAUSED,
    },
    LeadSequenceState.REPLIED: {
        LeadSequenceState.MEETING_BOOKED,
        LeadSequenceState.QUALIFIED,
        LeadSequenceState.DISQUALIFIED,
        LeadSequenceState.HANDOFF,
        LeadSequenceState.UNSUBSCRIBED,
        LeadSequenceState.COMPLETED,
    },
    LeadSequenceState.PAUSED: {
        LeadSequenceState.QUEUED,
        LeadSequenceState.WAITING,
        LeadSequenceState.READY,
        LeadSequenceState.UNSUBSCRIBED,
        LeadSequenceState.DISQUALIFIED,
    },
    # Terminal states have no valid outward transitions
    LeadSequenceState.UNSUBSCRIBED: set(),
    LeadSequenceState.BOUNCED: set(),
    LeadSequenceState.MEETING_BOOKED: set(),
    LeadSequenceState.QUALIFIED: set(),
    LeadSequenceState.DISQUALIFIED: set(),
    LeadSequenceState.HANDOFF: set(),
    LeadSequenceState.COMPLETED: set(),
}

class CampaignStateMachine:
    @classmethod
    def can_transition(cls, current: LeadSequenceState, new_state: LeadSequenceState) -> bool:
        allowed = VALID_TRANSITIONS.get(current, set())
        return new_state in allowed

    @classmethod
    async def transition_lead_state(
        cls,
        campaign_lead_id: str,
        new_state: LeadSequenceState,
        reason: str,
        db: AsyncSession,
        rule_matched: Optional[str] = None,
        model_version: Optional[str] = None,
        prompt_version: Optional[str] = None,
        knowledge_chunk_ids: Optional[list[str]] = None,
        payload: Optional[dict[str, Any]] = None
    ) -> CampaignLead:
        """
        Executes a deterministic state transition on CampaignLead and records
        an immutable ConversationEvent audit log.
        """
        res = await db.execute(
            select(CampaignLead).where(CampaignLead.id == campaign_lead_id)
        )
        lead_enrollment = res.scalar_one_or_none()
        if not lead_enrollment:
            raise ValueError(f"CampaignLead enrollment {campaign_lead_id} not found")

        current_state = lead_enrollment.state

        if current_state == new_state:
            return lead_enrollment

        if not cls.can_transition(current_state, new_state):
            err_msg = (
                f"Invalid state transition from {current_state.value} to {new_state.value} "
                f"for lead enrollment {campaign_lead_id}. Allowed: {[s.value for s in VALID_TRANSITIONS.get(current_state, set())]}"
            )
            logger.error(err_msg)
            raise InvalidStateTransitionError(err_msg)

        # Apply transition
        lead_enrollment.state = new_state
        lead_enrollment.updated_at = datetime.now(timezone.utc)

        # If terminal state, clear next_action_at to halt all scheduling permanently
        if new_state in TERMINAL_STATES:
            lead_enrollment.next_action_at = None
            logger.info(f"Lead enrollment {campaign_lead_id} reached terminal state {new_state.value}; next_action_at cleared.")

        # Create Immutable 5-Question Audit Trail Record
        audit_event = ConversationEvent(
            workspace_id=lead_enrollment.workspace_id,
            lead_id=lead_enrollment.lead_id,
            campaign_id=lead_enrollment.campaign_id,
            event_type="STATE_TRANSITION",
            rule_matched=rule_matched or f"STATE_MACHINE_RULE_{new_state.value}",
            model_version=model_version,
            prompt_version=prompt_version,
            knowledge_chunk_ids=knowledge_chunk_ids or [],
            previous_state=current_state.value,
            new_state=new_state.value,
            payload={"reason": reason, **(payload or {})}
        )
        db.add(audit_event)

        await db.commit()
        await db.refresh(lead_enrollment)
        return lead_enrollment
