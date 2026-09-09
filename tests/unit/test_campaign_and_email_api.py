import pytest
from httpx import AsyncClient, ASGITransport
from apps.api.main import app

@pytest.mark.asyncio
async def test_email_and_campaigns_api_lifecycle(client: AsyncClient):
    # Register user to get JWT token
    reg_res = await client.post("/api/v1/auth/register", json={
        "email": "campaign.master@outboundhq.com",
        "password": "StrongPassword123!",
        "workspace_name": "Outbound Growth Inc"
    })
    assert reg_res.status_code == 201, reg_res.text
    token = reg_res.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}
    # 1. Connect Mailbox Account
    acc_payload = {
        "provider": "GOOGLE",
        "email_address": "sdr@outboundhq.com",
        "daily_send_limit": 45,
        "credentials_token": "mock-oauth-token-12345"
    }
    acc_res = await client.post("/api/v1/email/accounts", json=acc_payload, headers=auth_headers)
    assert acc_res.status_code == 201, acc_res.text
    account = acc_res.json()
    assert account["email_address"] == "sdr@outboundhq.com"
    assert account["daily_send_limit"] == 45
    account_id = account["id"]

    # 2. List Accounts
    list_acc_res = await client.get("/api/v1/email/accounts", headers=auth_headers)
    assert list_acc_res.status_code == 200
    accounts = list_acc_res.json()
    assert any(a["id"] == account_id for a in accounts)

    # 3. Add to Suppression List
    supp_payload = {
        "email": "optout-user@competitor.com",
        "reason": "MANUAL",
        "source": "ADMIN_DASHBOARD"
    }
    supp_res = await client.post("/api/v1/email/suppression", json=supp_payload, headers=auth_headers)
    assert supp_res.status_code == 201
    supp_data = supp_res.json()
    assert supp_data["email"] == "optout-user@competitor.com"
    supp_id = supp_data["id"]

    # 4. List Suppression
    supp_list_res = await client.get("/api/v1/email/suppression", headers=auth_headers)
    assert supp_list_res.status_code == 200
    assert any(s["id"] == supp_id for s in supp_list_res.json())

    # 5. Create Campaign with 3 Sequence Steps
    camp_payload = {
        "name": "Mid-Market Tech Q4",
        "objective": "DEMO_BOOKING",
        "config_json": {"target_vertical": "SaaS"},
        "steps": [
            {
                "step_number": 1,
                "delay_days": 0,
                "delay_hours": 0,
                "prompt_instructions": "Initial outreach highlighting case studies",
                "template_config_json": {
                    "subject": "Question regarding outbound at {{company}}",
                    "body_text": "Hi {{first_name}}, love what you are building."
                }
            },
            {
                "step_number": 2,
                "delay_days": 3,
                "delay_hours": 0,
                "prompt_instructions": "Follow up with customer metrics",
                "template_config_json": {
                    "subject": "Re: Question regarding outbound at {{company}}",
                    "body_text": "Hi {{first_name}}, sharing a quick update."
                }
            },
            {
                "step_number": 3,
                "delay_days": 4,
                "delay_hours": 0,
                "prompt_instructions": "Breakup email",
                "template_config_json": {
                    "subject": "Closing the loop on {{company}}",
                    "body_text": "Hi {{first_name}}, assume you are busy so closing the file."
                }
            }
        ]
    }
    camp_res = await client.post("/api/v1/campaigns", json=camp_payload, headers=auth_headers)
    assert camp_res.status_code == 201, camp_res.text
    campaign = camp_res.json()
    assert campaign["name"] == "Mid-Market Tech Q4"
    assert len(campaign["steps"]) == 3
    campaign_id = campaign["id"]

    # 6. Retrieve Campaign
    get_camp_res = await client.get(f"/api/v1/campaigns/{campaign_id}", headers=auth_headers)
    assert get_camp_res.status_code == 200
    assert get_camp_res.json()["status"] == "DRAFT"

    # 7. Launch Campaign
    launch_res = await client.post(f"/api/v1/campaigns/{campaign_id}/launch", headers=auth_headers)
    assert launch_res.status_code == 200
    assert launch_res.json()["status"] == "RUNNING"

    # 8. Pause Campaign
    pause_res = await client.post(f"/api/v1/campaigns/{campaign_id}/pause", headers=auth_headers)
    assert pause_res.status_code == 200
    assert pause_res.json()["status"] == "PAUSED"

    # 9. Resume Campaign
    resume_res = await client.post(f"/api/v1/campaigns/{campaign_id}/resume", headers=auth_headers)
    assert resume_res.status_code == 200
    assert resume_res.json()["status"] == "RUNNING"

    # 10. List Campaign Audit Events
    events_res = await client.get(f"/api/v1/campaigns/{campaign_id}/events", headers=auth_headers)
    assert events_res.status_code == 200
