"""Safety Filter role.

Screens a parsed scenario for *urgent* cases before (or alongside) the regular
guidance flow — situations where the user should be nudged toward emergency
contraception or a pharmacist / doctor promptly, rather than just routine
missed-pill advice.

This is deliberately deterministic and conservative: the same scenario always
produces the same flags, so the screen is auditable and reproducible. It does
not replace medical judgement — it surfaces red flags.
"""

from __future__ import annotations

from models import ParsedScenario, SafetyFilterResult

# A pill this many hours late (or later) is effectively a missed pill.
MISSED_THRESHOLD_HOURS = 24
# At/after this lateness we treat the lapse as urgent on its own.
VERY_LATE_HOURS = 72

URGENT_MESSAGE = (
    "Based on what you described, this may need prompt attention. Consider "
    "emergency contraception and speak to a pharmacist or doctor as soon as you "
    "can — ideally today."
)
CLEAR_MESSAGE = (
    "Nothing here looks urgent. Continue with the standard guidance for your "
    "situation."
)


def _effective_missed(scenario: ParsedScenario) -> int:
    """Missed-pill count, treating a >=24h-late pill as one missed pill."""
    missed = scenario.pillsMissed or 0
    if missed == 0 and scenario.hoursLate is not None:
        if scenario.hoursLate >= MISSED_THRESHOLD_HOURS:
            missed = 1
    return missed


def screen(scenario: ParsedScenario) -> SafetyFilterResult:
    """Screen a scenario for urgent red flags.

    Args:
        scenario: The (possibly incomplete) parsed scenario.

    Returns:
        A `SafetyFilterResult` with `urgent`, the list of `triggers`, and a
        user-facing `message`.
    """
    triggers: list[str] = []
    missed = _effective_missed(scenario)

    if missed >= 2 and scenario.cycleWeek == 1:
        triggers.append(
            "Two or more pills missed during week 1 — the highest-risk point in "
            "the pack; emergency contraception may be needed."
        )

    if missed >= 3:
        triggers.append("Three or more active pills missed.")

    if scenario.hoursLate is not None and scenario.hoursLate >= VERY_LATE_HOURS:
        triggers.append(
            f"A pill was taken {scenario.hoursLate} hours late "
            f"(>= {VERY_LATE_HOURS}h)."
        )

    urgent = bool(triggers)
    return SafetyFilterResult(
        urgent=urgent,
        triggers=triggers,
        message=URGENT_MESSAGE if urgent else CLEAR_MESSAGE,
    )


def check(scenario: ParsedScenario) -> tuple[bool, str | None]:
    """Backwards-compatible helper: ``(is_safe, reason)``.

    ``is_safe`` is False for urgent scenarios, with the urgent message as the
    reason. Prefer :func:`screen` for the full structured result.
    """
    result = screen(scenario)
    return (not result.urgent, result.message if result.urgent else None)
