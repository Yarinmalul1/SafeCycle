"""SafeCycle guidance engine.

Deterministic, rule-based contraception guidance. The engine takes a validated
`PillScenario` and returns a `GuidanceResult`. No LLM calls happen here — the
decision must be reproducible and auditable.

Currently implemented: Yasmin (a combined oral contraceptive) missed-pill rules
for weeks 1-3 of the pack. The rules follow standard combined-pill guidance:

  * A pill <24h late is "late", not "missed": take it now, no extra action.
  * One missed pill (>=24h late), any week: take the most recent missed pill now,
    no backup needed.
  * Two or more missed pills — action depends on the week:
      - Week 1: take the most recent missed pill, use backup for 7 days, and
        consider emergency contraception if there was unprotected sex.
      - Week 2: take the most recent missed pill, use backup for 7 days.
        Emergency contraception generally not needed if the prior 7 days were
        taken correctly.
      - Week 3: take the most recent missed pill, use backup for 7 days, and
        skip the placebo/pill-free break — start the next pack immediately.
"""

from __future__ import annotations

from ai.product_catalog import PillType, normalize, pill_type, pop_window_hours
from models import GuidanceResult, PillScenario, RiskLevel

# A combined pill is only considered "missed" once it is this many hours late.
MISSED_THRESHOLD_HOURS = 24
# Standard backup duration after missed combined pills.
BACKUP_DAYS = 7
# Backup duration after a missed progestogen-only pill (shorter — POPs become
# reliable again faster).
POP_BACKUP_DAYS = 2
# A vaginal ring left out (or overdue) beyond this many hours loses protection.
RING_OUT_THRESHOLD_HOURS = 48


def evaluate(scenario: PillScenario) -> GuidanceResult:
    """Evaluate a scenario and return structured guidance.

    Dispatches by product family. Today only combined pills (e.g. Yasmin) have
    rules; anything else returns a conservative "talk to a professional" result.
    """
    ptype = pill_type(scenario.product)
    if ptype is PillType.COMBINED:
        return _evaluate_combined(scenario)
    if ptype is PillType.PROGESTOGEN_ONLY:
        return _evaluate_pop(scenario, pop_window_hours(scenario.product))
    if ptype is PillType.EXTENDED_CYCLE:
        return _evaluate_extended(scenario)
    if ptype is PillType.RING:
        return _evaluate_ring(scenario)

    return GuidanceResult(
        riskLevel=RiskLevel.MODERATE,
        takePillNow=True,
        summary=(
            f"Guidance for '{normalize(scenario.product)}' isn't available yet. "
            "Please check the product leaflet or speak to a pharmacist."
        ),
        notes=["Unsupported product — no rule set implemented."],
    )


def _missed_count(scenario: PillScenario) -> int:
    """Effective number of missed pills, accounting for hoursLate.

    `pillsMissed` is authoritative when provided. If it is 0 but the most recent
    pill is >=24h late, that late pill counts as one missed pill.
    """
    missed = scenario.pillsMissed
    if missed == 0 and scenario.hoursLate is not None:
        if scenario.hoursLate >= MISSED_THRESHOLD_HOURS:
            missed = 1
    return missed


def _evaluate_pop(scenario: PillScenario, window_hours: int) -> GuidanceResult:
    """Missed/late-pill rules for progestogen-only pills (POPs).

    POPs have no pack weeks and a much tighter timing window than combined
    pills: a pill is "missed" once it is more than ``window_hours`` late (3h for
    most POPs, 12h for desogestrel pills like Cerazette).
    """
    missed = scenario.pillsMissed
    if missed == 0 and scenario.hoursLate is not None and scenario.hoursLate > window_hours:
        missed = 1

    if missed == 0:
        if scenario.hoursLate is not None and scenario.hoursLate > 0:
            return GuidanceResult(
                riskLevel=RiskLevel.NONE,
                takePillNow=True,
                summary=(
                    f"You're within the {window_hours}-hour window for this "
                    "progestogen-only pill. Take it now and your next one at the "
                    "usual time — you're still protected."
                ),
            )
        return GuidanceResult(
            riskLevel=RiskLevel.NONE,
            takePillNow=False,
            summary="No pills missed — you're protected. Carry on as usual.",
        )

    # The pill was taken too late (or skipped): protection may have dropped.
    return GuidanceResult(
        riskLevel=RiskLevel.HIGH if scenario.unprotectedSex else RiskLevel.MODERATE,
        takePillNow=True,
        useBackup=True,
        backupDays=POP_BACKUP_DAYS,
        considerEmergencyContraception=scenario.unprotectedSex,
        summary=(
            "This progestogen-only pill was more than "
            f"{window_hours} hours late, so take the most recent pill now and "
            f"use backup contraception for the next {POP_BACKUP_DAYS} days. "
            "Consider emergency contraception if you had unprotected sex in the "
            "last few days."
        ),
        notes=[f"Progestogen-only pills must be taken within {window_hours} hours."],
    )


def _evaluate_extended(scenario: PillScenario) -> GuidanceResult:
    """Missed-pill rules for extended-cycle combined pills (e.g. Seasonique).

    These are combined pills taken continuously for a long active phase (~84
    days) with infrequent breaks, so there is no weekly placebo logic — the user
    is almost always mid-active-phase. Missed-pill handling mirrors the combined
    pill: one missed pill is low risk; two or more need backup.
    """
    missed = _missed_count(scenario)

    if missed == 0:
        if scenario.hoursLate is not None and scenario.hoursLate > 0:
            return GuidanceResult(
                riskLevel=RiskLevel.NONE,
                takePillNow=True,
                summary=(
                    "You're less than 24 hours late. Take this pill now and your "
                    "next one at the usual time — you're still protected."
                ),
            )
        return GuidanceResult(
            riskLevel=RiskLevel.NONE,
            takePillNow=False,
            summary="No pills missed — you're protected. Carry on as usual.",
        )

    if missed == 1:
        return GuidanceResult(
            riskLevel=RiskLevel.LOW,
            takePillNow=True,
            summary=(
                "One missed pill: take the most recent missed pill now (even if "
                "that means two in one day) and continue the pack as normal. No "
                "extra protection is needed."
            ),
        )

    # Two or more missed active pills.
    return GuidanceResult(
        riskLevel=RiskLevel.HIGH if scenario.unprotectedSex else RiskLevel.MODERATE,
        takePillNow=True,
        useBackup=True,
        backupDays=BACKUP_DAYS,
        considerEmergencyContraception=scenario.unprotectedSex,
        summary=(
            "Two or more pills missed: take the most recent missed pill now and "
            "use backup contraception for the next 7 days. Keep taking one active "
            "pill a day — with an extended-cycle pill you usually won't have a "
            "break for several more weeks. Consider emergency contraception if you "
            "had unprotected sex in the last few days."
        ),
        notes=[
            "Extended-cycle pills are taken continuously (~84 active days) before "
            "a scheduled break."
        ],
    )


def _evaluate_ring(scenario: PillScenario) -> GuidanceResult:
    """Rules for the vaginal ring (e.g. NuvaRing).

    For the ring, ``hoursLate`` is how long it has been out of place or overdue.
    Out for under 48 hours: reinsert and protection continues. Out for 48 hours
    or more: reinsert, use backup for 7 days, and consider emergency
    contraception if there was unprotected sex.
    """
    hours_out = scenario.hoursLate or 0

    if hours_out < RING_OUT_THRESHOLD_HOURS:
        return GuidanceResult(
            riskLevel=RiskLevel.NONE,
            takePillNow=True,
            summary=(
                "Your ring has been out for less than 48 hours. Reinsert it now "
                "(or insert a new one) — you're still protected."
            ),
            notes=["Here, 'take now' means reinsert your ring."],
        )

    return GuidanceResult(
        riskLevel=RiskLevel.HIGH if scenario.unprotectedSex else RiskLevel.MODERATE,
        takePillNow=True,
        useBackup=True,
        backupDays=BACKUP_DAYS,
        considerEmergencyContraception=scenario.unprotectedSex,
        summary=(
            "Your ring has been out for 48 hours or more, so protection may have "
            "dropped. Reinsert a ring now and use backup contraception for the "
            "next 7 days. Consider emergency contraception if you had unprotected "
            "sex in the last few days."
        ),
        notes=["Here, 'take now' means reinsert your ring."],
    )


def _evaluate_combined(scenario: PillScenario) -> GuidanceResult:
    """Missed-pill rules for combined oral contraceptives (Yasmin)."""
    missed = _missed_count(scenario)

    # Nothing missed: either fully on time, or just late (<24h).
    if missed == 0:
        if scenario.hoursLate is not None and scenario.hoursLate > 0:
            return GuidanceResult(
                riskLevel=RiskLevel.NONE,
                takePillNow=True,
                summary=(
                    "You're less than 24 hours late. Take this pill now and your "
                    "next one at the usual time — you're still protected."
                ),
            )
        return GuidanceResult(
            riskLevel=RiskLevel.NONE,
            takePillNow=False,
            summary="No pills missed — you're protected. Carry on as usual.",
        )

    # Exactly one missed pill (any week): take it now, no backup needed.
    if missed == 1:
        return GuidanceResult(
            riskLevel=RiskLevel.LOW,
            takePillNow=True,
            summary=(
                "One missed pill: take the most recent missed pill now (even if "
                "that means two in one day) and continue the pack as normal. No "
                "extra protection is needed."
            ),
        )

    # Two or more missed pills: action depends on the week.
    if scenario.cycleWeek == 1:
        return GuidanceResult(
            riskLevel=RiskLevel.HIGH if scenario.unprotectedSex else RiskLevel.MODERATE,
            takePillNow=True,
            useBackup=True,
            backupDays=BACKUP_DAYS,
            considerEmergencyContraception=scenario.unprotectedSex,
            summary=(
                "Two or more pills missed in week 1: take the most recent missed "
                "pill now and use backup contraception for the next 7 days. "
                "Because this is week 1, consider emergency contraception if you "
                "had unprotected sex in the last few days."
            ),
            notes=["Week 1 missed pills carry the highest pregnancy risk."],
        )

    if scenario.cycleWeek == 2:
        return GuidanceResult(
            riskLevel=RiskLevel.MODERATE,
            takePillNow=True,
            useBackup=True,
            backupDays=BACKUP_DAYS,
            considerEmergencyContraception=False,
            summary=(
                "Two or more pills missed in week 2: take the most recent missed "
                "pill now and use backup contraception for the next 7 days. If you "
                "took the previous 7 days correctly, emergency contraception is "
                "generally not needed."
            ),
        )

    if scenario.cycleWeek == 3:
        return GuidanceResult(
            riskLevel=RiskLevel.MODERATE,
            takePillNow=True,
            useBackup=True,
            backupDays=BACKUP_DAYS,
            skipPlaceboBreak=True,
            summary=(
                "Two or more pills missed in week 3: take the most recent missed "
                "pill now, use backup for 7 days, and skip the pill-free / placebo "
                "break — start your next pack immediately after this one."
            ),
            notes=["Skipping the break maintains protection into the next pack."],
        )

    # cycleWeek == 4 (placebo week): missing inactive pills doesn't reduce cover.
    return GuidanceResult(
        riskLevel=RiskLevel.NONE,
        takePillNow=False,
        summary=(
            "These are inactive (placebo) pills, so missing them doesn't affect "
            "your protection. Start your next pack on the usual day."
        ),
    )
