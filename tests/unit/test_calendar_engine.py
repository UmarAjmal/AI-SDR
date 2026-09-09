import asyncio
import pytest
from datetime import datetime, timedelta, timezone
import zoneinfo
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from httpx import AsyncClient

from packages.common.models.workspace import Workspace
from packages.common.models.crm import CRMLead
from packages.common.models.campaign import Campaign, CampaignLead, LeadSequenceState, ConversationEvent
from packages.common.models.calendar import CalendarConnection, Appointment, CalendarProviderType, AppointmentStatus
from packages.common.encryption import TokenEncryptor
from packages.common.distributed_lock import LockAcquisitionError
from packages.calendar.base import FreeBusyBlock, BookingRequest, BookingConfirmation
from packages.calendar.availability import AvailabilityEngine
from apps.api.core.security import create_access_token

@pytest.mark.asyncio
async def test_timezone_aware_free_busy_slot_resolution(db_session: AsyncSession):
    workspace_id = "ws-cal-test-1"
    encryptor = TokenEncryptor()

    conn = CalendarConnection(
        workspace_id=workspace_id,
        provider=CalendarProviderType.GOOGLE,
        account_email="host.sdr@enterprise.com",
        encrypted_access_token=encryptor.encrypt("mock-google-token"),
        encrypted_refresh_token=encryptor.encrypt("mock-refresh-token"),
        token_expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        sync_status="CONNECTED",
        working_hours_json={
            "start_time": "09:00",
            "end_time": "17:00",
            "days": [0, 1, 2, 3, 4]  # Mon-Fri
        },
        buffer_minutes=15,
        timezone="America/New_York"
    )
    db_session.add(conn)
    await db_session.flush()

    # Create mock provider returning a busy block at 2:00 PM - 2:30 PM EDT tomorrow
    host_tz = zoneinfo.ZoneInfo("America/New_York")
    tomorrow = (datetime.now(host_tz) + timedelta(days=1)).replace(hour=14, minute=0, second=0, microsecond=0)
    busy_start_utc = tomorrow.astimezone(timezone.utc)
    busy_end_utc = busy_start_utc + timedelta(minutes=30)

    mock_provider = MagicMock()
    mock_provider.get_free_busy = AsyncMock(return_value=[
        FreeBusyBlock(start_time=busy_start_utc, end_time=busy_end_utc)
    ])

    # Search slots in prospect timezone: America/Los_Angeles (PDT)
    slots = await AvailabilityEngine.find_available_slots(
        conn=conn,
        prospect_timezone="America/Los_Angeles",
        start_date=busy_start_utc - timedelta(hours=4),
        days_ahead=3,
        slot_duration_minutes=30,
        provider=mock_provider,
        db=db_session
    )

    assert len(slots) > 0
    for slot in slots:
        assert slot.timezone == "America/Los_Angeles"
        
        # Verify slot in host timezone is strictly within 09:00 - 17:00 EDT
        slot_host_start = slot.start_time.astimezone(host_tz)
        slot_host_end = slot.end_time.astimezone(host_tz)
        assert slot_host_start.hour >= 9
        assert (slot_host_end.hour < 17 or (slot_host_end.hour == 17 and slot_host_end.minute == 0))

        # Verify no slot overlaps with 15-min buffered busy block (1:45 PM - 2:45 PM EDT)
        buffered_start = busy_start_utc - timedelta(minutes=15)
        buffered_end = busy_end_utc + timedelta(minutes=15)
        slot_start_utc = slot.start_time.astimezone(timezone.utc)
        slot_end_utc = slot.end_time.astimezone(timezone.utc)

        overlaps = (slot_start_utc < buffered_end and slot_end_utc > buffered_start)
        assert not overlaps, f"Slot {slot_start_utc} overlapped with buffered busy {buffered_start} - {buffered_end}"

@pytest.mark.asyncio
async def test_concurrency_safe_meeting_booking_prevents_double_booking(db_session: AsyncSession):
    workspace_id = "ws-cal-test-2"
    encryptor = TokenEncryptor()

    conn = CalendarConnection(
        workspace_id=workspace_id,
        provider=CalendarProviderType.GOOGLE,
        account_email="host.rep@codenter.ai",
        encrypted_access_token=encryptor.encrypt("mock-token"),
        encrypted_refresh_token=encryptor.encrypt("mock-refresh"),
        token_expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        sync_status="CONNECTED",
        timezone="UTC"
    )
    lead = CRMLead(
        workspace_id=workspace_id,
        email="buyer@fastscale.com",
        first_name="Diana",
        company_name="FastScale"
    )
    db_session.add_all([conn, lead])
    await db_session.commit()

    slot_time = datetime.now(timezone.utc) + timedelta(days=2)
    slot_time = slot_time.replace(minute=0, second=0, microsecond=0)

    booking_req = BookingRequest(
        title="Intro Discovery",
        start_time=slot_time,
        end_time=slot_time + timedelta(minutes=30),
        attendee_email=lead.email,
        host_email=conn.account_email,
        timezone="UTC"
    )

    mock_provider = MagicMock()
    mock_provider.create_meeting_event = AsyncMock(return_value=BookingConfirmation(
        event_id="cal-evt-999",
        title="Intro Discovery",
        start_time=booking_req.start_time,
        end_time=booking_req.end_time,
        attendee_email=booking_req.attendee_email,
        host_email=booking_req.host_email,
        meeting_link="https://meet.google.com/abc-defg-hij",
        status="CONFIRMED"
    ))

    # First booking request succeeds
    conf1 = await AvailabilityEngine.book_meeting_concurrency_safe(
        workspace_id=workspace_id,
        connection_id=conn.id,
        lead_id=lead.id,
        booking=booking_req,
        provider=mock_provider,
        db=db_session
    )
    assert conf1.status == "CONFIRMED"
    assert conf1.event_id == "cal-evt-999"

    # Second booking request for the exact same slot must be rejected
    with pytest.raises(Exception) as exc_info:
        await AvailabilityEngine.book_meeting_concurrency_safe(
            workspace_id=workspace_id,
            connection_id=conn.id,
            lead_id=lead.id,
            booking=booking_req,
            provider=mock_provider,
            db=db_session
        )
    assert "already booked" in str(exc_info.value).lower() or "conflict" in str(exc_info.value).lower()

    # Exactly 1 confirmed appointment in database
    appts = (await db_session.execute(
        select(Appointment).where(Appointment.calendar_connection_id == conn.id)
    )).scalars().all()
    assert len(appts) == 1
    assert appts[0].status == AppointmentStatus.CONFIRMED

@pytest.mark.asyncio
async def test_meeting_booking_triggers_stop_condition_4_sequence_halt(db_session: AsyncSession):
    workspace_id = "ws-cal-test-3"
    encryptor = TokenEncryptor()

    conn = CalendarConnection(
        workspace_id=workspace_id,
        provider=CalendarProviderType.MICROSOFT,
        account_email="host.ms@codenter.ai",
        encrypted_access_token=encryptor.encrypt("mock-ms-token"),
        encrypted_refresh_token=encryptor.encrypt("mock-refresh"),
        token_expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        sync_status="CONNECTED"
    )
    lead = CRMLead(
        workspace_id=workspace_id,
        email="prospect.vip@global.com",
        first_name="Jonathan",
        company_name="Global Enterprises"
    )
    campaign = Campaign(
        workspace_id=workspace_id,
        name="Outbound Q4 Enterprise"
    )
    db_session.add_all([conn, lead, campaign])
    await db_session.flush()

    campaign_lead = CampaignLead(
        workspace_id=workspace_id,
        campaign_id=campaign.id,
        lead_id=lead.id,
        state=LeadSequenceState.WAITING
    )
    db_session.add(campaign_lead)
    await db_session.commit()

    slot_time = datetime.now(timezone.utc) + timedelta(days=3)
    booking_req = BookingRequest(
        title="Codenter Platform Walkthrough",
        start_time=slot_time,
        end_time=slot_time + timedelta(minutes=30),
        attendee_email=lead.email,
        host_email=conn.account_email
    )

    mock_provider = MagicMock()
    mock_provider.create_meeting_event = AsyncMock(return_value=BookingConfirmation(
        event_id="ms-teams-evt-123",
        title=booking_req.title,
        start_time=booking_req.start_time,
        end_time=booking_req.end_time,
        attendee_email=booking_req.attendee_email,
        host_email=booking_req.host_email,
        meeting_link="https://teams.microsoft.com/l/meetup-join/123",
        status="CONFIRMED"
    ))

    await AvailabilityEngine.book_meeting_concurrency_safe(
        workspace_id=workspace_id,
        connection_id=conn.id,
        lead_id=lead.id,
        campaign_id=campaign.id,
        booking=booking_req,
        provider=mock_provider,
        db=db_session
    )

    # Verify sequence halted instantly to MEETING_BOOKED (Stop Condition #4)
    refreshed_cl = (await db_session.execute(
        select(CampaignLead).where(CampaignLead.id == campaign_lead.id)
    )).scalar_one()

    assert refreshed_cl.state == LeadSequenceState.MEETING_BOOKED
    assert refreshed_cl.stop_reason == "MEETING_CONFIRMED"

    # Verify ConversationEvent recorded
    event = (await db_session.execute(
        select(ConversationEvent).where(
            ConversationEvent.workspace_id == workspace_id,
            ConversationEvent.event_type == "MEETING_BOOKED"
        )
    )).scalar_one_or_none()

    assert event is not None
    assert event.rule_matched == "STOP_CONDITION_MEETING_CONFIRMED"
    assert event.new_state == "MEETING_BOOKED"

@pytest.mark.asyncio
async def test_calendar_api_endpoints(client: AsyncClient, db_session: AsyncSession):
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "cal.admin@calendartest.org",
            "password": "StrongPassword123!",
            "workspace_name": "Calendar Test Org"
        }
    )
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Connect Calendar
    post_res = await client.post(
        "/api/v1/calendar/connections",
        json={
            "provider": "GOOGLE",
            "account_email": "sales@calendartest.org",
            "access_token": "mock-access-token",
            "refresh_token": "mock-refresh-token",
            "working_hours_start": "09:00",
            "working_hours_end": "17:00",
            "working_days": [0, 1, 2, 3, 4],
            "buffer_minutes": 15,
            "timezone": "America/New_York"
        },
        headers=headers
    )
    assert post_res.status_code == 201
    conn_data = post_res.json()
    assert conn_data["account_email"] == "sales@calendartest.org"
    conn_id = conn_data["id"]

    # 2. List Calendar Connections
    list_res = await client.get("/api/v1/calendar/connections", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    # 3. Query Slots
    slots_res = await client.get(
        f"/api/v1/calendar/slots?connection_id={conn_id}&prospect_timezone=America/Los_Angeles&days_ahead=5",
        headers=headers
    )
    assert slots_res.status_code == 200
    slots = slots_res.json()
    assert isinstance(slots, list)

    # 4. List Appointments (Initially empty)
    appts_res = await client.get("/api/v1/calendar/appointments", headers=headers)
    assert appts_res.status_code == 200
    assert len(appts_res.json()) == 0
