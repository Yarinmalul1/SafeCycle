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

# Methods the switching engine can currently reason about. Expanded as coverage
# grows (the ring and patch are added in later commits).
SUPPORTED_METHODS: set[ContraceptiveMethod] = {
    ContraceptiveMethod.COMBINED_PILL,
    ContraceptiveMethod.PROGESTOGEN_ONLY_PILL,
    ContraceptiveMethod.EXTENDED_CYCLE_PILL,
}

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
        )

    # A gap is present. Detailed timing/overlap handling is added in later
    # commits; for now, recommend backup conservatively.
    return GuidanceResult(
        riskLevel=RiskLevel.MODERATE,
        takePillNow=False,
        useBackup=True,
        backupDays=7,
        summary=(
            f"There was a gap before starting {to}. Start {to} now and use "
            "backup contraception for the next 7 days to be safe."
        ),
    )
