import pytest
import httpx
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from packages.common.models.workspace import Workspace
from packages.common.models.crm import CRMConnection, CRMLead, CRMProviderType, CRMSyncStatus
from packages.common.models.knowledge import BusinessProfile
from packages.common.encryption import TokenEncryptor
from packages.crm.adapters.hubspot_adapter import HubSpotProvider
from packages.crm.sync_service import CRMSyncService

@pytest.mark.asyncio
async def test_crm_sync_service_deduplication_and_suppression(db_session: AsyncSession):
    # 1. Setup workspace & business profile
    ws = Workspace(name="Sync Test Org", domain="synctest.org", settings={})
    db_session.add(ws)
    await db_session.flush()

    profile = BusinessProfile(
        workspace_id=ws.id,
        company_name="Sync Test Org",
        description="Autonomous SDR Platform",
        industries=["SaaS", "Fintech"],
        offerings=[{"title": "Sales Agent"}],
        value_propositions=[],
        icp_hints={"employee_ranges": ["50-1000"]},
        is_active=True
    )
    db_session.add(profile)

    # 2. Setup existing lead in DB that should be updated, not duplicated
    encryptor = TokenEncryptor()
    conn = CRMConnection(
        workspace_id=ws.id,
        provider=CRMProviderType.HUBSPOT,
        account_id="hub-12345",
        encrypted_access_token=encryptor.encrypt("mock-access-token"),
        encrypted_refresh_token=encryptor.encrypt("mock-refresh-token"),
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
        field_mappings_json={},
        sync_status=CRMSyncStatus.CONNECTED
    )
    db_session.add(conn)
    await db_session.flush()

    existing_lead = CRMLead(
        workspace_id=ws.id,
        crm_connection_id=conn.id,
        crm_record_id="hs-001",
        first_name="PreExisting",
        last_name="Lead",
        email="existing.contact@acme.com",
        job_title="Junior Rep",
        company_name="Acme Corp",
        domain="acme.com",
        industry="SaaS",
        opt_out=False,
        do_not_contact=False,
        bounce_status="NONE",
        total_score=10.0,
        score_reasons_json=[]
    )
    db_session.add(existing_lead)
    await db_session.commit()

    # 3. Define Mock HubSpot API Handler (Multi-page contacts + Token refresh)
    def mock_hubspot_handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        
        # Token refresh endpoint
        if "oauth/v1/token" in url_str:
            return httpx.Response(200, json={
                "access_token": "refreshed-access-token",
                "refresh_token": "new-refresh-token",
                "expires_in": 3600,
                "token_type": "Bearer"
            })

        # Contacts endpoint
        if "/crm/v3/objects/contacts" in url_str:
            params = request.url.params
            cursor = params.get("after")
            
            if not cursor:
                # Page 1: returns existing lead (with updated VP title) and a suppressed contact
                return httpx.Response(200, json={
                    "results": [
                        {
                            "id": "hs-001",
                            "properties": {
                                "firstname": "PreExisting",
                                "lastname": "Lead",
                                "email": "existing.contact@acme.com",
                                "jobtitle": "VP of Sales",  # Updated!
                                "company": "Acme Corp",
                                "domain": "acme.com",
                                "industry": "SaaS",
                                "numberofemployees": "250",
                                "lifecyclestage": "salesqualifiedlead",
                                "hs_email_optout": "false"
                            }
                        },
                        {
                            "id": "hs-002",
                            "properties": {
                                "firstname": "OptedOut",
                                "lastname": "User",
                                "email": "optout.user@domain.com",
                                "jobtitle": "CEO",
                                "company": "Domain Inc",
                                "domain": "domain.com",
                                "industry": "Fintech",
                                "numberofemployees": "80",
                                "hs_email_optout": "true"  # Suppressed!
                            }
                        }
                    ],
                    "paging": {
                        "next": {
                            "after": "cursor-page-2"
                        }
                    }
                })
            elif cursor == "cursor-page-2":
                # Page 2: returns a new lead, no further pages
                return httpx.Response(200, json={
                    "results": [
                        {
                            "id": "hs-003",
                            "properties": {
                                "firstname": "Alice",
                                "lastname": "Smith",
                                "email": "alice.smith@techcorp.io",
                                "jobtitle": "Head of Growth",
                                "company": "TechCorp",
                                "domain": "techcorp.io",
                                "industry": "SaaS",
                                "numberofemployees": "120",
                                "lifecyclestage": "lead",
                                "hs_email_optout": "false"
                            }
                        }
                    ],
                    "paging": {}
                })

        return httpx.Response(404, text="Not Found")

    transport = httpx.MockTransport(mock_hubspot_handler)
    mock_client = httpx.AsyncClient(transport=transport, base_url="https://api.hubapi.com")
    provider = HubSpotProvider(mock_client=mock_client)

    # 4. Execute CRMSyncService
    completed_conn = await CRMSyncService.sync_connection(
        workspace_id=ws.id,
        connection_id=conn.id,
        db=db_session,
        provider=provider,
        max_contacts=500
    )

    # 5. Verify Connection Status
    assert completed_conn.sync_status == CRMSyncStatus.CONNECTED
    assert completed_conn.last_sync_at is not None

    # 6. Verify Lead Deduplication
    leads_res = await db_session.execute(select(CRMLead).where(CRMLead.workspace_id == ws.id))
    all_leads = leads_res.scalars().all()
    # Should have exactly 3 leads total (hs-001 updated, hs-002 added, hs-003 added from page 2)
    assert len(all_leads) == 3

    # Check that existing lead was updated in-place without duplicate
    updated_lead_res = await db_session.execute(
        select(CRMLead).where(
            CRMLead.workspace_id == ws.id,
            CRMLead.email == "existing.contact@acme.com"
        )
    )
    updated_leads = updated_lead_res.scalars().all()
    assert len(updated_leads) == 1
    lead_001 = updated_leads[0]
    assert lead_001.job_title == "VP of Sales"
    assert lead_001.total_score >= 80.0  # Was re-scored to HOT

    # 7. Verify Suppression Propagation
    suppressed_lead_res = await db_session.execute(
        select(CRMLead).where(
            CRMLead.workspace_id == ws.id,
            CRMLead.email == "optout.user@domain.com"
        )
    )
    suppressed_lead = suppressed_lead_res.scalar_one()
    assert suppressed_lead.opt_out is True
    assert suppressed_lead.do_not_contact is True

    # 8. Verify Page 2 Lead Ingestion
    alice_lead_res = await db_session.execute(
        select(CRMLead).where(
            CRMLead.workspace_id == ws.id,
            CRMLead.email == "alice.smith@techcorp.io"
        )
    )
    alice = alice_lead_res.scalar_one()
    assert alice.first_name == "Alice"
    assert alice.total_score >= 50.0
