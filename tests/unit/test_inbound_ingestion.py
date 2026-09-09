import pytest
import asyncio
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from tests.conftest import TestingSessionLocal
from apps.worker.tasks.inbound_email import process_inbound_email_task
from packages.common.models.email import (
    EmailThread,
    EmailMessage,
    SuppressionList,
    SuppressionReason,
    ThreadStatus
)
from packages.common.models.crm import CRMLead
from packages.common.models.campaign import Campaign, CampaignLead, CampaignState, LeadSequenceState

@pytest.mark.asyncio
async def test_inbound_opt_out_triggers_instant_suppression_and_sequence_halt(monkeypatch, db_session: AsyncSession):
    monkeypatch.setattr("apps.worker.tasks.inbound_email.AsyncSessionLocal", TestingSessionLocal)

    workspace_id = "ws-inbound-test-1"
    sender_email = "optout.lead@prospect.com"

    # Setup lead and active campaign
    lead = CRMLead(
        workspace_id=workspace_id,
        email=sender_email,
        first_name="Terry",
        company_name="ProspectCo"
    )
    camp = Campaign(
        workspace_id=workspace_id,
        name="Outbound SDR Wave 1",
        status=CampaignState.RUNNING
    )
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

    # Incoming opt-out email
    payload = {
        "from_address": sender_email,
        "to_address": "sdr@codenter.ai",
        "subject": "Re: Quick question",
        "body_text": "Please remove me immediately and stop emailing me.\n\n> On Monday, sdr@codenter.ai wrote:\n> Hi Terry...",
        "provider_message_id": "msg-optout-999"
    }

    res = process_inbound_email_task(
        workspace_id=workspace_id,
        raw_payload=payload,
        provider="GOOGLE"
    )
    if asyncio.iscoroutine(res) or isinstance(res, asyncio.Task):
        result = await res
    else:
        result = res

    assert result["status"] == "suppressed"
    assert result["reason"] == "unsubscribe_detected"

    lead_id = lead.id
    camp_lead_id = campaign_lead.id

    # Expire session cache to read newly committed changes
    db_session.expire_all()

    # Verify Lead Model
    lead_res = await db_session.execute(select(CRMLead).where(CRMLead.id == lead_id))
    refreshed_lead = lead_res.scalar_one()
    assert refreshed_lead.opt_out is True
    assert refreshed_lead.do_not_contact is True

    # Verify Global Suppression List Entry
    supp_res = await db_session.execute(
        select(SuppressionList).where(
            SuppressionList.workspace_id == workspace_id,
            SuppressionList.email == sender_email
        )
    )
    supp = supp_res.scalar_one_or_none()
    assert supp is not None
    assert supp.reason == SuppressionReason.UNSUBSCRIBE

    # Verify Campaign Lead Sequence Halted to UNSUBSCRIBED
    cl_res = await db_session.execute(
        select(CampaignLead).where(CampaignLead.id == camp_lead_id)
    )
    refreshed_cl = cl_res.scalar_one()
    assert refreshed_cl.state == LeadSequenceState.UNSUBSCRIBED
    assert refreshed_cl.next_action_at is None

@pytest.mark.asyncio
async def test_inbound_message_deduplication(monkeypatch, db_session: AsyncSession):
    monkeypatch.setattr("apps.worker.tasks.inbound_email.AsyncSessionLocal", TestingSessionLocal)

    workspace_id = "ws-inbound-test-2"
    payload = {
        "from_address": "prospect@corp.com",
        "to_address": "sdr@codenter.ai",
        "subject": "Tell me more",
        "body_text": "Sounds interesting, can you share more details?",
        "provider_message_id": "unique-provider-id-001"
    }

    # First ingestion
    res1 = process_inbound_email_task(workspace_id=workspace_id, raw_payload=payload)
    if asyncio.iscoroutine(res1) or isinstance(res1, asyncio.Task):
        res1 = await res1

    assert res1["status"] in {"processed", "not_interested_halted", "auto_reply_ignored"}

    # Duplicate ingestion with same provider_message_id
    res2 = process_inbound_email_task(workspace_id=workspace_id, raw_payload=payload)
    if asyncio.iscoroutine(res2) or isinstance(res2, asyncio.Task):
        res2 = await res2

    assert res2["status"] == "skipped"
    assert res2["reason"] == "duplicate_message_id"

@pytest.mark.asyncio
async def test_inbound_quote_stripping_and_thread_creation(monkeypatch, db_session: AsyncSession):
    monkeypatch.setattr("apps.worker.tasks.inbound_email.AsyncSessionLocal", TestingSessionLocal)

    workspace_id = "ws-inbound-test-3"
    sender_email = "newlead@startup.io"

    quoted_email_body = (
        "How much does your Growth tier cost?\n\n"
        "On Monday, Oct 12, 2026 at 10:00 AM, Alex <alex@codenter.ai> wrote:\n"
        "> Hi there,\n"
        "> Wanted to introduce Codenter AI SDR..."
    )

    payload = {
        "from_address": sender_email,
        "to_address": "sdr@codenter.ai",
        "subject": "Re: Introduction to Codenter",
        "body_text": quoted_email_body,
        "provider_message_id": "msg-quote-strip-1"
    }

    res = process_inbound_email_task(workspace_id=workspace_id, raw_payload=payload)
    if asyncio.iscoroutine(res) or isinstance(res, asyncio.Task):
        await res

    # Verify Message created and clean body stored
    msg_res = await db_session.execute(
        select(EmailMessage).where(
            EmailMessage.workspace_id == workspace_id,
            EmailMessage.provider_message_id == "msg-quote-strip-1"
        )
    )
    msg = msg_res.scalar_one_or_none()
    assert msg is not None
    assert "Growth tier cost" in msg.body_text
    assert "Wanted to introduce Codenter" not in msg.body_text

    # Verify Thread created
    th_res = await db_session.execute(
        select(EmailThread).where(EmailThread.id == msg.thread_id)
    )
    thread = th_res.scalar_one_or_none()
    assert thread is not None
    assert thread.subject == "Re: Introduction to Codenter"
