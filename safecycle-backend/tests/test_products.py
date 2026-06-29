"""Per-product tests for the guidance engine and catalog.

Each section pins down how a specific product is classified and how the engine
treats it, so adding products can't silently regress the others.
"""

from __future__ import annotations

from ai import product_catalog
from logic.engine import evaluate
from models import PillScenario, PillType, RiskLevel


def _scenario(product: str, **overrides) -> PillScenario:
    base = {"product": product, "cycleWeek": 1, "pillsMissed": 0}
    base.update(overrides)
    return PillScenario(**base)


# --------------------------------------------------------------------------- #
# Yaz — combined pill (24 active + 4 inactive)
# --------------------------------------------------------------------------- #
def test_yaz_is_combined_and_supported():
    assert product_catalog.pill_type("yaz") is PillType.COMBINED
    assert product_catalog.is_supported("yaz") is True


def test_yaz_late_under_24h_is_no_risk():
    result = evaluate(_scenario("yaz", pillsMissed=0, hoursLate=6))
    assert result.riskLevel is RiskLevel.NONE
    assert result.takePillNow is True


def test_yaz_two_missed_week1_recommends_backup():
    result = evaluate(_scenario("yaz", pillsMissed=2, cycleWeek=1))
    assert result.useBackup is True
    assert result.riskLevel is RiskLevel.MODERATE


def test_yaz_two_missed_week3_skips_placebo_break():
    result = evaluate(_scenario("yaz", pillsMissed=2, cycleWeek=3))
    assert result.skipPlaceboBreak is True


# --------------------------------------------------------------------------- #
# Cerazette — progestogen-only pill (desogestrel, 12-hour window)
# --------------------------------------------------------------------------- #
def test_cerazette_is_pop_and_supported():
    assert product_catalog.pill_type("cerazette") is PillType.PROGESTOGEN_ONLY
    assert product_catalog.is_supported("cerazette") is True
    assert product_catalog.pop_window_hours("cerazette") == 12


def test_cerazette_within_12h_window_is_protected():
    result = evaluate(_scenario("cerazette", pillsMissed=0, hoursLate=10))
    assert result.riskLevel is RiskLevel.NONE
    assert result.useBackup is False


def test_cerazette_over_12h_is_missed_and_needs_backup():
    result = evaluate(_scenario("cerazette", pillsMissed=0, hoursLate=14))
    assert result.riskLevel is RiskLevel.MODERATE
    assert result.useBackup is True
    assert result.backupDays == 2


def test_cerazette_missed_with_unprotected_sex_is_high_risk():
    result = evaluate(_scenario("cerazette", pillsMissed=1, unprotectedSex=True))
    assert result.riskLevel is RiskLevel.HIGH
    assert result.considerEmergencyContraception is True


# --------------------------------------------------------------------------- #
# Micronor — progestogen-only pill (norethisterone, 3-hour window)
# --------------------------------------------------------------------------- #
def test_micronor_is_pop_with_default_3h_window():
    assert product_catalog.pill_type("micronor") is PillType.PROGESTOGEN_ONLY
    assert product_catalog.pop_window_hours("micronor") == 3


def test_micronor_within_3h_window_is_protected():
    result = evaluate(_scenario("micronor", pillsMissed=0, hoursLate=2))
    assert result.riskLevel is RiskLevel.NONE
    assert result.useBackup is False


def test_micronor_stricter_than_cerazette_at_same_delay():
    # A 5-hour delay is fine for Cerazette (12h) but a miss for Micronor (3h).
    delay = 5
    cerazette = evaluate(_scenario("cerazette", pillsMissed=0, hoursLate=delay))
    micronor = evaluate(_scenario("micronor", pillsMissed=0, hoursLate=delay))
    assert cerazette.riskLevel is RiskLevel.NONE
    assert micronor.riskLevel is RiskLevel.MODERATE
    assert micronor.useBackup is True
    assert micronor.backupDays == 2


# --------------------------------------------------------------------------- #
# Seasonique — extended-cycle combined pill (84 active + 7)
# --------------------------------------------------------------------------- #
def test_seasonique_is_extended_cycle_and_supported():
    assert product_catalog.pill_type("seasonique") is PillType.EXTENDED_CYCLE
    assert product_catalog.is_supported("seasonique") is True


def test_seasonique_one_missed_is_low_risk():
    result = evaluate(_scenario("seasonique", pillsMissed=1))
    assert result.riskLevel is RiskLevel.LOW
    assert result.useBackup is False


def test_seasonique_two_missed_needs_backup_and_mentions_continuous():
    result = evaluate(_scenario("seasonique", pillsMissed=2))
    assert result.useBackup is True
    assert result.backupDays == 7
    assert any("extended-cycle" in n.lower() for n in result.notes)


def test_seasonique_two_missed_with_unprotected_sex_is_high_risk():
    result = evaluate(_scenario("seasonique", pillsMissed=2, unprotectedSex=True))
    assert result.riskLevel is RiskLevel.HIGH
    assert result.considerEmergencyContraception is True


# --------------------------------------------------------------------------- #
# NuvaRing — vaginal ring
# --------------------------------------------------------------------------- #
def test_nuvaring_is_ring_and_supported():
    assert product_catalog.pill_type("nuvaring") is PillType.RING
    assert product_catalog.is_supported("nuvaring") is True


def test_nuvaring_out_under_48h_is_protected():
    result = evaluate(_scenario("nuvaring", pillsMissed=0, hoursLate=12))
    assert result.riskLevel is RiskLevel.NONE
    assert result.useBackup is False


def test_nuvaring_out_48h_or_more_needs_backup():
    result = evaluate(_scenario("nuvaring", pillsMissed=0, hoursLate=50))
    assert result.riskLevel is RiskLevel.MODERATE
    assert result.useBackup is True
    assert result.backupDays == 7


def test_nuvaring_out_long_with_unprotected_sex_is_high_risk():
    result = evaluate(_scenario("nuvaring", pillsMissed=0, hoursLate=72, unprotectedSex=True))
    assert result.riskLevel is RiskLevel.HIGH
    assert result.considerEmergencyContraception is True
