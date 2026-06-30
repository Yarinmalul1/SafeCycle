"""Product Catalog role.

Knowledge about the contraceptive products SafeCycle supports: how to normalize
product names, and which pill family / rule-set each product belongs to. Used by
the logic engine to decide which rules apply.

NOTE: skeleton — a tiny seed catalog is included so other modules have something
to import; this will grow into a fuller, possibly DB-backed catalog.
"""

from __future__ import annotations

from models import PillType

# Seed catalog: product name (lowercase) -> (pill family, regimen, plain-language
# description for the catalog UI). Keep descriptions short -- one line each --
# because the frontend renders them in a compact list row.
#
# Each entry's regimen and timing details are sourced from the manufacturer
# Summary of Product Characteristics (SmPC) and corroborated against the FSRH
# Combined Hormonal Contraception (CHC) and Progestogen-only Pill (POP)
# guidance. Brand-specific SmPCs are the primary source for active/inactive
# pill counts; the missed-pill timing windows (24h for combined, 3h or 12h
# for POPs) follow FSRH / WHO standard rules, not brand idiosyncrasies.
CATALOG: dict[str, tuple[PillType, str, str]] = {
    # Source: Bayer Yasmin SmPC; FSRH CHC guidance (2023). 21 active
    # (ethinylestradiol 30 mcg + drospirenone 3 mg) + 7 hormone-free days.
    "yasmin": (
        PillType.COMBINED,
        "21+7",
        "21 active pills then 7 inactive (or pill-free) days. Repeat each pack.",
    ),
    # Source: Bayer Yaz SmPC; FSRH CHC guidance. 24 active (EE 20 mcg +
    # drospirenone 3 mg) + 4 inactive. Shorter hormone-free interval than
    # 21+7 packs.
    "yaz": (
        PillType.COMBINED,
        "24+4",
        "24 active pills then 4 inactive days. Shorter break than a 21+7 pack.",
    ),
    # Source: Organon/Merck Cerazette SmPC; FSRH POP guidance (2022).
    # Desogestrel 75 mcg, continuous, 12-hour missed-pill window (wider
    # than older POPs because of stronger ovulation suppression).
    "cerazette": (
        PillType.PROGESTOGEN_ONLY,
        "continuous",
        "Taken every day with no break. Late by more than 12 hours counts as missed.",
    ),
    # Source: Janssen Micronor SmPC; FSRH POP guidance. Norethisterone
    # 350 mcg, continuous, classic 3-hour missed-pill window.
    "micronor": (
        PillType.PROGESTOGEN_ONLY,
        "continuous",
        "Taken every day with no break. Stricter 3-hour late window than desogestrel POPs.",
    ),
    # Source: Teva Seasonique SmPC; FSRH extended/continuous CHC guidance.
    # 84 active (EE 30 mcg + LNG 150 mcg) + 7 low-dose (EE 10 mcg). Yields
    # a withdrawal bleed only ~4x/year instead of monthly.
    "seasonique": (
        PillType.EXTENDED_CYCLE,
        "84+7",
        "Extended cycle: 84 active pills then 7 low-dose pills, so you bleed once a season.",
    ),
    # Source: Organon/Merck NuvaRing SmPC; FSRH CHC guidance. Etonogestrel
    # 11.7 mg + EE 2.7 mg, releases EE 15 mcg + ENG 120 mcg per day. In 3
    # weeks, out for the 4th (withdrawal bleed), then a new ring.
    "nuvaring": (
        PillType.RING,
        "21+7",
        "A flexible vaginal ring. In for 3 weeks, out for the 4th, then start a new one.",
    ),
}

# Product families the logic engine currently has a rule set for.
SUPPORTED_TYPES: set[PillType] = {
    PillType.COMBINED,
    PillType.PROGESTOGEN_ONLY,
    PillType.EXTENDED_CYCLE,
    PillType.RING,
}

# Progestogen-only pills must be taken within a per-product window (in hours).
# Desogestrel POPs (e.g. Cerazette) allow 12 hours; older norethisterone POPs
# allow only 3. Unknown POPs default to the stricter 3-hour window.
DEFAULT_POP_WINDOW_HOURS = 3
POP_WINDOW_HOURS: dict[str, int] = {
    "cerazette": 12,
}


def pop_window_hours(product: str) -> int:
    """Return the late-dose window (hours) for a progestogen-only pill."""
    return POP_WINDOW_HOURS.get(normalize(product), DEFAULT_POP_WINDOW_HOURS)


def is_supported(product: str) -> bool:
    """Whether the engine has rules for this product's family."""
    return pill_type(product) in SUPPORTED_TYPES


def list_products() -> list[dict]:
    """Return the catalog as a sorted list of product records.

    Each record has the product `name`, its pill-family `type`, whether it is
    `supported` (i.e. the engine has rules for that family), the pack `regimen`,
    and a plain-language `description` for the catalog UI.
    """
    return [
        {
            "name": name,
            "type": ptype,
            "supported": ptype in SUPPORTED_TYPES,
            "regimen": regimen,
            "description": description,
        }
        for name, (ptype, regimen, description) in sorted(CATALOG.items())
    ]


def normalize(product: str) -> str:
    """Normalize a product name for lookup (lowercase, trimmed)."""
    return product.strip().lower()


def pill_type(product: str) -> PillType:
    """Return the pill family for a product, or UNKNOWN if unrecognized."""
    entry = CATALOG.get(normalize(product))
    return entry[0] if entry else PillType.UNKNOWN
