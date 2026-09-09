import logging
import uuid
import httpx
from datetime import datetime, timezone
from typing import Optional
from dateutil.parser import isoparse

from packages.calendar.base import (
    CalendarProvider,
    FreeBusyBlock,
    BookingRequest,
    BookingConfirmation
)

logger = logging.getLogger("codenter.calendar.outlook")

class OutlookCalendarProvider(CalendarProvider):
    """
    Microsoft Graph API calendar adapter for free/busy scheduling and meeting bookings.
    """
    GET_SCHEDULE_URL = "https://graph.microsoft.com/v1.0/me/calendar/getSchedule"
    EVENTS_URL = "https://graph.microsoft.com/v1.0/me/events"

    def __init__(self, mock_client: Optional[httpx.AsyncClient] = None):
        self.mock_client = mock_client

    async def get_free_busy(
        self,
        access_token: str,
        calendar_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> list[FreeBusyBlock]:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        body = {
            "schedules": [calendar_id],
            "startTime": {"dateTime": start_time.isoformat(), "timeZone": "UTC"},
            "endTime": {"dateTime": end_time.isoformat(), "timeZone": "UTC"},
            "availabilityViewInterval": 15
        }

        client = self.mock_client or httpx.AsyncClient(timeout=15.0)
        owns_client = self.mock_client is None

        try:
            resp = await client.post(self.GET_SCHEDULE_URL, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()

            schedules = data.get("value", [])
            blocks = []
            for sched in schedules:
                items = sched.get("scheduleItems", [])
                for it in items:
                    status = (it.get("status") or "").lower()
                    if status != "free":
                        s = isoparse(it["start"]["dateTime"])
                        e = isoparse(it["end"]["dateTime"])
                        if s.tzinfo is None:
                            s = s.replace(tzinfo=timezone.utc)
                        if e.tzinfo is None:
                            e = e.replace(tzinfo=timezone.utc)
                        blocks.append(FreeBusyBlock(start_time=s, end_time=e))
            return blocks
        finally:
            if owns_client:
                await client.aclose()

    async def create_meeting_event(
        self,
        access_token: str,
        calendar_id: str,
        booking: BookingRequest
    ) -> BookingConfirmation:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        body = {
            "subject": booking.title,
            "body": {
                "contentType": "HTML",
                "content": booking.description or ""
            },
            "start": {
                "dateTime": booking.start_time.isoformat(),
                "timeZone": "UTC"
            },
            "end": {
                "dateTime": booking.end_time.isoformat(),
                "timeZone": "UTC"
            },
            "attendees": [
                {
                    "emailAddress": {"address": booking.attendee_email},
                    "type": "required"
                }
            ],
            "isOnlineMeeting": True,
            "onlineMeetingProvider": "teamsForBusiness"
        }

        client = self.mock_client or httpx.AsyncClient(timeout=15.0)
        owns_client = self.mock_client is None

        try:
            resp = await client.post(self.EVENTS_URL, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()

            meeting_link = data.get("onlineMeeting", {}).get("joinUrl") or data.get("webLink")

            return BookingConfirmation(
                event_id=data.get("id", str(uuid.uuid4())),
                title=data.get("subject", booking.title),
                start_time=booking.start_time,
                end_time=booking.end_time,
                attendee_email=booking.attendee_email,
                host_email=booking.host_email,
                meeting_link=meeting_link or f"https://teams.microsoft.com/l/meetup-join/{uuid.uuid4()}",
                status="CONFIRMED"
            )
        finally:
            if owns_client:
                await client.aclose()

    async def cancel_meeting_event(
        self,
        access_token: str,
        calendar_id: str,
        event_id: str
    ) -> bool:
        url = f"{self.EVENTS_URL}/{event_id}"
        headers = {"Authorization": f"Bearer {access_token}"}

        client = self.mock_client or httpx.AsyncClient(timeout=15.0)
        owns_client = self.mock_client is None

        try:
            resp = await client.delete(url, headers=headers)
            return resp.status_code in (200, 204)
        finally:
            if owns_client:
                await client.aclose()
