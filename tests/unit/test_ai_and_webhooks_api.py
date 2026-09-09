import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from packages.common.models.user import User
from packages.common.models.workspace import WorkspaceMember
from packages.common.models.knowledge import BusinessProfile, KnowledgeDocument, KnowledgeChunk
from packages.common.models.crm import CRMLead
from packages.common.models.campaign import Campaign, CampaignStep, CampaignState
from packages.common.models.email import EmailThread, EmailMessage, ThreadStatus, MessageDirection

@pytest.mark.asyncio
async def test_ai_and_webhooks_api_lifecycle(client: AsyncClient, db_session: AsyncSession):
    # 1. Register user & get token
    reg_res = await client.post("/api/v1/auth/register", json={
        "email": "ai.director@codenter.ai",
        "password": "StrongPassword123!",
        "workspace_name": "Codenter AI Lab"
    })
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    u_res = await db_session.execute(select(User).where(User.email == "ai.director@codenter.ai"))
    user = u_res.scalar_one()
    m_res = await db_session.execute(select(WorkspaceMember).where(WorkspaceMember.user_id == user.id))
    member = m_res.scalar_one()
    ws_id = member.workspace_id

    # 2. Test Classify Intent API (Regular inquiry)
    classify_res = await client.post(
        "/api/v1/ai/classify-intent",
        json={"subject": "Inquiry", "reply_text": "What does your Growth tier cost? Can you share pricing?"},
        headers=headers
    )
    assert classify_res.status_code == 200
    res_data = classify_res.json()
    assert res_data["intent"] == "PRICING"
    assert res_data["confidence"] >= 0.85

    # 3. Test Classify Intent API (Opt-out pre-LLM check)
    opt_out_res = await client.post(
        "/api/v1/ai/classify-intent",
        json={"subject": "Stop", "reply_text": "Please unsubscribe me immediately."},
        headers=headers
    )
    assert opt_out_res.status_code == 200
    opt_data = opt_out_res.json()
    assert opt_data["intent"] == "UNSUBSCRIBE"
    assert opt_data["confidence"] == 1.0

    # 4. Setup BusinessProfile and KnowledgeChunk for Verification and Draft generation
    bp = BusinessProfile(
        workspace_id=ws_id,
        company_name="Codenter AI",
        is_active=True,
        version=1,
        claims_policy={"prohibited_claims": ["100% money back guarantee"]}
    )
    doc = KnowledgeDocument(
        workspace_id=ws_id,
        url="https://codenter.ai/features",
        title="Features",
        content_hash="hash-feat-1",
        raw_text="Codenter AI SDR delivers 3.2x more qualified discovery calls in 45 days."
    )
    db_session.add_all([bp, doc])
    await db_session.flush()

    chunk = KnowledgeChunk(
        workspace_id=ws_id,
        document_id=doc.id,
        chunk_index=0,
        content="Codenter AI SDR delivers 3.2x more qualified discovery calls in 45 days.",
        token_count=16,
        embedding=[0.1] * 1536
    )
    db_session.add(chunk)
    await db_session.commit()

    # 5. Test Verify Claims Endpoint
    verify_res = await client.post(
        "/api/v1/ai/verify-claims",
        json={
            "claims": ["delivers 3.2x more qualified discovery calls in 45 days"],
            "draft_text": "Codenter AI SDR delivers 3.2x more qualified discovery calls in 45 days."
        },
        headers=headers
    )
    assert verify_res.status_code == 200
    verify_data = verify_res.json()
    assert verify_data["is_grounded"] is True
    assert len(verify_data["unsupported_claims"]) == 0

    # 6. Test Generate Outbound Draft
    lead = CRMLead(
        workspace_id=ws_id,
        email="alex.smith@cloudtarget.com",
        first_name="Alex",
        company_name="CloudTarget",
        industry="Cloud Software"
    )
    camp = Campaign(workspace_id=ws_id, name="Cloud Outbound Wave", status=CampaignState.DRAFT)
    db_session.add_all([lead, camp])
    await db_session.flush()

    step = CampaignStep(
        campaign_id=camp.id,
        step_number=1,
        delay_days=1,
        prompt_instructions="Focus on qualified pipeline acceleration",
        template_config_json={"subject": "Accelerating Outbound"}
    )
    db_session.add(step)
    await db_session.commit()

    draft_res = await client.post(
        "/api/v1/ai/generate-draft",
        json={
            "lead_id": lead.id,
            "campaign_step_id": step.id,
            "custom_instructions": "Highlight 3.2x pipeline acceleration"
        },
        headers=headers
    )
    assert draft_res.status_code == 200
    draft_data = draft_res.json()
    assert "draft" in draft_data
    assert "telemetry" in draft_data
    assert draft_data["telemetry"]["cost_usd"] >= 0.0

    # 7. Test Generate Reply Endpoint
    thread = EmailThread(
        workspace_id=ws_id,
        lead_id=lead.id,
        subject="Re: Accelerating Outbound",
        status=ThreadStatus.REPLIED
    )
    db_session.add(thread)
    await db_session.flush()

    inbound_msg = EmailMessage(
        workspace_id=ws_id,
        thread_id=thread.id,
        direction=MessageDirection.INBOUND,
        from_address=lead.email,
        to_address="sdr@codenter.ai",
        subject="Re: Accelerating Outbound",
        body_text="What is your pricing?"
    )
    db_session.add(inbound_msg)
    await db_session.commit()

    reply_res = await client.post(
        "/api/v1/ai/generate-reply",
        json={
            "thread_id": thread.id,
            "inbound_message_id": inbound_msg.id
        },
        headers=headers
    )
    assert reply_res.status_code == 200
    reply_data = reply_res.json()
    assert "body" in reply_data
    assert reply_data["confidence"] >= 0.85

    # 8. Test Webhook Endpoints
    # Microsoft handshake validation
    msft_handshake = await client.post(
        f"/api/v1/webhooks/microsoft/{ws_id}?validationToken=test-token-handshake-456"
    )
    assert msft_handshake.status_code == 200
    assert msft_handshake.text == "test-token-handshake-456"

    # Generic inbound webhook
    webhook_inbound = await client.post(
        f"/api/v1/webhooks/inbound/{ws_id}",
        json={
            "from_address": "incoming@enterprise.com",
            "to_address": "sdr@codenter.ai",
            "subject": "Quick note",
            "body_text": "We received your message"
        }
    )
    assert webhook_inbound.status_code == 202
    assert webhook_inbound.json()["status"] == "accepted"

    # Google Pub/Sub webhook
    google_webhook = await client.post(
        f"/api/v1/webhooks/google/{ws_id}",
        json={"message": {"data": ""}}
    )
    assert google_webhook.status_code == 202
    assert google_webhook.json()["status"] == "accepted"
