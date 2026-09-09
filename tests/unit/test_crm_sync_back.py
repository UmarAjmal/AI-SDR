import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from packages.common.models.crm import CRMLead, CRMConnection, CRMSyncStatus, CRMProviderType
from packages.common.models.audit import AuditLog
from packages.common.models.campaign import ConversationEvent
from packages.common.encryption import TokenEncryptor
from apps.worker.tasks.crm_sync import sync_lead_outcome_to_crm_task

@pytest.mark.asyncio
async def test_crm_sync_back_updates_hubspot_contact_and_creates_audit_log(db_session: AsyncSession):
    workspace_id = "ws-crm-sync-1"
    encryptor = TokenEncryptor()

    enc_access = encryptor.encrypt("mock-hubspot-access-token")
    enc_refresh = encryptor.encrypt("mock-hubspot-refresh-token")

    conn = CRMConnection(
        workspace_id=workspace_id,
        provider=CRMProviderType.HUBSPOT,
        account_id="hub-acct-101",
        encrypted_access_token=enc_access,
        encrypted_refresh_token=enc_refresh,
        sync_status=CRMSyncStatus.CONNECTED
    )
    db_session.add(conn)
    await db_session.flush()

    lead = CRMLead(
        workspace_id=workspace_id,
        email="qualified.buyer@scale.com",
        first_name="Victoria",
        last_name="Chase",
        job_title="VP Sales",
        company_name="Scale Co",
        crm_record_id="hs-contact-777",
        crm_connection_id=conn.id,
        qualification_status="QUALIFIED",
        is_qualified=True,
        qualification_details={
            "need": "Automate cold outreach for 30 SDRs",
            "fit_score": 95,
            "authority": "DECISION_MAKER",
            "timing": "NOW",
            "pain_points": ["Manual prospecting bottleneck"],
            "next_action": "BOOK_MEETING"
        }
    )
    db_session.add(lead)
    await db_session.commit()

    mock_hubspot = MagicMock()
    mock_hubspot.update_contact = AsyncMock(return_value=True)

    with patch("apps.worker.tasks.crm_sync.HubSpotProvider", return_value=mock_hubspot):
        result = sync_lead_outcome_to_crm_task.apply(kwargs={
            "workspace_id": workspace_id,
            "lead_id": lead.id
        }).get()
        if asyncio.iscoroutine(result) or isinstance(result, asyncio.Task):
            result = await result

    assert result["status"] == "success"
    assert result["lead_id"] == lead.id
    assert result["crm_record_id"] == "hs-contact-777"

    # Verify HubSpot update payload
    mock_hubspot.update_contact.assert_awaited_once()
    called_kwargs = mock_hubspot.update_contact.await_args.kwargs
    assert called_kwargs["contact_id"] == "hs-contact-777"
    payload = called_kwargs["fields"]
    assert payload["lifecyclestage"] == "marketingqualifiedlead"
    assert payload["hs_lead_status"] == "QUALIFIED"
    assert "Automate cold outreach" in payload["ai_sdr_qualification_summary"]

    # Verify AuditLog written
    audit_stmt = select(AuditLog).where(
        AuditLog.workspace_id == workspace_id,
        AuditLog.action == "CRM_OUTCOME_SYNC"
    )
    a_res = await db_session.execute(audit_stmt)
    audit = a_res.scalar_one_or_none()
    assert audit is not None
    assert audit.resource_id == lead.id

    # Verify ConversationEvent recorded
    event_stmt = select(ConversationEvent).where(
        ConversationEvent.workspace_id == workspace_id,
        ConversationEvent.event_type == "CRM_OUTCOME_SYNC"
    )
    e_res = await db_session.execute(event_stmt)
    event = e_res.scalar_one_or_none()
    assert event is not None
    assert event.rule_matched == "BI_DIRECTIONAL_CRM_SYNC_BACK"

@pytest.mark.asyncio
async def test_crm_sync_back_retries_on_5xx_without_dropping_local_state(db_session: AsyncSession):
    workspace_id = "ws-crm-sync-2"
    encryptor = TokenEncryptor()

    conn = CRMConnection(
        workspace_id=workspace_id,
        provider=CRMProviderType.HUBSPOT,
        account_id="hub-acct-500",
        encrypted_access_token=encryptor.encrypt("token"),
        encrypted_refresh_token=encryptor.encrypt("refresh"),
        sync_status=CRMSyncStatus.CONNECTED
    )
    db_session.add(conn)
    await db_session.flush()

    lead = CRMLead(
        workspace_id=workspace_id,
        email="resilient.lead@tech.com",
        first_name="Evan",
        crm_record_id="hs-contact-500",
        crm_connection_id=conn.id,
        qualification_status="QUALIFIED",
        is_qualified=True,
        qualification_details={"need": "Testing resilience"}
    )
    db_session.add(lead)
    await db_session.commit()

    mock_hubspot = MagicMock()
    mock_hubspot.update_contact = AsyncMock(side_effect=RuntimeError("500 Server Error from HubSpot CRM"))

    # Test that retry is invoked when CRM provider fails with 5xx
    with patch("apps.worker.tasks.crm_sync.HubSpotProvider", return_value=mock_hubspot):
        with patch.object(sync_lead_outcome_to_crm_task, "retry", side_effect=RuntimeError("TaskRetried")) as mock_retry:
            task_future = sync_lead_outcome_to_crm_task.apply(kwargs={
                "workspace_id": workspace_id,
                "lead_id": lead.id
            }).get()
            if asyncio.iscoroutine(task_future) or isinstance(task_future, asyncio.Task):
                with pytest.raises(RuntimeError, match="TaskRetried"):
                    await task_future
            mock_retry.assert_called_once()

    # Re-fetch lead to ensure local qualification state was NEVER dropped
    refreshed_lead = (await db_session.execute(
        select(CRMLead).where(CRMLead.id == lead.id)
    )).scalar_one()

    assert refreshed_lead.qualification_status == "QUALIFIED"
    assert refreshed_lead.is_qualified is True
    assert refreshed_lead.qualification_details["need"] == "Testing resilience"
