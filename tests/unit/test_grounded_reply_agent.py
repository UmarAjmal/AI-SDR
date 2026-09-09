import pytest
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from packages.common.models.crm import CRMLead
from packages.common.models.email import EmailThread, EmailMessage, ThreadStatus, MessageDirection, DeliveryStatus
from packages.common.models.knowledge import BusinessProfile, KnowledgeDocument, KnowledgeChunk
from packages.common.models.campaign import ConversationEvent
from packages.ai.schemas import IntentClassificationResult
from packages.ai.taxonomy import IntentType
from packages.ai.reply_agent import GroundedReplyAgent

@pytest.mark.asyncio
async def test_grounded_reply_agent_generates_verified_reply_with_citations(db_session: AsyncSession):
    workspace_id = "ws-reply-test-1"

    # Setup BusinessProfile
    bp = BusinessProfile(
        workspace_id=workspace_id,
        company_name="Codenter Inc",
        is_active=True,
        version=1,
        pricing={"growth": "$499/mo"}
    )
    doc = KnowledgeDocument(
        workspace_id=workspace_id,
        url="https://codenter.ai/pricing",
        title="Pricing Guide",
        content_hash="hash-123",
        raw_text="Growth Tier begins at $499/mo with full outbound automation."
    )
    db_session.add_all([bp, doc])
    await db_session.flush()

    chunk = KnowledgeChunk(
        workspace_id=workspace_id,
        document_id=doc.id,
        chunk_index=0,
        content="Growth Tier begins at $499/mo with full outbound automation.",
        token_count=18,
        embedding=[0.1] * 1536
    )
    lead = CRMLead(
        workspace_id=workspace_id,
        email="buyer@enterprise.com",
        first_name="Jordan",
        company_name="Enterprise Corp"
    )
    db_session.add_all([chunk, lead])
    await db_session.flush()

    thread = EmailThread(
        workspace_id=workspace_id,
        lead_id=lead.id,
        subject="Re: Outbound Automation",
        status=ThreadStatus.REPLIED,
        last_message_at=datetime.now(timezone.utc)
    )
    db_session.add(thread)
    await db_session.flush()

    inbound_msg = EmailMessage(
        workspace_id=workspace_id,
        thread_id=thread.id,
        direction=MessageDirection.INBOUND,
        from_address="buyer@enterprise.com",
        to_address="sdr@codenter.ai",
        subject="Re: Outbound Automation",
        body_text="How much does the growth tier cost? Can you share pricing?",
        delivery_status=DeliveryStatus.DELIVERED
    )
    db_session.add(inbound_msg)
    await db_session.commit()

    classification = IntentClassificationResult(
        intent=IntentType.PRICING.value,
        confidence=0.95,
        reasoning="Prospect requested pricing for growth tier",
        suggested_action="Answer with verified pricing",
        requires_human_review=False
    )

    draft = await GroundedReplyAgent.generate_grounded_reply(
        workspace_id=workspace_id,
        lead=lead,
        thread=thread,
        inbound_message=inbound_msg,
        classification=classification,
        db=db_session
    )

    assert draft.confidence >= 0.85
    assert draft.requires_human_review is False
    assert len(draft.citations) > 0
    assert "https://codenter.ai/pricing" in draft.citations
    assert len(draft.body) > 0

    # Verify ConversationEvent audit trail
    events_res = await db_session.execute(
        select(ConversationEvent).where(
            ConversationEvent.workspace_id == workspace_id,
            ConversationEvent.lead_id == lead.id
        )
    )
    events = events_res.scalars().all()
    assert len(events) >= 1
    event = events[-1]
    assert event.event_type == "INBOUND_REPLY_GENERATION"
    assert event.rule_matched == "GROUNDED_INBOUND_REPLY_POLICY"
    assert event.new_state == "PENDING_AUTO_REPLY"
    assert event.knowledge_chunk_ids == [chunk.id]

@pytest.mark.asyncio
async def test_unsafe_intent_routes_to_human_review(db_session: AsyncSession):
    workspace_id = "ws-reply-test-2"

    lead = CRMLead(workspace_id=workspace_id, email="prospect@company.com")
    thread = EmailThread(workspace_id=workspace_id, lead_id="dummy", subject="Re: Outreach")
    inbound_msg = EmailMessage(
        workspace_id=workspace_id,
        thread_id=thread.id,
        direction=MessageDirection.INBOUND,
        from_address="prospect@company.com",
        to_address="sdr@codenter.ai",
        subject="Re: Outreach",
        body_text="We have a massive objection with our budget freeze."
    )

    # Objection intent cannot auto reply and requires human review
    classification = IntentClassificationResult(
        intent=IntentType.OBJECTION.value,
        confidence=0.92,
        reasoning="Prospect raised budget objection",
        suggested_action="Route to human sales rep",
        requires_human_review=True
    )

    draft = await GroundedReplyAgent.generate_grounded_reply(
        workspace_id=workspace_id,
        lead=lead,
        thread=thread,
        inbound_message=inbound_msg,
        classification=classification,
        db=db_session
    )

    assert draft.requires_human_review is True
    assert "human" in draft.body.lower() or "review" in draft.body.lower()
    assert draft.citations == []

@pytest.mark.asyncio
async def test_low_confidence_reply_forces_human_review(db_session: AsyncSession):
    workspace_id = "ws-reply-test-3"

    lead = CRMLead(workspace_id=workspace_id, email="prospect3@company.com")
    thread = EmailThread(workspace_id=workspace_id, lead_id=lead.id, subject="Re: Info")
    inbound_msg = EmailMessage(
        workspace_id=workspace_id,
        thread_id=thread.id,
        direction=MessageDirection.INBOUND,
        from_address="prospect3@company.com",
        to_address="sdr@codenter.ai",
        subject="Re: Info",
        body_text="Need info with simulate_low_confidence flag"
    )

    # Classification with low confidence
    classification = IntentClassificationResult(
        intent=IntentType.PRODUCT_QUESTION.value,
        confidence=0.75,  # Under 0.85 threshold
        reasoning="Ambiguous question",
        suggested_action="Review",
        requires_human_review=True
    )

    draft = await GroundedReplyAgent.generate_grounded_reply(
        workspace_id=workspace_id,
        lead=lead,
        thread=thread,
        inbound_message=inbound_msg,
        classification=classification,
        db=db_session
    )

    assert draft.requires_human_review is True
