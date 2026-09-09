from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field

class TimeSlot(BaseModel):
    start_time: datetime
    end_time: datetime
    timezone: str = "UTC"

class FreeBusyBlock(BaseModel):
    start_time: datetime
    end_time: datetime

class BookingRequest(BaseModel):
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    attendee_email: str
    host_email: str
    timezone: str = "UTC"
    idempotency_key: Optional[str] = None

class BookingConfirmation(BaseModel):
    event_id: str
    title: str
    start_time: datetime
    end_time: datetime
    attendee_email: str
    host_email: str
    meeting_link: Optional[str] = None
    status: str = "CONFIRMED"

class CalendarProvider(ABC):
    """
    Abstract Base Class for Calendar Providers (Google Calendar, Microsoft Outlook Calendar).
    """

    @abstractmethod
    async def get_free_busy(
        self,
        access_token: str,
        calendar_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> list[FreeBusyBlock]:
        """
        Queries host free/busy schedule between start_time and end_time.
        """
        pass

    @abstractmethod
    async def create_meeting_event(
        self,
        access_token: str,
        calendar_id: str,
        booking: BookingRequest
    ) -> BookingConfirmation:
        """
        Creates a confirmed calendar event with video conference details.
        """
        pass

    @abstractmethod
    async def cancel_meeting_event(
        self,
        access_token: str,
        calendar_id: str,
        event_id: str
    ) -> bool:
        """
        Cancels an existing calendar event.
        """
        pass
