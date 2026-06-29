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
