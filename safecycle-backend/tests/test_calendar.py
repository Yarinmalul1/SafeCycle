"""Unit tests for the schedule generator (Phase 3).

Pure-logic tests: no Supabase, no Google API, no FastAPI client. They cover
the spec's three method families and the dispatch fallback.
"""

from __future__ import annotations

from datetime import date, timedelta

from logic.calendar import (
    DEFAULT_DAYS_AHEAD,
    PATCH_INTERVAL_DAYS,
    RING_CYCLE_DAYS,
    RING_IN_DAYS,
    generate,
    generate_patch_schedule,
    generate_pill_schedule,
    generate_ring_schedule,
)

START = date(2026, 1, 1)


def test_pill_schedule_has_one_event_per_day():
    events = generate_pill_schedule(START, days_ahead=90, hour=9)
    assert len(events) == 90
    # First and last events sit at the right ends of the window.
    assert events[0].starts_at.date() == START
    assert events[-1].starts_at.date() == START + timedelta(days=89)
    # All at 9 AM UTC.
    assert all(e.starts_at.hour == 9 for e in events)


def test_pill_schedule_default_window_is_90_days():
    assert len(generate_pill_schedule(START)) == DEFAULT_DAYS_AHEAD


def test_pill_schedule_respects_custom_hour():
    events = generate_pill_schedule(START, days_ahead=3, hour=21)
    assert all(e.starts_at.hour == 21 for e in events)


def test_ring_schedule_alternates_21_in_7_out():
    events = generate_ring_schedule(START, days_ahead=90)
    inserts = [e for e in events if "Insert" in e.summary]
    removes = [e for e in events if "Remove" in e.summary]
    # 90-day window fits 4 inserts (days 0, 28, 56, 84) but only 3 removes
    # (day 105 would land outside the window).
    assert len(inserts) == 4
    assert len(removes) == 3
    # Each insert sits one full 28-day cycle apart.
    for prev, curr in zip(inserts, inserts[1:]):
        assert (curr.starts_at - prev.starts_at).days == RING_CYCLE_DAYS
    # Each remove follows its insert by 21 days.
    for ins, rem in zip(inserts, removes):
        assert (rem.starts_at - ins.starts_at).days == RING_IN_DAYS


def test_ring_schedule_omits_trailing_remove_outside_window():
    # A 21-day window only fits one insert and no remove (remove would be at day 21,
    # which is the exclusive end of the window).
    events = generate_ring_schedule(START, days_ahead=RING_IN_DAYS)
    assert len(events) == 1
    assert "Insert" in events[0].summary


def test_patch_schedule_is_weekly():
    events = generate_patch_schedule(START, days_ahead=90)
    # 90 // 7 == 12 full weeks, plus the start day -> 13 events.
    assert len(events) == 13
    for prev, curr in zip(events, events[1:]):
        assert (curr.starts_at - prev.starts_at).days == PATCH_INTERVAL_DAYS


def test_generate_dispatches_by_method_family():
    pill = generate("pill", START)
    ring = generate("ring", START)
    patch = generate("patch", START)
    # Each family produces a distinct event count for the same window.
    assert len({len(pill), len(ring), len(patch)}) == 3


def test_generate_unknown_method_defaults_to_pill_schedule():
    # Safest fallback for a contraception app: daily reminders.
    pill = generate("pill", START)
    unknown = generate("something-else", START)
    assert len(unknown) == len(pill)
    assert all("pill" in e.summary.lower() for e in unknown)
