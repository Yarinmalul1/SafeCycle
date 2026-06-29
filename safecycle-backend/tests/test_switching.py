"""Tests for the deterministic method-switching engine."""

from __future__ import annotations

from logic.switching import evaluate_switch
from models import ContraceptiveMethod as M
from models import MethodSwitchScenario, RiskLevel


def _switch(frm: M, to: M, **overrides) -> MethodSwitchScenario:
    base = {"fromMethod": frm, "toMethod": to}
    base.update(overrides)
    return MethodSwitchScenario(**base)


# --------------------------------------------------------------------------- #
# Seamless pill-type switches
# --------------------------------------------------------------------------- #
def test_combined_to_pop_seamless_is_continuous_protection():
    result = evaluate_switch(_switch(M.COMBINED_PILL, M.PROGESTOGEN_ONLY_PILL))
    assert result.riskLevel is RiskLevel.NONE
    assert result.useBackup is False


def test_pop_to_combined_seamless_is_continuous_protection():
    result = evaluate_switch(_switch(M.PROGESTOGEN_ONLY_PILL, M.COMBINED_PILL))
    assert result.riskLevel is RiskLevel.NONE
    assert result.useBackup is False


def test_combined_to_extended_seamless_is_continuous_protection():
    result = evaluate_switch(_switch(M.COMBINED_PILL, M.EXTENDED_CYCLE_PILL))
    assert result.riskLevel is RiskLevel.NONE
    assert result.useBackup is False


def test_pill_switch_with_gap_recommends_backup():
    result = evaluate_switch(
        _switch(M.COMBINED_PILL, M.PROGESTOGEN_ONLY_PILL, gapDays=3)
    )
    assert result.useBackup is True
    assert result.riskLevel is RiskLevel.MODERATE


# --------------------------------------------------------------------------- #
# Methods not yet covered fall back to conservative guidance
# --------------------------------------------------------------------------- #
def test_unsupported_method_is_conservative():
    result = evaluate_switch(_switch(M.VAGINAL_RING, M.COMBINED_PILL))
    assert result.riskLevel is RiskLevel.MODERATE
    assert result.useBackup is True
    assert "isn't available" in result.summary
