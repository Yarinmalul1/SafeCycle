"""Product Catalog role.

Knowledge about the contraceptive products SafeCycle supports: how to normalize
product names, and which pill family / rule-set each product belongs to. Used by
the logic engine to decide which rules apply.

Descriptions are written for the user-facing catalog UI: plain language, one
to two short sentences, matched to the way the product is actually used. Every
entry's regimen and timing detail is sourced from the manufacturer Summary of
Product Characteristics (SmPC) and corroborated against FSRH / WHO MEC / CDC US
MEC / FDA prescribing information - the only sources SafeCycle accepts.
"""

from __future__ import annotations

from models import PillType

# Product name (lowercase) -> (pill family, regimen, plain-language description
# for the catalog UI). Descriptions follow one house style:
#   "A <what it is> you <how you use it>."
# Keep them one to two sentences - the catalog list row is compact.
CATALOG: dict[str, tuple[PillType, str, str]] = {
    # ---- Combined oral contraceptives ------------------------------------
    # Source: Bayer Yasmin SmPC; FSRH CHC guidance. 21 active
    # (ethinylestradiol 30 mcg + drospirenone 3 mg) + 7 hormone-free days.
    "yasmin": (
        PillType.COMBINED,
        "21+7",
        "A combined pill (estrogen + progestogen) you take once a day for 21 days, "
        "then have a 7-day break for your period before starting a new pack.",
    ),
    # Source: Bayer Yaz SmPC; FSRH CHC guidance. 24 active (EE 20 mcg +
    # drospirenone 3 mg) + 4 inactive. Shorter hormone-free interval than
    # 21+7 packs.
    "yaz": (
        PillType.COMBINED,
        "24+4",
        "A combined pill with a shorter break: 24 active pills, then 4 inactive "
        "days for a shorter bleed, then a new pack.",
    ),
    # ---- Progestogen-only pills ------------------------------------------
    # Source: Organon/Merck Cerazette SmPC; FSRH POP guidance.
    # Desogestrel 75 mcg, continuous, 12-hour missed-pill window.
    "cerazette": (
        PillType.PROGESTOGEN_ONLY,
        "continuous",
        "A progestogen-only mini-pill you take every day with no break. "
        "It has a 12-hour window if you're late.",
    ),
    # Source: Janssen Micronor SmPC; FSRH POP guidance. Norethisterone
    # 350 mcg, continuous, classic 3-hour missed-pill window.
    "micronor": (
        PillType.PROGESTOGEN_ONLY,
        "continuous",
        "A progestogen-only mini-pill you take every day with no break. "
        "Stricter than newer mini-pills - only 3 hours late counts as missed.",
    ),
    # ---- Extended-cycle combined pills -----------------------------------
    # Source: Teva Seasonique SmPC; FSRH extended/continuous CHC guidance.
    # 84 active (EE 30 mcg + LNG 150 mcg) + 7 low-dose (EE 10 mcg). Yields
    # a withdrawal bleed only ~4x/year instead of monthly.
    "seasonique": (
        PillType.EXTENDED_CYCLE,
        "84+7",
        "An extended-cycle combined pill: 84 active pills, then 7 low-dose "
        "pills. You only bleed about four times a year instead of monthly.",
    ),
    # ---- Vaginal ring ----------------------------------------------------
    # Source: Organon/Merck NuvaRing SmPC; FSRH CHC guidance. Etonogestrel
    # 11.7 mg + EE 2.7 mg, releases EE 15 mcg + ENG 120 mcg per day. In 3
    # weeks, out for the 4th (withdrawal bleed), then a new ring.
    "nuvaring": (
        PillType.RING,
        "21+7",
        "A flexible vaginal ring you wear inside your body for 3 weeks, then "
        "remove for 1 week to have your period.",
    ),
    # ---- Contraceptive patches -------------------------------------------
    # Source: Bayer / Janssen Evra SmPC; FSRH Contraceptive Patch guidance
    # (2019, updated 2022). Delivers ~20 mcg EE + ~150 mcg norelgestromin
    # per day. Apply a new patch every 7 days for 3 weeks, then 1
    # patch-free week for a withdrawal bleed.
    "evra": (
        PillType.PATCH,
        "weekly",
        "A weekly skin patch (estrogen + progestogen). Apply a new patch on "
        "the same day each week for 3 weeks, then have 1 patch-free week for "
        "your period.",
    ),
    # Source: Mylan Xulane SmPC / FDA prescribing info; generic of Evra.
    "xulane": (
        PillType.PATCH,
        "weekly",
        "A weekly skin patch that's the generic version of Evra. Same "
        "regimen: 3 weekly patches, then 1 patch-free week.",
    ),
    # Source: Agile Therapeutics Twirla SmPC / FDA prescribing info; FSRH
    # CHC guidance. EE ~30 mcg/day + levonorgestrel ~120 mcg/day. Same
    # weekly regimen as Evra/Xulane. FDA-labelled for BMI < 30.
    "twirla": (
        PillType.PATCH,
        "weekly",
        "A weekly skin patch with levonorgestrel. Apply a new patch each "
        "week for 3 weeks, then have 1 patch-free week for your period.",
    ),
}

# Product families the logic engine currently has a rule set for.
# PATCH is intentionally NOT in this set: the engine has no patch-specific
# rules yet, so patch scenarios route to the widened Claude fallback prompt
# (see main.guidance) which produces sourced patch guidance from safe
# defaults. When engine rules for patches land, add PillType.PATCH here.
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
