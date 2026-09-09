import pytest
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from packages.common.models.crm import CRMLead
from packages.common.models.email import EmailThread, EmailMessage, ThreadStatus, MessageDirection, DeliveryStatus
from packages.common.models.knowledge import BusinessProfile
from packages.common.models.campaign import ConversationEvent
from packages.ai.agents.qualification_agent import QualificationAgent, QualificationResult
from packages.ai.gateway import ModelGateway

@pytest.mark.asyncio
async def test_qualification_thread_a_qualified(db_session: AsyncSession):
    workspace_id = "ws-qual-test-1"

    bp = BusinessProfile(
        workspace_id=workspace_id,
        company_name="SDR Automations",
        is_active=True,
        version=1,
        offerings={"ai_sdr": "Autonomous Outbound Pipeline"}
    )
    lead = CRMLead(
        workspace_id=workspace_id,
        email="vp.sales@growthcorp.com",
        first_name="Alexander",
        last_name="Vance",
        job_title="VP of Sales",
        company_name="GrowthCorp",
        industry="Technology",
        total_score=88.0
    )
    db_session.add_all([bp, lead])
    await db_session.flush()

    thread = EmailThread(
        workspace_id=workspace_id,
        lead_id=lead.id,
        subject="Autonomous SDR demo",
        status=ThreadStatus.REPLIED,
        last_message_at=datetime.now(timezone.utc)
    )
    db_session.add(thread)
    await db_session.flush()

    outbound = EmailMessage(
        workspace_id=workspace_id,
        thread_id=thread.id,
        from_address="sdr@codenter.ai",
        to_address=lead.email,
        subject="Autonomous SDR demo",
        direction=MessageDirection.OUTBOUND,
        delivery_status=DeliveryStatus.SENT,
        body_text="Hi Alexander, wanted to see if automating pipeline generation is a priority?"
    )
    inbound = EmailMessage(
        workspace_id=workspace_id,
        thread_id=thread.id,
        from_address=lead.email,
        to_address="sdr@codenter.ai",
        subject="Re: Autonomous SDR demo",
        direction=MessageDirection.INBOUND,
        delivery_status=DeliveryStatus.DELIVERED,
        body_text="We need this urgently for our 50-person sales team. Are you available this Thursday for a live demo?"
    )
    db_session.add_all([outbound, inbound])
    await db_session.flush()

    res = await QualificationAgent.evaluate_lead_qualification(
        lead=lead,
        thread=thread,
        profile=bp,
        db=db_session
    )

    assert isinstance(res, QualificationResult)
    assert res.qualification_status == "QUALIFIED"
    assert res.timing == "NOW"
    assert res.next_action == "BOOK_MEETING"
    assert res.authority in ["DECISION_MAKER", "INFLUENCER"]
    assert len(res.pain_points) > 0

    # Verify ConversationEvent audit trail
    stmt = select(ConversationEvent).where(
        ConversationEvent.workspace_id == workspace_id,
        ConversationEvent.event_type == "AI_LEAD_QUALIFICATION"
    )
    audit_res = await db_session.execute(stmt)
    event = audit_res.scalar_one_or_none()
    assert event is not None
    assert event.rule_matched == "NFAT_QUALIFICATION_FRAMEWORK"
    assert event.payload["qualification_status"] == "QUALIFIED"

@pytest.mark.asyncio
async def test_qualification_thread_b_developing(db_session: AsyncSession):
    workspace_id = "ws-qual-test-2"

    lead = CRMLead(
        workspace_id=workspace_id,
        email="mark@retailgroup.com",
        first_name="Mark",
        job_title="Marketing Specialist",
        company_name="Retail Group",
        total_score=60.0
    )
    db_session.add(lead)
    await db_session.flush()

    thread = EmailThread(
        workspace_id=workspace_id,
        lead_id=lead.id,
        subject="AI prospecting",
        status=ThreadStatus.REPLIED
    )
    db_session.add(thread)
    await db_session.flush()

    inbound = EmailMessage(
        workspace_id=workspace_id,
        thread_id=thread.id,
        from_address=lead.email,
        to_address="sdr@codenter.ai",
        subject="Re: AI prospecting",
        direction=MessageDirection.INBOUND,
        delivery_status=DeliveryStatus.DELIVERED,
        body_text="Sounds cool, maybe next year when our budget unlocks."
    )
    db_session.add(inbound)
    await db_session.flush()

    res = await QualificationAgent.evaluate_lead_qualification(
        lead=lead,
        thread=thread,
        db=db_session
    )

    assert res.qualification_status == "DEVELOPING"
    assert res.timing == "LATER"
    assert res.next_action == "FOLLOW_UP"

@pytest.mark.asyncio
async def test_qualification_thread_c_unqualified_intern(db_session: AsyncSession):
    workspace_id = "ws-qual-test-3"

    lead = CRMLead(
        workspace_id=workspace_id,
        email="intern@techcamp.edu",
        first_name="Sam",
        job_title="Summer Intern",
        company_name="TechCamp",
        total_score=15.0
    )
    db_session.add(lead)
    await db_session.flush()

    thread = EmailThread(
        workspace_id=workspace_id,
        lead_id=lead.id,
        subject="Platform overview",
        status=ThreadStatus.REPLIED
    )
    db_session.add(thread)
    await db_session.flush()

    inbound = EmailMessage(
        workspace_id=workspace_id,
        thread_id=thread.id,
        from_address=lead.email,
        to_address="sdr@codenter.ai",
        subject="Re: Platform overview",
        direction=MessageDirection.INBOUND,
        delivery_status=DeliveryStatus.DELIVERED,
        body_text="I am an intern here, not interested in purchasing any software."
    )
    db_session.add(inbound)
    await db_session.flush()

    res = await QualificationAgent.evaluate_lead_qualification(
        lead=lead,
        thread=thread,
        db=db_session
    )

    assert res.qualification_status == "UNQUALIFIED"
    assert res.authority == "UNKNOWN"
    assert res.next_action == "STOP"

@pytest.mark.asyncio
async def test_overqualification_safeguard_demotes_polite_pleasantry(db_session: AsyncSession):
    workspace_id = "ws-qual-test-4"

    lead = CRMLead(
        workspace_id=workspace_id,
        email="executive@bigco.com",
        first_name="Rachel",
        job_title="Director of Strategy",
        company_name="BigCo",
        total_score=85.0
    )
    db_session.add(lead)
    await db_session.flush()

    thread = EmailThread(
        workspace_id=workspace_id,
        lead_id=lead.id,
        subject="Quick intro",
        status=ThreadStatus.REPLIED
    )
    db_session.add(thread)
    await db_session.flush()

    # Pure polite pleasantry
    inbound = EmailMessage(
        workspace_id=workspace_id,
        thread_id=thread.id,
        from_address=lead.email,
        to_address="sdr@codenter.ai",
        subject="Re: Quick intro",
        direction=MessageDirection.INBOUND,
        delivery_status=DeliveryStatus.DELIVERED,
        body_text="Thanks, have a great day!"
    )
    db_session.add(inbound)
    await db_session.flush()

    res = await QualificationAgent.evaluate_lead_qualification(
        lead=lead,
        thread=thread,
        db=db_session
    )

    # Must NOT be QUALIFIED despite being a Director at BigCo with high score
    assert res.qualification_status != "QUALIFIED"
    assert res.qualification_status == "DEVELOPING"
    assert any("Over-qualification guard" in r for r in res.reason_codes)
