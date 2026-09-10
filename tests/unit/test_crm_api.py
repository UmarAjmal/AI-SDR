import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from packages.common.models.user import User
from packages.common.models.workspace import WorkspaceMember
from packages.common.models.crm import CRMLead, CRMConnection, CRMProviderType, CRMSyncStatus
from packages.common.encryption import TokenEncryptor

@pytest.mark.asyncio
async def test_crm_and_leads_api_endpoints(client: AsyncClient, db_session: AsyncSession):
    # 1. Register user & workspace
    reg_res = await client.post("/api/v1/auth/register", json={
        "email": "crm.director@enterprise.com",
        "password": "StrongPassword123!",
        "workspace_name": "CRM Enterprise Corp"
    })
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Test GET OAuth Authorization URL
    connect_res = await client.post(
        "/api/v1/integrations/crm/HUBSPOT/connect?redirect_uri=https://app.codenter.ai/callback",
        headers=headers
    )
    assert connect_res.status_code == 200
    auth_data = connect_res.json()
    assert "https://app.hubspot.com/oauth/authorize" in auth_data["authorization_url"]
    assert "codenter_" in auth_data["state"]

    # 3. Directly create a CRMConnection and sample leads in the test DB
    u_res = await db_session.execute(select(User).where(User.email == "crm.director@enterprise.com"))
    user = u_res.scalar_one()
    m_res = await db_session.execute(select(WorkspaceMember).where(WorkspaceMember.user_id == user.id))
    member = m_res.scalar_one()
    ws_id = member.workspace_id

    encryptor = TokenEncryptor()
    conn = CRMConnection(
        workspace_id=ws_id,
        provider=CRMProviderType.HUBSPOT,
        account_id="hub-portal-99",
        account_name="HubSpot Production",
        encrypted_access_token=encryptor.encrypt("test-access-token-12345"),
        encrypted_refresh_token=encryptor.encrypt("refresh-token-12345"),
        field_mappings_json={},
        sync_status=CRMSyncStatus.CONNECTED
    )
    db_session.add(conn)
    await db_session.flush()

    lead_hot = CRMLead(
        workspace_id=ws_id,
        crm_connection_id=conn.id,
        first_name="Marcus",
        last_name="Vance",
        email="marcus.vance@techgiant.com",
        job_title="VP of Sales",
        company_name="TechGiant Inc",
        domain="techgiant.com",
        industry="SaaS",
        total_score=94.0,
        icp_score=40.0,
        intent_score=20.0,
        opt_out=False,
        do_not_contact=False,
        score_reasons_json=[{"category": "ICP_FIT", "points": 40.0, "reason": "Target Executive Role"}]
    )
    lead_cold = CRMLead(
        workspace_id=ws_id,
        crm_connection_id=conn.id,
        first_name="Junior",
        last_name="Intern",
        email="intern@studentcorp.com",
        job_title="Summer Intern",
        company_name="Student Corp",
        domain="studentcorp.com",
        industry="Education",
        total_score=22.0,
        icp_score=5.0,
        intent_score=0.0,
        opt_out=False,
        do_not_contact=False,
        score_reasons_json=[{"category": "NEGATIVE_DEDUCTION", "points": -15.0, "reason": "Intern Role"}]
    )
    db_session.add(lead_hot)
    db_session.add(lead_cold)
    await db_session.commit()

    # 4. Verify List CRM Connections
    conns_res = await client.get("/api/v1/integrations/crm/connections", headers=headers)
    assert conns_res.status_code == 200
    connections = conns_res.json()
    assert len(connections) == 1
    assert connections[0]["account_id"] == "hub-portal-99"

    # 5. Verify Trigger CRM Sync
    sync_res = await client.post(f"/api/v1/integrations/crm/{conn.id}/sync", headers=headers)
    assert sync_res.status_code == 202
    assert sync_res.json()["sync_status"] == "SYNCING"

    # 6. Verify List Leads (Default: both leads returned)
    leads_res = await client.get("/api/v1/leads", headers=headers)
    assert leads_res.status_code == 200
    data = leads_res.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2

    # 7. Verify Filter Leads by score_band=HOT
    hot_res = await client.get("/api/v1/leads?score_band=HOT", headers=headers)
    assert hot_res.status_code == 200
    hot_data = hot_res.json()
    assert hot_data["total"] == 1
    assert hot_data["items"][0]["email"] == "marcus.vance@techgiant.com"

    # 8. Verify Search Leads
    search_res = await client.get("/api/v1/leads?search=TechGiant", headers=headers)
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["total"] == 1
    assert search_data["items"][0]["company_name"] == "TechGiant Inc"

    # 9. Verify Get Single Lead Detail
    lead_detail_res = await client.get(f"/api/v1/leads/{lead_hot.id}", headers=headers)
    assert lead_detail_res.status_code == 200
    lead_detail = lead_detail_res.json()
    assert lead_detail["id"] == lead_hot.id
    assert lead_detail["total_score"] == 94.0

    # 10. Verify Update Lead & Manual Opt-out
    put_res = await client.put(
        f"/api/v1/leads/{lead_hot.id}",
        json={"opt_out": True, "lead_notes": "Prospect requested no emails"},
        headers=headers
    )
    assert put_res.status_code == 200
    updated = put_res.json()
    assert updated["opt_out"] is True
    assert updated["do_not_contact"] is True

    # 11. Verify GET /api/v1/integrations/crm/{connection_id}/errors
    errors_res = await client.get(f"/api/v1/integrations/crm/{conn.id}/errors", headers=headers)
    assert errors_res.status_code == 200
    errors_data = errors_res.json()
    assert errors_data["connection_id"] == conn.id
    assert "errors" in errors_data

    # 12. Verify POST /api/v1/leads/{lead_id}/outcome
    outcome_res = await client.post(
        f"/api/v1/leads/{lead_hot.id}/outcome",
        json={"meeting_booked": True, "handoff_required": True},
        headers=headers
    )
    assert outcome_res.status_code == 200
    outcome_data = outcome_res.json()
    assert outcome_data["meeting_booked"] is True
    assert outcome_data["is_qualified"] is True
    assert outcome_data["handoff_required"] is True
    assert outcome_data["qualification_status"] == "QUALIFIED"

    # 13. Verify Incremental Webhook POST /api/v1/integrations/crm/{provider}/webhook
    webhook_res = await client.post(
        "/api/v1/integrations/crm/HUBSPOT/webhook",
        json=[{
            "eventId": "evt_webhook_999",
            "subscriptionType": "contact.propertyChange",
            "objectId": "hs-contact-777",
            "properties": {
                "hs_email_optout": "true",
                "lifecyclestage": "customer"
            }
        }]
    )
    assert webhook_res.status_code == 200
    assert webhook_res.json()["status"] == "accepted"

    # 14. Verify 10 Canonical Lead Model Groups in response
    lead_check = await client.get(f"/api/v1/leads/{lead_hot.id}", headers=headers)
    assert lead_check.status_code == 200
    lc = lead_check.json()
    # Group 1: Identity
    assert "first_name" in lc and "email" in lc and "job_title" in lc
    # Group 2: Company
    assert "company_name" in lc and "domain" in lc and "industry" in lc
    # Group 3: CRM
    assert "provider" in lc and "owner_id" in lc and "lifecycle_stage" in lc
    # Group 4: Context
    assert "lead_notes" in lc and "custom_fields" in lc
    # Group 5: Enrichment
    assert "enrichment" in lc
    # Group 6: Scoring
    assert "icp_score" in lc and "total_score" in lc and "score_band" in lc and "reasons" in lc
    # Group 7: Consent / Suppression
    assert "opt_out" in lc and "do_not_contact" in lc and "suppression_reason" in lc
    # Group 8: Campaign
    assert "state" in lc and "current_step" in lc
    # Group 9: Conversation
    assert "thread_id" in lc
    # Group 10: Outcome
    assert "is_qualified" in lc and "meeting_booked" in lc and "disqualified" in lc and "handoff_required" in lc
