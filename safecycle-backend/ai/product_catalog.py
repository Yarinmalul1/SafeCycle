"""Product Catalog role.

Knowledge about the contraceptive products SafeCycle supports: how to normalize
product names, and which pill family / rule-set each product belongs to. Used by
the logic engine to decide which rules apply.

NOTE: skeleton — a tiny seed catalog is included so other modules have something
to import; this will grow into a fuller, possibly DB-backed catalog.
"""

from __future__ import annotations

from models import PillType

# Minimal seed catalog: product name (lowercase) -> pill family.
CATALOG: dict[str, PillType] = {
    "yasmin": PillType.COMBINED,
    "yaz": PillType.COMBINED,
    "cerazette": PillType.PROGESTOGEN_ONLY,
}


def normalize(product: str) -> str:
    """Normalize a product name for lookup (lowercase, trimmed)."""
    return product.strip().lower()


def pill_type(product: str) -> PillType:
    """Return the pill family for a product, or UNKNOWN if unrecognized."""
    return CATALOG.get(normalize(product), PillType.UNKNOWN)
