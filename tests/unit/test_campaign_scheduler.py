import zoneinfo
from datetime import datetime, timezone
import pytest
from packages.campaign.scheduler import CampaignScheduler

def test_campaign_scheduler_business_hours_and_jitter():
    # Thursday 10:00 AM UTC
    base_thursday = datetime(2026, 9, 10, 10, 0, 0, tzinfo=timezone.utc)
    
    # Delay 1 day in UTC with fixed 15-minute jitter
    next_send = CampaignScheduler.calculate_next_send_time(
        lead_timezone="UTC",
        delay_days=1,
        delay_hours=0,
        start_hour=9,
        base_time=base_thursday,
        jitter_minutes=15
    )

    # Should land on Friday (2026-09-11) at 09:15 UTC
    assert next_send.weekday() == 4  # Friday
    assert next_send.hour == 9
    assert next_send.minute == 15

def test_campaign_scheduler_weekend_skipping():
    # Friday 2:00 PM UTC
    base_friday = datetime(2026, 9, 11, 14, 0, 0, tzinfo=timezone.utc)

    # Delay 1 business day -> Must skip Saturday (Sep 12) and Sunday (Sep 13) and land on Monday (Sep 14)
    next_send = CampaignScheduler.calculate_next_send_time(
        lead_timezone="UTC",
        delay_days=1,
        delay_hours=0,
        start_hour=9,
        base_time=base_friday,
        jitter_minutes=20
    )

    assert next_send.weekday() == 0  # Monday
    assert next_send.day == 14
    assert next_send.month == 9
    assert next_send.hour == 9
    assert next_send.minute == 20

def test_campaign_scheduler_lead_timezone_conversion():
    # UTC Tuesday 12:00 PM -> America/New_York is 08:00 AM (EDT is UTC-4)
    base_tuesday = datetime(2026, 9, 8, 12, 0, 0, tzinfo=timezone.utc)

    next_send_utc = CampaignScheduler.calculate_next_send_time(
        lead_timezone="America/New_York",
        delay_days=1,
        delay_hours=0,
        start_hour=9,
        base_time=base_tuesday,
        jitter_minutes=30
    )

    # In America/New_York, it should be Wednesday Sep 9 at 9:30 AM EDT
    ny_tz = zoneinfo.ZoneInfo("America/New_York")
    next_send_ny = next_send_utc.astimezone(ny_tz)

    assert next_send_ny.weekday() == 2  # Wednesday
    assert next_send_ny.day == 9
    assert next_send_ny.hour == 9
    assert next_send_ny.minute == 30

    # In UTC, 9:30 AM EDT is 13:30 UTC
    assert next_send_utc.hour == 13
    assert next_send_utc.minute == 30

def test_campaign_scheduler_jitter_bounds():
    base_time = datetime(2026, 9, 8, 10, 0, 0, tzinfo=timezone.utc)
    for _ in range(10):
        next_send = CampaignScheduler.calculate_next_send_time(
            lead_timezone="UTC",
            delay_days=1,
            base_time=base_time
        )
        assert 5 <= next_send.minute <= 45
