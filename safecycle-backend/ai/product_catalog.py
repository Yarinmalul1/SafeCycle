"""Product Catalog role.

Knowledge about the contraceptive products SafeCycle supports: how to normalize
product names, and which pill family / rule-set each product belongs to. Used by
the logic engine to decide which rules apply.

NOTE: skeleton — a tiny seed catalog is included so other modules have something
to import; this will grow into a fuller, possibly DB-backed catalog.
"""

from __future__ import annotations

from models import PillType

# Seed catalog: product name (lowercase) -> pill family.
CATALOG: dict[str, PillType] = {
    "yasmin": PillType.COMBINED,  # combined, 21 active + 7 inactive
    "yaz": PillType.COMBINED,  # combined, 24 active + 4 inactive
    "cerazette": PillType.PROGESTOGEN_ONLY,  # desogestrel, 12h window
    "micronor": PillType.PROGESTOGEN_ONLY,  # norethisterone, 3h window
}

# Pill families the logic engine currently has a rule set for.
SUPPORTED_TYPES: set[PillType] = {PillType.COMBINED, PillType.PROGESTOGEN_ONLY}

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

    Each record has the product `name`, its pill-family `type`, and whether it
    is `supported` (i.e. the engine has rules for that family).
    """
    return [
        {"name": name, "type": ptype, "supported": ptype in SUPPORTED_TYPES}
        for name, ptype in sorted(CATALOG.items())
    ]


def normalize(product: str) -> str:
    """Normalize a product name for lookup (lowercase, trimmed)."""
    return product.strip().lower()


def pill_type(product: str) -> PillType:
    """Return the pill family for a product, or UNKNOWN if unrecognized."""
    return CATALOG.get(normalize(product), PillType.UNKNOWN)
