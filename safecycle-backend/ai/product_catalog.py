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
CATALOG: dict[str, tuple[PillType, str, str]] = {
    "yasmin": (
        PillType.COMBINED,
        "21+7",
        "21 active pills then 7 inactive (or pill-free) days. Repeat each pack.",
    ),
    "yaz": (
        PillType.COMBINED,
        "24+4",
        "24 active pills then 4 inactive days. Shorter break than a 21+7 pack.",
    ),
    "cerazette": (
        PillType.PROGESTOGEN_ONLY,
        "continuous",
        "Taken every day with no break. Late by more than 12 hours counts as missed.",
    ),
    "micronor": (
        PillType.PROGESTOGEN_ONLY,
        "continuous",
        "Taken every day with no break. Stricter 3-hour late window than desogestrel POPs.",
    ),
    "seasonique": (
        PillType.EXTENDED_CYCLE,
        "84+7",
        "Extended cycle: 84 active pills then 7 low-dose pills, so you bleed once a season.",
    ),
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
