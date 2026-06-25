"""Tests for the deterministic guidance engine (Yasmin missed-pill rules)."""

from __future__ import annotations

import pytest

from logic.engine import BACKUP_DAYS, evaluate
from models import PillScenario, RiskLevel


def _scenario(**overrides) -> PillScenario:
    """Build a Yasmin scenario with sensible defaults, overriding as needed."""
    base = {"product": "yasmin", "cycleWeek": 1, "pillsMissed": 0}
    base.update(overrides)
    return PillScenario(**base)


def test_no_pills_missed_is_no_risk():
    result = evaluate(_scenario(pillsMissed=0))
    assert result.riskLevel is RiskLevel.NONE
    assert result.useBackup is False


def test_late_under_24h_is_not_missed():
    result = evaluate(_scenario(pillsMissed=0, hoursLate=6))
    assert result.riskLevel is RiskLevel.NONE
    assert result.takePillNow is True
    assert result.useBackup is False


def test_late_over_24h_counts_as_one_missed():
    result = evaluate(_scenario(pillsMissed=0, hoursLate=30))
    assert result.riskLevel is RiskLevel.LOW
    assert result.takePillNow is True
    assert result.useBackup is False


def test_one_missed_pill_needs_no_backup():
    result = evaluate(_scenario(pillsMissed=1, cycleWeek=2))
    assert result.riskLevel is RiskLevel.LOW
    assert result.useBackup is False
    assert result.considerEmergencyContraception is False


def test_two_missed_week1_recommends_backup():
    result = evaluate(_scenario(pillsMissed=2, cycleWeek=1))
    assert result.useBackup is True
    assert result.backupDays == BACKUP_DAYS


def test_two_missed_week1_with_unprotected_sex_is_high_risk():
    result = evaluate(_scenario(pillsMissed=2, cycleWeek=1, unprotectedSex=True))
    assert result.riskLevel is RiskLevel.HIGH
    assert result.considerEmergencyContraception is True


def test_two_missed_week2_no_emergency_contraception():
    result = evaluate(_scenario(pillsMissed=3, cycleWeek=2))
    assert result.useBackup is True
    assert result.considerEmergencyContraception is False
    assert result.riskLevel is RiskLevel.MODERATE


def test_two_missed_week3_skips_placebo_break():
    result = evaluate(_scenario(pillsMissed=2, cycleWeek=3))
    assert result.useBackup is True
    assert result.skipPlaceboBreak is True


def test_unsupported_product_is_conservative():
    result = evaluate(_scenario(product="mystery-pill", pillsMissed=2))
    assert result.riskLevel is RiskLevel.MODERATE
    assert "isn't available" in result.summary


@pytest.mark.parametrize("week", [1, 2, 3])
def test_one_missed_pill_low_risk_every_active_week(week):
    result = evaluate(_scenario(pillsMissed=1, cycleWeek=week))
    assert result.riskLevel is RiskLevel.LOW
