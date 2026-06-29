"""SafeCycle method-switching engine.

Deterministic, rule-based guidance for switching from one contraceptive method
to another. Like the missed-pill engine, this makes a reproducible, auditable
decision with no LLM calls, returning a `GuidanceResult`.

⚠️ SIMPLIFIED / NOT CLINICALLY REVIEWED. These rules follow the general shape of
standard switching guidance (continuous protection when switched seamlessly;
otherwise backup until the new method is reliably effective) but are deliberately
conservative placeholders for the demo — they must be clinician-reviewed before
real use.

Coverage grows commit by commit; see `SUPPORTED_METHODS`.
"""

from __future__ import annotations

from models import ContraceptiveMethod, GuidanceResult, MethodSwitchScenario, RiskLevel

# Methods the switching engine can reason about. The conservative branch in
# evaluate_switch guards against any future method added to the enum but not yet
# given switching rules.
SUPPORTED_METHODS: set[ContraceptiveMethod] = {
    ContraceptiveMethod.COMBINED_PILL,
    ContraceptiveMethod.PROGESTOGEN_ONLY_PILL,
    ContraceptiveMethod.EXTENDED_CYCLE_PILL,
    ContraceptiveMethod.VAGINAL_RING,
    ContraceptiveMethod.PATCH,
}

# Days of backup contraception needed until a freshly started method is reliably
# effective (when it wasn't started seamlessly). Combined methods take ~7 days;
# the progestogen-only pill takes ~2.
LEAD_TIME_DAYS: dict[ContraceptiveMethod, int] = {
    ContraceptiveMethod.COMBINED_PILL: 7,
    ContraceptiveMethod.EXTENDED_CYCLE_PILL: 7,
    ContraceptiveMethod.VAGINAL_RING: 7,
    ContraceptiveMethod.PATCH: 7,
    ContraceptiveMethod.PROGESTOGEN_ONLY_PILL: 2,
}


def _lead_time(method: ContraceptiveMethod) -> int:
    return LEAD_TIME_DAYS.get(method, 7)


# Human-readable method names for user-facing summaries.
METHOD_LABELS: dict[ContraceptiveMethod, str] = {
    ContraceptiveMethod.COMBINED_PILL: "the combined pill",
    ContraceptiveMethod.PROGESTOGEN_ONLY_PILL: "the progestogen-only pill",
    ContraceptiveMethod.EXTENDED_CYCLE_PILL: "the extended-cycle pill",
    ContraceptiveMethod.VAGINAL_RING: "the vaginal ring",
    ContraceptiveMethod.PATCH: "the patch",
}


def _label(method: ContraceptiveMethod) -> str:
    return METHOD_LABELS.get(method, method.value)


# Transition-specific practical tips, keyed by (fromMethod, toMethod).
_M = ContraceptiveMethod
TRANSITION_NOTES: dict[tuple[ContraceptiveMethod, ContraceptiveMethod], str] = {
    (_M.COMBINED_PILL, _M.VAGINAL_RING): (
        "Insert the ring on the day you would have taken your next active pill."
    ),
    (_M.EXTENDED_CYCLE_PILL, _M.VAGINAL_RING): (
        "Insert the ring on the day you would have taken your next active pill."
    ),
    (_M.PROGESTOGEN_ONLY_PILL, _M.VAGINAL_RING): (
        "Insert the ring on the day after your last progestogen-only pill."
    ),
    (_M.VAGINAL_RING, _M.COMBINED_PILL): (
        "Start the pill on the day you remove the ring."
    ),
    (_M.VAGINAL_RING, _M.EXTENDED_CYCLE_PILL): (
        "Start the pill on the day you remove the ring."
    ),
    (_M.VAGINAL_RING, _M.PROGESTOGEN_ONLY_PILL): (
        "Start the pill on the day you remove the ring."
    ),
    # Ring <-> patch
    (_M.VAGINAL_RING, _M.PATCH): "Apply the patch on the day you remove the ring.",
    (_M.PATCH, _M.VAGINAL_RING): "Insert the ring on the day you remove the patch.",
    # Pill <-> patch
    (_M.COMBINED_PILL, _M.PATCH): (
        "Apply the patch on the day you would have taken your next active pill."
    ),
    (_M.EXTENDED_CYCLE_PILL, _M.PATCH): (
        "Apply the patch on the day you would have taken your next active pill."
    ),
    (_M.PROGESTOGEN_ONLY_PILL, _M.PATCH): (
        "Apply the patch on the day after your last progestogen-only pill."
    ),
    (_M.PATCH, _M.COMBINED_PILL): "Start the pill on the day you remove the patch.",
    (_M.PATCH, _M.EXTENDED_CYCLE_PILL): (
        "Start the pill on the day you remove the patch."
    ),
    (_M.PATCH, _M.PROGESTOGEN_ONLY_PILL): (
        "Start the pill on the day you remove the patch."
    ),
}


def _transition_notes(scenario: MethodSwitchScenario) -> list[str]:
    note = TRANSITION_NOTES.get((scenario.fromMethod, scenario.toMethod))
    return [note] if note else []


def evaluate_switch(scenario: MethodSwitchScenario) -> GuidanceResult:
    """Evaluate a method switch and return structured guidance."""
    if (
        scenario.fromMethod not in SUPPORTED_METHODS
        or scenario.toMethod not in SUPPORTED_METHODS
    ):
        return GuidanceResult(
            riskLevel=RiskLevel.MODERATE,
            takePillNow=False,
            useBackup=True,
            backupDays=7,
            summary=(
                "Switching guidance for this combination of methods isn't "
                "available yet. Use backup contraception and check with a "
                "pharmacist or clinician about how to switch safely."
            ),
            notes=["Unsupported method combination — no rule set implemented."],
        )

    frm, to = _label(scenario.fromMethod), _label(scenario.toMethod)

    notes = _transition_notes(scenario)

    # Seamless switch (no gap): protection carries over continuously.
    if scenario.gapDays == 0:
        return GuidanceResult(
            riskLevel=RiskLevel.NONE,
            takePillNow=False,
            useBackup=False,
            summary=(
                f"Switching from {frm} to {to} with no gap keeps you "
                f"continuously protected. Start {to} right away — no backup "
                "contraception is needed."
            ),
            notes=notes,
        )

    # A gap is present: the new method needs time to become reliable, so back up
    # for its lead time. The backup duration depends on the method being started.
    backup = _lead_time(scenario.toMethod)
    notes = notes + [
        "Switching as your old method runs out (no gap) avoids needing backup."
    ]
    return GuidanceResult(
        riskLevel=RiskLevel.MODERATE,
        takePillNow=False,
        useBackup=True,
        backupDays=backup,
        summary=(
            f"There was a {scenario.gapDays}-day gap before starting {to}. "
            f"Start {to} now and use backup contraception for the next "
            f"{backup} days, until {to} is reliably effective."
        ),
        notes=notes,
    )
