import pytest
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from packages.common.models.campaign import (
    Campaign,
    CampaignLead,
    CampaignState,
    LeadSequenceState,
    ConversationEvent
)
from packages.common.models.crm import CRMLead
from packages.campaign.state_machine import (
    CampaignStateMachine,
    InvalidStateTransitionError,
    TERMINAL_STATES
)

@pytest.mark.asyncio
async def test_valid_lead_sequence_state_transitions(db_session: AsyncSession):
    workspace_id = "ws-sm-test-1"

    # Create Lead and Campaign
    lead = CRMLead(workspace_id=workspace_id, email="lead1@test.com")
    camp = Campaign(workspace_id=workspace_id, name="Q4 Outbound", status=CampaignState.RUNNING)
    db_session.add_all([lead, camp])
    await db_session.commit()

    campaign_lead = CampaignLead(
        workspace_id=workspace_id,
        campaign_id=camp.id,
        lead_id=lead.id,
        state=LeadSequenceState.QUEUED,
        next_action_at=datetime.now(timezone.utc)
    )
    db_session.add(campaign_lead)
    await db_session.commit()

    # QUEUED -> READY
    cl = await CampaignStateMachine.transition_lead_state(
        campaign_lead_id=campaign_lead.id,
        new_state=LeadSequenceState.READY,
        reason="Scheduled send triggered",
        db=db_session
    )
    assert cl.state == LeadSequenceState.READY

    # READY -> SENT
    cl = await CampaignStateMachine.transition_lead_state(
        campaign_lead_id=campaign_lead.id,
        new_state=LeadSequenceState.SENT,
        reason="Dispatched outbound email step 1",
        db=db_session
    )
    assert cl.state == LeadSequenceState.SENT

    # SENT -> WAITING
    cl = await CampaignStateMachine.transition_lead_state(
        campaign_lead_id=campaign_lead.id,
        new_state=LeadSequenceState.WAITING,
        reason="Waiting for delay before step 2",
        db=db_session
    )
    assert cl.state == LeadSequenceState.WAITING

    # WAITING -> COMPLETED (terminal)
    cl = await CampaignStateMachine.transition_lead_state(
        campaign_lead_id=campaign_lead.id,
        new_state=LeadSequenceState.COMPLETED,
        reason="All sequence steps executed",
        db=db_session
    )
    assert cl.state == LeadSequenceState.COMPLETED
    assert cl.next_action_at is None  # Terminal states clear next_action_at

    # Check that ConversationEvents were created
    events_res = await db_session.execute(
        select(ConversationEvent).where(ConversationEvent.campaign_id == camp.id)
    )
    events = events_res.scalars().all()
    assert len(events) == 4
    assert events[-1].new_state == "COMPLETED"

@pytest.mark.asyncio
async def test_invalid_state_transition_raises_error(db_session: AsyncSession):
    workspace_id = "ws-sm-test-2"

    lead = CRMLead(workspace_id=workspace_id, email="lead2@test.com")
    camp = Campaign(workspace_id=workspace_id, name="Enterprise Sequence", status=CampaignState.RUNNING)
    db_session.add_all([lead, camp])
    await db_session.commit()

    campaign_lead = CampaignLead(
        workspace_id=workspace_id,
        campaign_id=camp.id,
        lead_id=lead.id,
        state=LeadSequenceState.UNSUBSCRIBED,
        next_action_at=None
    )
    db_session.add(campaign_lead)
    await db_session.commit()

    # Terminal states (like UNSUBSCRIBED) cannot transition out to READY or SENT
    with pytest.raises(InvalidStateTransitionError):
        await CampaignStateMachine.transition_lead_state(
            campaign_lead_id=campaign_lead.id,
            new_state=LeadSequenceState.READY,
            reason="Illegal reactivation",
            db=db_session
        )

@pytest.mark.asyncio
async def test_all_stop_conditions_lead_to_terminal_state(db_session: AsyncSession):
    workspace_id = "ws-sm-test-3"

    stop_states = [
        (LeadSequenceState.UNSUBSCRIBED, "Prospect replied 'Unsubscribe'"),
        (LeadSequenceState.BOUNCED, "Mailbox returned 550 User Unknown"),
        (LeadSequenceState.MEETING_BOOKED, "Prospect booked a slot on Calendly"),
        (LeadSequenceState.QUALIFIED, "Sales accepted opportunity"),
        (LeadSequenceState.DISQUALIFIED, "Competitor or student"),
        (LeadSequenceState.HANDOFF, "Prospect requested human sales rep"),
    ]

    for target_state, reason in stop_states:
        lead = CRMLead(workspace_id=workspace_id, email=f"lead_{target_state.value}@test.com")
        camp = Campaign(workspace_id=workspace_id, name="Test Stop Sequence", status=CampaignState.RUNNING)
        db_session.add_all([lead, camp])
        await db_session.commit()

        campaign_lead = CampaignLead(
            workspace_id=workspace_id,
            campaign_id=camp.id,
            lead_id=lead.id,
            state=LeadSequenceState.WAITING,
            next_action_at=datetime.now(timezone.utc)
        )
        db_session.add(campaign_lead)
        await db_session.commit()

        cl = await CampaignStateMachine.transition_lead_state(
            campaign_lead_id=campaign_lead.id,
            new_state=target_state,
            reason=reason,
            db=db_session
        )

        assert cl.state == target_state
        assert cl.next_action_at is None
        assert target_state in TERMINAL_STATES
