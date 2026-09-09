import random
import zoneinfo
from datetime import datetime, timezone, timedelta

class CampaignScheduler:
    @classmethod
    def calculate_next_send_time(
        cls,
        lead_timezone: str | None = None,
        delay_days: int = 1,
        delay_hours: int = 0,
        start_hour: int = 9,
        end_hour: int = 17,
        base_time: datetime | None = None,
        jitter_minutes: int | None = None
    ) -> datetime:
        """
        Calculates the next scheduled send timestamp in UTC:
        1. Translates into the prospect's local timezone.
        2. Adds delay_days strictly skipping weekends (Saturday and Sunday).
        3. Enforces the business-hours window (9 AM - 5 PM).
        4. Applies anti-spam randomized jitter (5-45 minutes).
        5. Converts back to UTC.
        """
        # Resolve timezone safely
        try:
            tz = zoneinfo.ZoneInfo(lead_timezone) if lead_timezone else zoneinfo.ZoneInfo("UTC")
        except Exception:
            tz = zoneinfo.ZoneInfo("UTC")

        now_utc = base_time or datetime.now(timezone.utc)
        local_time = now_utc.astimezone(tz)

        # 1. Advance business days
        days_added = 0
        current_date = local_time.date()

        while days_added < delay_days:
            current_date += timedelta(days=1)
            # Monday=0, Sunday=6. Skip Saturday (5) and Sunday (6)
            if current_date.weekday() < 5:
                days_added += 1

        # If current_date falls on weekend (e.g. delay_days=0 on a Saturday), advance to Monday
        while current_date.weekday() >= 5:
            current_date += timedelta(days=1)

        # 2. Compute randomized jitter (5 to 45 minutes)
        if jitter_minutes is None:
            jitter = random.randint(5, 45)
        else:
            jitter = jitter_minutes

        target_hour = start_hour + delay_hours
        if target_hour >= end_hour:
            # Shift to next business day at start_hour
            current_date += timedelta(days=1)
            while current_date.weekday() >= 5:
                current_date += timedelta(days=1)
            target_hour = start_hour

        scheduled_local = datetime(
            year=current_date.year,
            month=current_date.month,
            day=current_date.day,
            hour=target_hour,
            minute=jitter,
            second=0,
            tzinfo=tz
        )

        # If the scheduled time is already in the past relative to now, advance to next business day
        if scheduled_local <= local_time:
            next_date = current_date + timedelta(days=1)
            while next_date.weekday() >= 5:
                next_date += timedelta(days=1)
            scheduled_local = datetime(
                year=next_date.year,
                month=next_date.month,
                day=next_date.day,
                hour=start_hour,
                minute=jitter,
                second=0,
                tzinfo=tz
            )

        # Convert back to UTC
        return scheduled_local.astimezone(timezone.utc)
