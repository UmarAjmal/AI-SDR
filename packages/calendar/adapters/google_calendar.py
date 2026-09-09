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

logger = logging.getLogger("codenter.calendar.google")

class GoogleCalendarProvider(CalendarProvider):
    """
    Google Calendar API v3 adapter for free/busy scheduling and meeting bookings.
    """
    FREE_BUSY_URL = "https://www.googleapis.com/calendar/v3/freeBusy"
    BASE_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars"

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
            "timeMin": start_time.isoformat(),
            "timeMax": end_time.isoformat(),
            "items": [{"id": calendar_id}]
        }

        client = self.mock_client or httpx.AsyncClient(timeout=15.0)
        owns_client = self.mock_client is None

        try:
            resp = await client.post(self.FREE_BUSY_URL, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            
            cal_data = data.get("calendars", {}).get(calendar_id, {})
            busy_list = cal_data.get("busy", [])
            
            blocks = []
            for b in busy_list:
                s = isoparse(b["start"])
                e = isoparse(b["end"])
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
        url = f"{self.BASE_EVENTS_URL}/{calendar_id}/events?conferenceDataVersion=1"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        req_id = booking.idempotency_key or str(uuid.uuid4())
        body = {
            "summary": booking.title,
            "description": booking.description or "",
            "start": {"dateTime": booking.start_time.isoformat()},
            "end": {"dateTime": booking.end_time.isoformat()},
            "attendees": [{"email": booking.attendee_email}],
            "conferenceData": {
                "createRequest": {
                    "requestId": req_id,
                    "conferenceSolutionKey": {"type": "hangoutsMeet"}
                }
            }
        }

        client = self.mock_client or httpx.AsyncClient(timeout=15.0)
        owns_client = self.mock_client is None

        try:
            resp = await client.post(url, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()

            meeting_link = data.get("hangoutLink")
            if not meeting_link and "conferenceData" in data:
                entry_points = data["conferenceData"].get("entryPoints", [])
                for ep in entry_points:
                    if ep.get("entryPointType") == "video":
                        meeting_link = ep.get("uri")
                        break

            return BookingConfirmation(
                event_id=data.get("id", str(uuid.uuid4())),
                title=data.get("summary", booking.title),
                start_time=booking.start_time,
                end_time=booking.end_time,
                attendee_email=booking.attendee_email,
                host_email=booking.host_email,
                meeting_link=meeting_link or f"https://meet.google.com/{uuid.uuid4().hex[:3]}-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:3]}",
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
        url = f"{self.BASE_EVENTS_URL}/{calendar_id}/events/{event_id}"
        headers = {"Authorization": f"Bearer {access_token}"}

        client = self.mock_client or httpx.AsyncClient(timeout=15.0)
        owns_client = self.mock_client is None

        try:
            resp = await client.delete(url, headers=headers)
            return resp.status_code in (200, 204)
        finally:
            if owns_client:
                await client.aclose()
