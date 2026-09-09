import pytest
from decimal import Decimal
from datetime import datetime, timezone
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from packages.common.models.workspace import Workspace
from packages.common.models.campaign import Campaign, CampaignLead, CampaignState, LeadSequenceState
from packages.common.models.crm import CRMLead
from packages.common.models.email import EmailThread, EmailMessage, MessageDirection, DeliveryStatus
from packages.common.models.calendar import Appointment, AppointmentStatus
from packages.common.models.usage import UsageEvent, UsageEventType
from packages.common.models.telemetry import ConversationEvent, ConversationEventType
from packages.common.models.audit import AuditLog
from packages.ai.metering import calculate_cost, record_usage, enforce_spending_limits
from packages.analytics.funnel import get_workspace_funnel, FunnelReport


@pytest.mark.asyncio
async def test_token_cost_calculation_accuracy():
    """
    Validates token cost calculation against model pricing matrix for both split tokens and unit events.
    """
    # Claude 3.5 Sonnet: $3/1M prompt + $15/1M completion
    # 10,000 prompt tokens = $0.03, 5,000 completion tokens = $0.075 -> Total = $0.105
    claude_cost = calculate_cost(
        event_type="MODEL_TOKENS",
        model="claude-3-5-sonnet",
        prompt_tokens=10000,
        completion_tokens=5000
    )
    assert claude_cost == Decimal("0.105000")

    # GPT-4o: $5/1M prompt + $15/1M completion
    # 2,000 prompt tokens = $0.010, 1,000 completion tokens = $0.015 -> Total = $0.025
    gpt4o_cost = calculate_cost(
        event_type="MODEL_TOKENS",
        model="gpt-4o",
        prompt_tokens=2000,
        completion_tokens=1000
    )
    assert gpt4o_cost == Decimal("0.025000")

    # GPT-4o-mini: $0.15/1M prompt + $0.60/1M completion
    # 20,000 prompt tokens = $0.003, 10,000 completion tokens = $0.006 -> Total = $0.009
    gpt4o_mini_cost = calculate_cost(
        event_type="MODEL_TOKENS",
        model="gpt-4o-mini",
        prompt_tokens=20000,
        completion_tokens=10000
    )
    assert gpt4o_mini_cost == Decimal("0.009000")

    # text-embedding-3-small: $0.02 / 1M tokens
    # 50,000 tokens = $0.001
    emb_cost = calculate_cost(
        event_type="MODEL_TOKENS",
        model="text-embedding-3-small",
        units=50000
    )
    assert emb_cost == Decimal("0.001000")

    # Operational non-token events
    # 100 email sends @ $0.001 = $0.10
    email_cost = calculate_cost(event_type="EMAIL_SENT", units=100)
    assert email_cost == Decimal("0.100000")

    # 10 browser renders @ $0.005 = $0.05
    browser_cost = calculate_cost(event_type="BROWSER_RENDER", units=10)
    assert browser_cost == Decimal("0.050000")

    # 5 enrichment calls @ $0.02 = $0.10
    enrich_cost = calculate_cost(event_type="ENRICHMENT_CALL", units=5)
    assert enrich_cost == Decimal("0.100000")


@pytest.mark.asyncio
async def test_conversation_event_5_core_questions(db_session: AsyncSession):
    """
    Validates that ConversationEvent stores and enforces all 5 questions of the SDR audit trail:
    1. What happened? (event_type)
    2. Which rule allowed it? (rule_name / rule_matched)
    3. Which AI model & prompt version was used? (model_version, prompt_version)
    4. What knowledge chunks/data were retrieved? (knowledge_chunk_ids)
    5. What downstream state changed? (previous_state -> new_state)
    """
    ws = Workspace(name="Observability Corp")
    db_session.add(ws)
    await db_session.commit()
    await db_session.refresh(ws)

    # 1. Create event with 5-question audit fields
    event = ConversationEvent(
        workspace_id=ws.id,
        event_type=ConversationEventType.REPLY_GENERATED,
        rule_name="GROUNDED_FAQ_AUTO_REPLY_RULE",
        model_version="claude-3-5-sonnet-20241022",
        prompt_version="reply_v1.4",
        knowledge_chunk_ids=["chunk-faq-pricing", "chunk-soc2-compliance"],
        previous_state="REPLIED",
        new_state="SENT",
        data_payload={"latency_ms": 380, "grounding_confidence": 0.98}
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)

    # Verify all 5 questions
    assert event.event_type == "REPLY_GENERATED"
    assert event.rule_name == "GROUNDED_FAQ_AUTO_REPLY_RULE"
    assert event.rule_matched == "GROUNDED_FAQ_AUTO_REPLY_RULE"  # backward compat alias
    assert event.model_version == "claude-3-5-sonnet-20241022"
    assert event.prompt_version == "reply_v1.4"
    assert len(event.knowledge_chunk_ids) == 2
    assert event.previous_state == "REPLIED"
    assert event.new_state == "SENT"
    assert event.data_payload["latency_ms"] == 380
    assert event.payload["latency_ms"] == 380  # backward compat alias


@pytest.mark.asyncio
async def test_spending_cap_enforcement_and_auto_pause(db_session: AsyncSession):
    """
    Validates that exceeding workspace spending limits triggers automatic campaign pausing
    and records an immutable audit log.
    """
    # Setup workspace with $5.00 spending limit
    ws = Workspace(name="Budget Strict Inc", settings={"spending_limit_usd": 5.0})
    db_session.add(ws)
    await db_session.commit()
    await db_session.refresh(ws)

    # Setup active running campaign
    camp = Campaign(
        workspace_id=ws.id,
        name="Outbound High Velocity",
        status=CampaignState.RUNNING
    )
    db_session.add(camp)
    await db_session.commit()
    await db_session.refresh(camp)

    # Record usage that exceeds $5.00 limit (e.g. 500,000 completion tokens of Claude @ $15/1M = $7.50)
    usage = await record_usage(
        workspace_id=ws.id,
        event_type=UsageEventType.MODEL_TOKENS,
        model="claude-3-5-sonnet",
        prompt_tokens=0,
        completion_tokens=500000,
        db=db_session
    )
    assert usage.cost_estimate_usd == Decimal("7.500000")

    # Verify campaign was automatically transitioned to PAUSED
    await db_session.refresh(camp)
    assert camp.status == CampaignState.PAUSED

    # Verify AuditLog was emitted
    audit_q = select(AuditLog).where(
        AuditLog.workspace_id == ws.id,
        AuditLog.action == "SPENDING_CAP_EXCEEDED_CAMPAIGNS_PAUSED"
    )
    audit_res = await db_session.execute(audit_q)
    audit_entry = audit_res.scalar_one_or_none()
    assert audit_entry is not None
    assert camp.id in audit_entry.payload["paused_campaign_ids"]


@pytest.mark.asyncio
async def test_synthetic_funnel_sequence(db_session: AsyncSession):
    """
    Unit test funnel aggregator with synthetic event sequence:
    100 enrolled -> 95 sent -> 20 replied -> 5 positive -> 2 booked.
    Asserts exact counts and calculated conversion rates:
    delivery rate, reply rate, positive reply rate, booking rate.
    """
    ws = Workspace(name="Funnel Test Workspace")
    db_session.add(ws)
    await db_session.commit()
    await db_session.refresh(ws)

    camp = Campaign(
        workspace_id=ws.id,
        name="Enterprise SaaS Sequence",
        status=CampaignState.RUNNING
    )
    db_session.add(camp)
    await db_session.commit()
    await db_session.refresh(camp)

    # 1. 100 enrolled leads
    leads = []
    for i in range(100):
        lead = CRMLead(
            workspace_id=ws.id,
            first_name=f"Lead{i}",
            last_name="Test",
            email=f"lead{i}@enterprise.com",
            company_name="Enterprise Corp",
            is_qualified=(i < 5),  # 5 qualified leads
            qualification_status="QUALIFIED" if i < 5 else "UNQUALIFIED"
        )
        leads.append(lead)
    db_session.add_all(leads)
    await db_session.commit()

    camp_leads = [
        CampaignLead(
            workspace_id=ws.id,
            campaign_id=camp.id,
            lead_id=lead.id,
            state=LeadSequenceState.SENT if i < 95 else LeadSequenceState.QUEUED
        )
        for i, lead in enumerate(leads)
    ]
    db_session.add_all(camp_leads)
    await db_session.commit()

    # 2. 95 sends recorded via ConversationEvent
    events = []
    for i in range(95):
        events.append(
            ConversationEvent(
                workspace_id=ws.id,
                campaign_id=camp.id,
                lead_id=leads[i].id,
                event_type=ConversationEventType.EMAIL_SENT,
                rule_name="PACING_JITTER_RELEASE",
                model_version="claude-3-5-sonnet",
                prompt_version="outbound_v1.0",
                previous_state="READY",
                new_state="SENT",
                data_payload={"latency_ms": 350}
            )
        )

    # 3. 20 replies received
    for i in range(20):
        events.append(
            ConversationEvent(
                workspace_id=ws.id,
                campaign_id=camp.id,
                lead_id=leads[i].id,
                event_type=ConversationEventType.INBOUND_RECEIVED,
                rule_name="INBOUND_WEBHOOK_PARSE",
                data_payload={"latency_ms": 10}
            )
        )

    # 4. 5 positive interest classifications
    for i in range(5):
        events.append(
            ConversationEvent(
                workspace_id=ws.id,
                campaign_id=camp.id,
                lead_id=leads[i].id,
                event_type=ConversationEventType.INTENT_CLASSIFIED,
                rule_name="14_INTENT_TAXONOMY",
                data_payload={"intent": "POSITIVE_INTEREST", "confidence": 0.96, "latency_ms": 150}
            )
        )

    # 5. 2 meetings booked
    for i in range(2):
        events.append(
            ConversationEvent(
                workspace_id=ws.id,
                campaign_id=camp.id,
                lead_id=leads[i].id,
                event_type=ConversationEventType.MEETING_BOOKED,
                rule_name="DOUBLE_BOOKING_SAFE_CONFIRM",
                data_payload={"slot": "Friday 10:00 AM", "latency_ms": 220}
            )
        )

    db_session.add_all(events)
    await db_session.commit()

    # Run funnel aggregation
    report: FunnelReport = await get_workspace_funnel(
        workspace_id=ws.id,
        campaign_id=camp.id,
        db=db_session
    )

    # Assert Funnel Counts
    assert report.enrolled_leads == 100
    assert report.emails_sent == 95
    assert report.emails_delivered == 95
    assert report.replies_received == 20
    assert report.positive_replies == 5
    assert report.qualified_leads == 5
    assert report.meetings_booked == 2

    # Assert Computed Conversion Rates
    # Delivery Rate = 95 / 95 * 100 = 100.0%
    assert report.delivery_rate == 100.0

    # Reply Rate = 20 / 95 * 100 = 21.05%
    assert report.reply_rate == round(20 / 95 * 100, 2)
    assert report.reply_rate == 21.05

    # Positive Reply Rate = 5 / 20 * 100 = 25.0%
    assert report.positive_reply_rate == 25.0

    # Booking Rate = 2 / 5 * 100 = 40.0%
    assert report.booking_rate == 40.0

    # Qualification Rate = 5 / 100 * 100 = 5.0%
    assert report.qualification_rate == 5.0

    # Average AI Latency computed across events with latency
    assert report.average_ai_latency_ms > 0


@pytest.mark.asyncio
async def test_analytics_and_usage_rest_endpoints(client: AsyncClient):
    """
    Tests REST endpoints:
    - GET /api/v1/analytics/overview
    - GET /api/v1/analytics/events
    - GET /api/v1/campaigns/{id}/analytics
    - GET /api/v1/usage/summary
    """
    # 1. Register user & authenticate
    reg_res = await client.post("/api/v1/auth/register", json={
        "email": "analytics.director@saasmetrics.io",
        "password": "StrongPassword123!",
        "workspace_name": "SaaS Metrics HQ"
    })
    assert reg_res.status_code == 201, reg_res.text
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Test GET /api/v1/analytics/overview
    overview_res = await client.get("/api/v1/analytics/overview", headers=headers)
    assert overview_res.status_code == 200, overview_res.text
    overview_data = overview_res.json()
    assert "funnel" in overview_data
    assert "quality_benchmarks" in overview_data
    assert overview_data["quality_benchmarks"]["unsubscribe_recall_rate"] == 100.0
    assert overview_data["quality_benchmarks"]["hallucination_rate"] == 0.0

    # 3. Test GET /api/v1/analytics/events
    events_res = await client.get("/api/v1/analytics/events", headers=headers)
    assert events_res.status_code == 200, events_res.text
    assert isinstance(events_res.json(), list)

    # 4. Create Campaign to test campaign-specific analytics
    camp_res = await client.post("/api/v1/campaigns", json={
        "name": "Q4 Outbound Funnel",
        "objective": "DEMO_BOOKING",
        "steps": [
            {"step_number": 1, "channel": "EMAIL", "template_subject": "Quick intro", "template_body": "Hi {{first_name}}"}
        ]
    }, headers=headers)
    assert camp_res.status_code == 201, camp_res.text
    camp_id = camp_res.json()["id"]

    # Test GET /api/v1/campaigns/{id}/analytics
    camp_analytics_res = await client.get(f"/api/v1/campaigns/{camp_id}/analytics", headers=headers)
    assert camp_analytics_res.status_code == 200, camp_analytics_res.text
    camp_funnel = camp_analytics_res.json()
    assert camp_funnel["campaign_id"] == camp_id
    assert "delivery_rate" in camp_funnel

    # 5. Log a usage event and test GET /api/v1/usage/summary
    usage_res = await client.post("/api/v1/usage/events", json={
        "event_type": "MODEL_TOKENS",
        "units": 15000,
        "cost_estimate_usd": "0.135000",
        "metadata_json": {"model": "claude-3-5-sonnet", "latency_ms": 360}
    }, headers=headers)
    assert usage_res.status_code == 201, usage_res.text

    summary_res = await client.get("/api/v1/usage/summary", headers=headers)
    assert summary_res.status_code == 200, summary_res.text
    summary_data = summary_res.json()
    assert summary_data["total_units"] >= 15000
    assert "model_breakdown" in summary_data
    assert "claude-3-5-sonnet" in summary_data["model_breakdown"]
    assert "spending_percentage" in summary_data
