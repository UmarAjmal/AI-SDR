import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_tenant_isolation_boundary(client: AsyncClient):
    # 1. Register User A in Workspace A
    user_a_payload = {
        "email": "user.a@company-a.com",
        "password": "PasswordUserA123!",
        "workspace_name": "Workspace Alpha"
    }
    res_a = await client.post("/api/v1/auth/register", json=user_a_payload)
    assert res_a.status_code == 201
    data_a = res_a.json()
    token_a = data_a["access_token"]
    ws_a_id = data_a["active_workspace_id"]

    # 2. Register User B in Workspace B
    user_b_payload = {
        "email": "user.b@company-b.com",
        "password": "PasswordUserB123!",
        "workspace_name": "Workspace Beta"
    }
    res_b = await client.post("/api/v1/auth/register", json=user_b_payload)
    assert res_b.status_code == 201
    data_b = res_b.json()
    token_b = data_b["access_token"]
    ws_b_id = data_b["active_workspace_id"]

    assert ws_a_id != ws_b_id

    # 3. User A logs a usage event in Workspace A
    headers_a = {"Authorization": f"Bearer {token_a}"}
    usage_event_payload = {
        "event_type": "MODEL_TOKENS",
        "units": 1500,
        "cost_estimate_usd": 0.004500,
        "metadata_json": {"model": "claude-3-5-sonnet", "purpose": "outbound_draft"}
    }
    post_event_res = await client.post("/api/v1/usage/events", json=usage_event_payload, headers=headers_a)
    assert post_event_res.status_code == 201

    # User A checks usage summary -> Should see 1500 units
    summary_a_res = await client.get("/api/v1/usage/summary", headers=headers_a)
    assert summary_a_res.status_code == 200
    assert summary_a_res.json()["total_units"] == 1500

    # 4. User B checks usage summary in Workspace B -> MUST BE 0 (Cannot see Workspace A's data)
    headers_b = {"Authorization": f"Bearer {token_b}"}
    summary_b_res = await client.get("/api/v1/usage/summary", headers=headers_b)
    assert summary_b_res.status_code == 200
    assert summary_b_res.json()["total_units"] == 0
    assert summary_b_res.json()["total_events"] == 0

    # 5. User B attempts to access Workspace A by maliciously injecting X-Workspace-Id header
    spoofed_headers = {
        "Authorization": f"Bearer {token_b}",
        "X-Workspace-Id": ws_a_id
    }
    spoof_res = await client.get("/api/v1/workspaces/current", headers=spoofed_headers)
    # CRITICAL: Must be rejected with 403 Forbidden!
    assert spoof_res.status_code == 403
    assert "no membership or access rights" in spoof_res.json()["detail"]

    # 6. User B attempts to update Workspace A settings
    spoof_update_res = await client.put(
        "/api/v1/workspaces/current",
        json={"name": "Hacked Workspace Name"},
        headers=spoofed_headers
    )
    assert spoof_update_res.status_code == 403

    # Verify Workspace A's name remains uncompromised
    current_a = await client.get("/api/v1/workspaces/current", headers=headers_a)
    assert current_a.status_code == 200
    assert current_a.json()["name"] == "Workspace Alpha"

@pytest.mark.asyncio
async def test_audit_log_tenant_isolation(client: AsyncClient):
    # Register User 1
    res1 = await client.post("/api/v1/auth/register", json={
        "email": "audit1@corp1.com",
        "password": "Password123!",
        "workspace_name": "Corp 1"
    })
    token1 = res1.json()["access_token"]

    # Register User 2
    res2 = await client.post("/api/v1/auth/register", json={
        "email": "audit2@corp2.com",
        "password": "Password123!",
        "workspace_name": "Corp 2"
    })
    token2 = res2.json()["access_token"]

    # User 1 fetches audit logs
    logs1 = await client.get("/api/v1/audit-logs", headers={"Authorization": f"Bearer {token1}"})
    assert logs1.status_code == 200
    items1 = logs1.json()
    assert len(items1) >= 1
    # Ensure every log has workspace_id == user1's workspace
    for item in items1:
        assert item["workspace_id"] == res1.json()["active_workspace_id"]
        assert item["actor_email"] == "audit1@corp1.com"

    # User 2 fetches audit logs
    logs2 = await client.get("/api/v1/audit-logs", headers={"Authorization": f"Bearer {token2}"})
    assert logs2.status_code == 200
    items2 = logs2.json()
    for item in items2:
        assert item["workspace_id"] == res2.json()["active_workspace_id"]
        assert item["actor_email"] == "audit2@corp2.com"
