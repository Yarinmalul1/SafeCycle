"""Schedule generation for SafeCycle calendar export (Phase 3).

Pure functions: given a contraceptive method family and a start date, return
the list of reminder events covering the next N days. Persistence lives in
db/calendars.py; export to Google Calendar / ICS lives at the API layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

# Default rolling window for any generated schedule (~3 months).
DEFAULT_DAYS_AHEAD = 90
# Default reminder time when the user doesn't override.
DEFAULT_HOUR = 9

# Ring cycle: 21 days in, then 7 days out (no ring), repeat.
RING_IN_DAYS = 21
RING_OUT_DAYS = 7
RING_CYCLE_DAYS = RING_IN_DAYS + RING_OUT_DAYS

# Patch: changed weekly on the same weekday.
PATCH_INTERVAL_DAYS = 7


@dataclass(frozen=True)
class CalendarEvent:
    """One reminder event in a generated schedule."""

    starts_at: datetime
    summary: str
    description: str

    def as_dict(self) -> dict:
        return {
            "starts_at": self.starts_at.isoformat(),
            "summary": self.summary,
            "description": self.description,
        }


def _at_hour(d: date, hour: int) -> datetime:
    """Combine a date with an hour-of-day at UTC."""
    return datetime.combine(d, time(hour=hour, tzinfo=timezone.utc))


def generate_pill_schedule(
    start: date,
    *,
    days_ahead: int = DEFAULT_DAYS_AHEAD,
    hour: int = DEFAULT_HOUR,
) -> list[CalendarEvent]:
    """One pill reminder per day at `hour` for `days_ahead` days."""
    return [
        CalendarEvent(
            starts_at=_at_hour(start + timedelta(days=i), hour),
            summary="Take pill",
            description="Daily contraceptive pill reminder.",
        )
        for i in range(days_ahead)
    ]


def generate_ring_schedule(
    start: date,
    *,
    days_ahead: int = DEFAULT_DAYS_AHEAD,
    hour: int = DEFAULT_HOUR,
) -> list[CalendarEvent]:
    """Insert event every 28 days; remove event 21 days after each insert."""
    events: list[CalendarEvent] = []
    end = start + timedelta(days=days_ahead)
    day = start
    while day < end:
        events.append(CalendarEvent(
            starts_at=_at_hour(day, hour),
            summary="Insert NuvaRing",
            description="Insert a new vaginal ring; leave in for 21 days.",
        ))
        remove_day = day + timedelta(days=RING_IN_DAYS)
        if remove_day < end:
            events.append(CalendarEvent(
                starts_at=_at_hour(remove_day, hour),
                summary="Remove NuvaRing",
                description="Remove the ring; 7-day ring-free week begins.",
            ))
        day += timedelta(days=RING_CYCLE_DAYS)
    return events


def generate_patch_schedule(
    start: date,
    *,
    days_ahead: int = DEFAULT_DAYS_AHEAD,
    hour: int = DEFAULT_HOUR,
) -> list[CalendarEvent]:
    """One patch-change reminder every 7 days from `start`."""
    events: list[CalendarEvent] = []
    end = start + timedelta(days=days_ahead)
    day = start
    while day < end:
        events.append(CalendarEvent(
            starts_at=_at_hour(day, hour),
            summary="Change patch",
            description="Weekly contraceptive patch change.",
        ))
        day += timedelta(days=PATCH_INTERVAL_DAYS)
    return events


def generate(
    method: str,
    start: date,
    *,
    days_ahead: int = DEFAULT_DAYS_AHEAD,
    hour: int = DEFAULT_HOUR,
) -> list[CalendarEvent]:
    """Dispatch by method family. Unknown methods default to a daily pill
    schedule, which is the safest fallback for a contraception app."""
    m = method.lower().strip()
    if m == "ring":
        return generate_ring_schedule(start, days_ahead=days_ahead, hour=hour)
    if m == "patch":
        return generate_patch_schedule(start, days_ahead=days_ahead, hour=hour)
    return generate_pill_schedule(start, days_ahead=days_ahead, hour=hour)
