import pytest
import httpx
from datetime import datetime, timezone
from packages.common.models.crm import CRMProviderType, CRMConnection, CRMSyncStatus, CRMLead
from packages.crm.base import CanonicalContact
from packages.crm.normalizer import LeadNormalizer
from packages.crm.adapters.salesforce_adapter import SalesforceProvider
from packages.crm.adapters.pipedrive_adapter import PipedriveProvider
from packages.crm.adapters.zoho_adapter import ZohoProvider
from packages.crm.sync_service import CRMSyncService

# -------------------------------------------------------------
# 1. Salesforce Adapter & Normalizer Tests
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_salesforce_adapter_fetch_and_normalize():
    mock_salesforce_response = {
        "totalSize": 2,
        "done": False,
        "nextRecordsUrl": "/services/data/v59.0/query/01gD00000022SuVIAU-2000",
        "records": [
            {
                "attributes": {"type": "Lead", "url": "/services/data/v59.0/sobjects/Lead/00Q5g00000abc123"},
                "Id": "00Q5g00000abc123",
                "FirstName": "Marc",
                "LastName": "Benioff",
                "Email": "marc@salesforce.com",
                "Phone": "+1 415 901 7000",
                "MobilePhone": None,
                "Title": "CEO",
                "Company": "Salesforce Inc",
                "Website": "https://www.salesforce.com",
                "Industry": "Cloud Software",
                "NumberOfEmployees": 75000,
                "City": "San Francisco",
                "State": "CA",
                "Country": "USA",
                "AnnualRevenue": 34000000000,
                "Status": "Working - Contacted",
                "OwnerId": "0055g00000owner1",
                "Description": "Met at Dreamforce 2026",
                "HasOptedOutOfEmail": False,
                "DoNotCall": False
            },
            {
                "Id": "00Q5g00000def456",
                "FirstName": "Opted",
                "LastName": "Out",
                "Email": "optout@acme.corp",
                "Title": "Director",
                "Company": "Acme",
                "HasOptedOutOfEmail": True,
                "DoNotCall": True,
                "Status": "Unsubscribed"
            }
        ]
    }

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        if "query" in str(request.url):
            return httpx.Response(200, json=mock_salesforce_response)
        elif request.method == "PATCH" and "Lead/00Q5g00000abc123" in str(request.url):
            return httpx.Response(204)
        return httpx.Response(404)

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as mock_client:
        adapter = SalesforceProvider(
            instance_url="https://testorg.my.salesforce.com",
            mock_client=mock_client
        )
        batch = await adapter.fetch_contacts(access_token="mock_sf_token", limit=10)

        assert len(batch.contacts) == 2
        assert batch.has_more is True
        assert batch.next_cursor == "/services/data/v59.0/query/01gD00000022SuVIAU-2000"

        c1 = batch.contacts[0]
        assert c1.email == "marc@salesforce.com"
        assert c1.first_name == "Marc"
        assert c1.last_name == "Benioff"
        assert c1.company_name == "Salesforce Inc"
        assert c1.domain == "salesforce.com"
        assert c1.employee_count == 75000
        assert c1.opt_out is False

        c2 = batch.contacts[1]
        assert c2.opt_out is True
        assert c2.do_not_contact is True

        # Test Update Lead
        updated = await adapter.update_contact(
            access_token="mock_sf_token",
            contact_id="00Q5g00000abc123",
            fields={"Status": "Closed - Converted"}
        )
        assert updated is True

# -------------------------------------------------------------
# 2. Pipedrive Adapter & Normalizer Tests
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_pipedrive_adapter_fetch_and_normalize():
    mock_pipedrive_response = {
        "success": True,
        "data": [
            {
                "id": 1001,
                "name": "Timo Rein",
                "first_name": "Timo",
                "last_name": "Rein",
                "email": [
                    {"value": "timo@pipedrive.com", "primary": True},
                    {"value": "timo.personal@gmail.com", "primary": False}
                ],
                "phone": [
                    {"value": "+372 555 1234", "primary": True}
                ],
                "org_name": "Pipedrive OU",
                "job_title": "Co-founder",
                "owner_id": {"id": 42, "name": "Admin Owner"},
                "marketing_status": "subscribed"
            },
            {
                "id": 1002,
                "name": "Unsub Prospect",
                "email": [{"value": "unsub@test.com", "primary": True}],
                "marketing_status": "unsubscribed"
            }
        ],
        "additional_data": {
            "pagination": {
                "start": 0,
                "limit": 100,
                "more_items_in_collection": True,
                "next_start": 100
            }
        }
    }

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and "persons" in str(request.url):
            return httpx.Response(200, json=mock_pipedrive_response)
        elif request.method == "PUT" and "persons/1001" in str(request.url):
            return httpx.Response(200, json={"success": True})
        return httpx.Response(404)

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as mock_client:
        adapter = PipedriveProvider(mock_client=mock_client)
        batch = await adapter.fetch_contacts(access_token="mock_40_char_token_1234567890abcdef1234")

        assert len(batch.contacts) == 2
        assert batch.has_more is True
        assert batch.next_cursor == "100"

        c1 = batch.contacts[0]
        assert c1.email == "timo@pipedrive.com"
        assert c1.first_name == "Timo"
        assert c1.last_name == "Rein"
        assert c1.phone == "+372 555 1234"
        assert c1.company_name == "Pipedrive OU"
        assert c1.domain == "pipedrive.com"
        assert c1.opt_out is False

        c2 = batch.contacts[1]
        assert c2.opt_out is True

        # Test Update Person
        updated = await adapter.update_contact(
            access_token="mock_pipedrive_token",
            contact_id="1001",
            fields={"job_title": "Executive Chairman"}
        )
        assert updated is True

# -------------------------------------------------------------
# 3. Zoho Adapter & Normalizer Tests
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_zoho_adapter_fetch_and_normalize():
    mock_zoho_response = {
        "data": [
            {
                "id": "410000000123456",
                "First_Name": "Sridhar",
                "Last_Name": "Vembu",
                "Email": "sridhar@corp.zoho.com",
                "Phone": "+91 44 6744 7070",
                "Designation": "CEO & Founder",
                "Company": "Zoho Corporation",
                "Website": "https://www.zoho.com",
                "Industry": "Enterprise Software",
                "No_of_Employees": 15000,
                "City": "Chennai",
                "State": "Tamil Nadu",
                "Country": "India",
                "Annual_Revenue": 1000000000,
                "Lead_Status": "Pre-Qualified",
                "Owner": {"id": "1111", "name": "Global Rep"},
                "Description": "High priority inbound account",
                "Email_Opt_Out": False
            }
        ],
        "info": {
            "per_page": 100,
            "count": 1,
            "page": 1,
            "more_records": False
        }
    }

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and "Leads" in str(request.url):
            return httpx.Response(200, json=mock_zoho_response)
        elif request.method == "PUT" and "Leads/410000000123456" in str(request.url):
            return httpx.Response(200, json={"data": [{"code": "SUCCESS"}]})
        return httpx.Response(404)

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as mock_client:
        adapter = ZohoProvider(mock_client=mock_client)
        batch = await adapter.fetch_contacts(access_token="mock_zoho_oauth_token")

        assert len(batch.contacts) == 1
        assert batch.has_more is False

        c1 = batch.contacts[0]
        assert c1.email == "sridhar@corp.zoho.com"
        assert c1.first_name == "Sridhar"
        assert c1.last_name == "Vembu"
        assert c1.company_name == "Zoho Corporation"
        assert c1.domain == "zoho.com"
        assert c1.employee_count == 15000
        assert c1.revenue_band == "1000000000"
        assert c1.opt_out is False

        # Test Update Lead
        updated = await adapter.update_contact(
            access_token="mock_zoho_token",
            contact_id="410000000123456",
            fields={"Lead_Status": "Contacted"}
        )
        assert updated is True

# -------------------------------------------------------------
# 4. CRMSyncService Multi-Provider Factory Test
# -------------------------------------------------------------
def test_crm_sync_service_provider_resolution():
    conn_hubspot = CRMConnection(
        id="conn-1",
        workspace_id="ws-1",
        provider=CRMProviderType.HUBSPOT,
        encrypted_access_token="dummy",
        encrypted_refresh_token="dummy"
    )
    p1 = CRMSyncService.get_provider(conn_hubspot)
    assert p1.__class__.__name__ == "HubSpotProvider"

    conn_sf = CRMConnection(
        id="conn-2",
        workspace_id="ws-1",
        provider=CRMProviderType.SALESFORCE,
        encrypted_access_token="dummy",
        encrypted_refresh_token="dummy",
        field_mappings_json={"instance_url": "https://custom.my.salesforce.com"}
    )
    p2 = CRMSyncService.get_provider(conn_sf)
    assert p2.__class__.__name__ == "SalesforceProvider"
    assert p2.instance_url == "https://custom.my.salesforce.com"

    conn_pd = CRMConnection(
        id="conn-3",
        workspace_id="ws-1",
        provider=CRMProviderType.PIPEDRIVE,
        encrypted_access_token="dummy",
        encrypted_refresh_token="dummy"
    )
    p3 = CRMSyncService.get_provider(conn_pd)
    assert p3.__class__.__name__ == "PipedriveProvider"

    conn_zoho = CRMConnection(
        id="conn-4",
        workspace_id="ws-1",
        provider=CRMProviderType.ZOHO,
        encrypted_access_token="dummy",
        encrypted_refresh_token="dummy",
        field_mappings_json={"api_domain": "https://www.zohoapis.eu"}
    )
    p4 = CRMSyncService.get_provider(conn_zoho)
    assert p4.__class__.__name__ == "ZohoProvider"
    assert "zohoapis.eu" in p4.base_api
