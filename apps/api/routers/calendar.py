from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.api.core.database import get_db
from apps.api.core.dependencies import get_current_workspace_context, require_role, WorkspaceContext
from packages.common.models.workspace import WorkspaceRole
from packages.common.models.calendar import CalendarConnection, Appointment, CalendarProviderType, AppointmentStatus
from packages.common.encryption import TokenEncryptor
from packages.calendar.base import TimeSlot, BookingRequest, BookingConfirmation
from packages.calendar.availability import AvailabilityEngine

router = APIRouter(prefix="/calendar", tags=["Calendar & Autonomous Meeting Booking"])

class CalendarConnectionCreateRequest(BaseModel):
    provider: CalendarProviderType
    account_email: str
    access_token: str
    refresh_token: str
    expires_in_seconds: int = 3600
    working_hours_start: str = "09:00"
    working_hours_end: str = "17:00"
    working_days: List[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4])
    buffer_minutes: int = 15
    timezone: str = "UTC"

class CalendarConnectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    provider: CalendarProviderType
    account_email: str
    sync_status: str
    working_hours: dict
    buffer_minutes: int
    timezone: str
    created_at: datetime

class BookMeetingApiRequest(BaseModel):
    connection_id: str
    lead_id: str
    campaign_id: Optional[str] = None
    title: str = "Intro Discovery Meeting"
    description: Optional[str] = "Discussion of autonomous SDR capabilities"
    start_time: datetime
    end_time: datetime
    attendee_email: str
    host_email: str
    prospect_timezone: str = "UTC"

class AppointmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    calendar_connection_id: Optional[str]
    lead_id: Optional[str]
    campaign_id: Optional[str]
    title: str
    description: Optional[str]
    start_time: datetime
    end_time: datetime
    attendee_email: str
    host_email: str
    status: AppointmentStatus
    provider_event_id: Optional[str]
    meeting_link: Optional[str]
    created_at: datetime

@router.get("/connections", response_model=List[CalendarConnectionResponse])
async def list_calendar_connections(
    ctx: WorkspaceContext = Depends(get_current_workspace_context),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(CalendarConnection).where(CalendarConnection.workspace_id == ctx.workspace_id)
    res = await db.execute(stmt)
    conns = res.scalars().all()
    
    return [
        CalendarConnectionResponse(
            id=c.id,
            workspace_id=c.workspace_id,
            provider=c.provider,
            account_email=c.account_email,
            sync_status=c.sync_status,
            working_hours=c.working_hours_json,
            buffer_minutes=c.buffer_minutes,
            timezone=c.timezone,
            created_at=c.created_at
        )
        for c in conns
    ]

@router.post("/connections", response_model=CalendarConnectionResponse, status_code=status.HTTP_201_CREATED)
async def connect_calendar(
    payload: CalendarConnectionCreateRequest,
    ctx: WorkspaceContext = Depends(require_role([WorkspaceRole.OWNER, WorkspaceRole.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    encryptor = TokenEncryptor()
    enc_access = encryptor.encrypt(payload.access_token)
    enc_refresh = encryptor.encrypt(payload.refresh_token)
    expires_at = datetime.now(timezone.utc)

    conn = CalendarConnection(
        workspace_id=ctx.workspace_id,
        provider=payload.provider,
        account_email=payload.account_email,
        encrypted_access_token=enc_access,
        encrypted_refresh_token=enc_refresh,
        token_expires_at=expires_at,
        sync_status="CONNECTED",
        working_hours_json={
            "start_time": payload.working_hours_start,
            "end_time": payload.working_hours_end,
            "days": payload.working_days
        },
        buffer_minutes=payload.buffer_minutes,
        timezone=payload.timezone
    )
    db.add(conn)
    await db.commit()
    await db.refresh(conn)

    return CalendarConnectionResponse(
        id=conn.id,
        workspace_id=conn.workspace_id,
        provider=conn.provider,
        account_email=conn.account_email,
        sync_status=conn.sync_status,
        working_hours=conn.working_hours_json,
        buffer_minutes=conn.buffer_minutes,
        timezone=conn.timezone,
        created_at=conn.created_at
    )

@router.get("/slots", response_model=List[TimeSlot])
async def get_available_slots(
    connection_id: Optional[str] = Query(None),
    prospect_timezone: str = Query("UTC"),
    days_ahead: int = Query(5, ge=1, le=14),
    ctx: WorkspaceContext = Depends(get_current_workspace_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns 2-3 free slots in prospect timezone with 15-minute buffers and working hours enforcement.
    """
    if connection_id:
        c_stmt = select(CalendarConnection).where(
            CalendarConnection.id == connection_id,
            CalendarConnection.workspace_id == ctx.workspace_id
        )
        conn = (await db.execute(c_stmt)).scalar_one_or_none()
    else:
        c_stmt = select(CalendarConnection).where(
            CalendarConnection.workspace_id == ctx.workspace_id,
            CalendarConnection.sync_status == "CONNECTED"
        )
        conn = (await db.execute(c_stmt)).scalars().first()

    if not conn:
        raise HTTPException(status_code=404, detail="No active calendar connection found")

    slots = await AvailabilityEngine.find_available_slots(
        conn=conn,
        prospect_timezone=prospect_timezone,
        days_ahead=days_ahead,
        db=db
    )
    return slots

@router.post("/book", response_model=BookingConfirmation)
async def book_meeting_slot(
    payload: BookMeetingApiRequest,
    ctx: WorkspaceContext = Depends(require_role([WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.MEMBER])),
    db: AsyncSession = Depends(get_db)
):
    """
    Concurrency-safe atomic meeting confirmation:
    Acquires distributed lock, prevents double booking, dispatches provider invite, and halts lead sequence.
    """
    booking_req = BookingRequest(
        title=payload.title,
        description=payload.description,
        start_time=payload.start_time,
        end_time=payload.end_time,
        attendee_email=payload.attendee_email,
        host_email=payload.host_email,
        timezone=payload.prospect_timezone
    )

    try:
        confirmation = await AvailabilityEngine.book_meeting_concurrency_safe(
            workspace_id=ctx.workspace_id,
            connection_id=payload.connection_id,
            lead_id=payload.lead_id,
            booking=booking_req,
            campaign_id=payload.campaign_id,
            db=db
        )
        return confirmation
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/appointments", response_model=List[AppointmentResponse])
async def list_appointments(
    ctx: WorkspaceContext = Depends(get_current_workspace_context),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Appointment).where(
        Appointment.workspace_id == ctx.workspace_id
    ).order_by(Appointment.start_time.desc())
    res = await db.execute(stmt)
    return res.scalars().all()
