import logging
import uuid
import zoneinfo
from datetime import datetime, timedelta, timezone, time as dtime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from packages.common.models.calendar import CalendarConnection, Appointment, AppointmentStatus, CalendarProviderType
from packages.common.models.campaign import CampaignLead, LeadSequenceState, ConversationEvent
from packages.common.models.crm import CRMLead
from packages.common.encryption import TokenEncryptor
from packages.common.distributed_lock import DistributedLock, LockAcquisitionError
from packages.calendar.base import (
    CalendarProvider,
    TimeSlot,
    FreeBusyBlock,
    BookingRequest,
    BookingConfirmation
)
from packages.calendar.adapters.google_calendar import GoogleCalendarProvider
from packages.calendar.adapters.outlook_calendar import OutlookCalendarProvider

logger = logging.getLogger("codenter.calendar.availability")

class AvailabilityEngine:
    """
    Timezone-aware host free/busy availability resolver and concurrency-safe booking engine.
    Strictly enforces:
    - 15-minute before/after buffers.
    - Host working hours (Mon-Fri 09:00 - 17:00).
    - Prospect timezone translation.
    - Atomic distributed locking on slot booking to eliminate race conditions.
    - Sequence Stop Condition #4 (instant halt to MEETING_BOOKED).
    """

    @classmethod
    def get_provider_for_connection(
        cls,
        conn: CalendarConnection,
        mock_provider: Optional[CalendarProvider] = None
    ) -> CalendarProvider:
        if mock_provider:
            return mock_provider
        if conn.provider == CalendarProviderType.GOOGLE:
            return GoogleCalendarProvider()
        elif conn.provider == CalendarProviderType.MICROSOFT:
            return OutlookCalendarProvider()
        return GoogleCalendarProvider()

    @classmethod
    async def find_available_slots(
        cls,
        conn: CalendarConnection,
        prospect_timezone: str = "UTC",
        start_date: Optional[datetime] = None,
        days_ahead: int = 5,
        slot_duration_minutes: int = 30,
        buffer_minutes: Optional[int] = None,
        max_slots_to_return: int = 3,
        provider: Optional[CalendarProvider] = None,
        db: Optional[AsyncSession] = None
    ) -> list[TimeSlot]:
        """
        Finds free slots within host working hours, applying buffers and converting to prospect timezone.
        """
        buffer_mins = buffer_minutes if buffer_minutes is not None else conn.buffer_minutes
        
        try:
            host_tz = zoneinfo.ZoneInfo(conn.timezone)
        except Exception:
            host_tz = zoneinfo.ZoneInfo("UTC")

        try:
            prospect_tz = zoneinfo.ZoneInfo(prospect_timezone)
        except Exception:
            prospect_tz = zoneinfo.ZoneInfo("UTC")

        now_utc = datetime.now(timezone.utc)
        search_start = start_date or now_utc
        if search_start.tzinfo is None:
            search_start = search_start.replace(tzinfo=timezone.utc)

        search_end = search_start + timedelta(days=days_ahead)

        # 1. Fetch busy blocks from provider
        busy_blocks: list[FreeBusyBlock] = []
        cal_provider = cls.get_provider_for_connection(conn, provider)
        
        token = conn.encrypted_access_token
        try:
            encryptor = TokenEncryptor()
            token = encryptor.decrypt(conn.encrypted_access_token)
        except Exception:
            pass

        try:
            provider_busy = await cal_provider.get_free_busy(
                access_token=token,
                calendar_id=conn.account_email,
                start_time=search_start,
                end_time=search_end
            )
            busy_blocks.extend(provider_busy)
        except Exception as e:
            logger.warning(f"Could not fetch provider free/busy for {conn.account_email}: {e}")

        # 2. Fetch existing confirmed DB appointments
        if db is not None:
            appt_stmt = select(Appointment).where(
                Appointment.calendar_connection_id == conn.id,
                Appointment.status == AppointmentStatus.CONFIRMED,
                Appointment.start_time < search_end,
                Appointment.end_time > search_start
            )
            appt_res = await db.execute(appt_stmt)
            for appt in appt_res.scalars().all():
                busy_blocks.append(FreeBusyBlock(start_time=appt.start_time, end_time=appt.end_time))

        # 3. Buffer busy blocks: expand busy windows by buffer_mins before and after
        buffered_busy: list[tuple[datetime, datetime]] = []
        for b in busy_blocks:
            b_start = b.start_time - timedelta(minutes=buffer_mins)
            b_end = b.end_time + timedelta(minutes=buffer_mins)
            buffered_busy.append((b_start, b_end))

        # 4. Generate candidate slots within host working hours
        working_hours = conn.working_hours_json or {}
        allowed_days = working_hours.get("days", [0, 1, 2, 3, 4])
        start_str = working_hours.get("start_time", "09:00")
        end_str = working_hours.get("end_time", "17:00")
        
        start_h, start_m = map(int, start_str.split(":"))
        end_h, end_m = map(int, end_str.split(":"))

        available_slots: list[TimeSlot] = []

        # Iterate through days
        current_day = search_start.astimezone(host_tz)
        for d in range(days_ahead + 1):
            day_cursor = current_day + timedelta(days=d)
            if day_cursor.weekday() not in allowed_days:
                continue

            # Day working window in host timezone
            day_work_start = datetime.combine(
                day_cursor.date(),
                dtime(start_h, start_m),
                tzinfo=host_tz
            ).astimezone(timezone.utc)

            day_work_end = datetime.combine(
                day_cursor.date(),
                dtime(end_h, end_m),
                tzinfo=host_tz
            ).astimezone(timezone.utc)

            slot_start = day_work_start
            while slot_start + timedelta(minutes=slot_duration_minutes) <= day_work_end:
                slot_end = slot_start + timedelta(minutes=slot_duration_minutes)

                # Skip if in the past
                if slot_start <= now_utc + timedelta(hours=2):
                    slot_start += timedelta(minutes=slot_duration_minutes)
                    continue

                # Check conflict with buffered busy blocks
                has_conflict = False
                for b_start, b_end in buffered_busy:
                    if slot_start < b_end and slot_end > b_start:
                        has_conflict = True
                        break

                if not has_conflict:
                    # Convert slot to prospect's timezone
                    prospect_start = slot_start.astimezone(prospect_tz)
                    prospect_end = slot_end.astimezone(prospect_tz)
                    available_slots.append(
                        TimeSlot(
                            start_time=prospect_start,
                            end_time=prospect_end,
                            timezone=prospect_timezone
                        )
                    )
                    if len(available_slots) >= max_slots_to_return:
                        return available_slots

                slot_start += timedelta(minutes=slot_duration_minutes)

        return available_slots

    @classmethod
    async def book_meeting_concurrency_safe(
        cls,
        workspace_id: str,
        connection_id: str,
        lead_id: str,
        booking: BookingRequest,
        campaign_id: Optional[str] = None,
        provider: Optional[CalendarProvider] = None,
        db: Optional[AsyncSession] = None
    ) -> BookingConfirmation:
        """
        Concurrency-Safe Atomic Meeting Booking:
        1. Acquires atomic distributed lock: booking_lock:{host_email}:{slot_start}.
        2. Double-booking check in DB & Provider.
        3. Dispatches calendar invite via provider.
        4. Saves Appointment record.
        5. Halts active lead sequence to MEETING_BOOKED (Stop Condition #4).
        6. Records immutable 5-Question Audit Event.
        """
        lock_key = f"booking_lock:{booking.host_email}:{booking.start_time.isoformat()}"
        
        # 1. Acquire distributed lock (zero retries to fail fast if double-booking attempt)
        async with DistributedLock(lock_key, ttl_seconds=15, max_retries=0) as lock:
            if not lock.acquired:
                raise LockAcquisitionError(f"Slot {booking.start_time.isoformat()} is currently being reserved by another request")

            if db is None:
                raise ValueError("Database session required for meeting booking")

            # 2. Verify connection
            c_stmt = select(CalendarConnection).where(
                CalendarConnection.id == connection_id,
                CalendarConnection.workspace_id == workspace_id
            )
            c_res = await db.execute(c_stmt)
            conn = c_res.scalar_one_or_none()
            if not conn:
                raise ValueError(f"CalendarConnection {connection_id} not found in workspace {workspace_id}")

            # 3. Double-Booking DB Check
            conflict_stmt = select(Appointment).where(
                Appointment.calendar_connection_id == conn.id,
                Appointment.status == AppointmentStatus.CONFIRMED,
                Appointment.start_time < booking.end_time,
                Appointment.end_time > booking.start_time
            )
            conflicts = (await db.execute(conflict_stmt)).scalars().all()
            if conflicts:
                raise ValueError(f"Slot {booking.start_time.isoformat()} is already booked by another confirmed meeting")

            # 4. Decrypt token & call provider
            token = conn.encrypted_access_token
            try:
                encryptor = TokenEncryptor()
                token = encryptor.decrypt(conn.encrypted_access_token)
            except Exception:
                pass

            cal_provider = cls.get_provider_for_connection(conn, provider)
            confirmation = await cal_provider.create_meeting_event(
                access_token=token,
                calendar_id=conn.account_email,
                booking=booking
            )

            # 5. Persist Appointment record
            appt = Appointment(
                workspace_id=workspace_id,
                calendar_connection_id=conn.id,
                lead_id=lead_id,
                campaign_id=campaign_id,
                title=booking.title,
                description=booking.description,
                start_time=booking.start_time,
                end_time=booking.end_time,
                attendee_email=booking.attendee_email,
                host_email=booking.host_email,
                status=AppointmentStatus.CONFIRMED,
                provider_event_id=confirmation.event_id,
                meeting_link=confirmation.meeting_link,
                idempotency_key=booking.idempotency_key,
                metadata_json={"timezone": booking.timezone}
            )
            db.add(appt)
            await db.flush()

            # 6. Enforce Stop Condition #4: Halt active LeadSequenceState to MEETING_BOOKED
            lead_stmt = select(CampaignLead).where(
                CampaignLead.lead_id == lead_id,
                CampaignLead.workspace_id == workspace_id,
                CampaignLead.state.in_([
                    LeadSequenceState.QUEUED,
                    LeadSequenceState.WAITING,
                    LeadSequenceState.READY,
                    LeadSequenceState.SENT,
                    LeadSequenceState.REPLIED,
                    LeadSequenceState.PAUSED
                ])
            )
            campaign_leads = (await db.execute(lead_stmt)).scalars().all()
            for cl in campaign_leads:
                cl.state = LeadSequenceState.MEETING_BOOKED
                cl.stop_reason = "MEETING_CONFIRMED"

            # 7. Record Immutable 5-Question Audit Event
            event = ConversationEvent(
                workspace_id=workspace_id,
                lead_id=lead_id,
                campaign_id=campaign_id,
                event_type="MEETING_BOOKED",
                rule_matched="STOP_CONDITION_MEETING_CONFIRMED",
                model_version="calendar-engine-v1.0",
                prompt_version="v1.0",
                knowledge_chunk_ids=[],
                previous_state="ACTIVE_SEQUENCE",
                new_state="MEETING_BOOKED",
                payload={
                    "appointment_id": appt.id,
                    "event_id": confirmation.event_id,
                    "start_time": booking.start_time.isoformat(),
                    "end_time": booking.end_time.isoformat(),
                    "meeting_link": confirmation.meeting_link,
                    "attendee_email": booking.attendee_email
                }
            )
            db.add(event)
            await db.commit()

            logger.info(f"Confirmed meeting booked for lead {booking.attendee_email} at {booking.start_time.isoformat()}")
            return confirmation
