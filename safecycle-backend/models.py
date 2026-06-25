"""SafeCycle Pydantic models.

This module is the single source of truth for the data shapes used across the
SafeCycle backend: the Input Parser request/response, the structured scenario
consumed by the logic engine, and the guidance result the engine produces.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #
class RiskLevel(str, Enum):
    """How urgent / risky the situation is, in plain terms."""

    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class PillType(str, Enum):
    """Family of contraceptive pill. Affects which rules apply."""

    COMBINED = "combined"  # combined oral contraceptive (estrogen + progestogen)
    PROGESTOGEN_ONLY = "progestogen_only"  # mini-pill
    UNKNOWN = "unknown"


# --------------------------------------------------------------------------- #
# Input Parser role — request/response models
# --------------------------------------------------------------------------- #
class ParseInputRequest(BaseModel):
    """Raw, natural-language contraception scenario from the user."""

    userInput: str = Field(
        ...,
        min_length=1,
        description="Free-text description, e.g. 'I took my yasmin 6 hours late'.",
    )


class ParsedScenario(BaseModel):
    """Structured contraception scenario for downstream guidance logic."""

    product: Optional[str] = Field(
        None,
        description="The contraceptive product named, normalized to lowercase "
        "(e.g. 'yasmin', 'cerazette'), or null if not stated.",
    )
    hoursLate: Optional[int] = Field(
        None,
        description="How many hours late the pill was taken, if stated. "
        "Null if not mentioned or not applicable.",
    )
    pillsMissed: Optional[int] = Field(
        None,
        description="Number of pills completely missed/skipped, if stated. "
        "Null if not mentioned.",
    )
    cycleWeek: Optional[int] = Field(
        None,
        description="Which week of the pill pack the user is in (1-4), if stated. "
        "Null if not mentioned.",
    )
    confidence: float = Field(
        ...,
        description="Confidence (0.0-1.0) that the extracted fields correctly "
        "capture the user's scenario.",
    )
    clarifyingQuestion: Optional[str] = Field(
        None,
        description="A single question to ask the user when essential information "
        "is missing or ambiguous; null when the scenario is clear enough.",
    )


# --------------------------------------------------------------------------- #
# Logic engine — input
# --------------------------------------------------------------------------- #
class PillScenario(BaseModel):
    """The structured, validated scenario the logic engine reasons over.

    This is intentionally narrower than `ParsedScenario`: by the time a scenario
    reaches the engine we expect the essential fields to be present (the parser /
    question generator are responsible for filling gaps first).
    """

    product: str = Field(..., description="Product name, lowercase (e.g. 'yasmin').")
    cycleWeek: int = Field(
        ...,
        ge=1,
        le=4,
        description="Week of the pill pack (1-3 active, 4 = placebo/break).",
    )
    pillsMissed: int = Field(
        0,
        ge=0,
        description="Number of active pills completely missed (>=24h late each).",
    )
    hoursLate: Optional[int] = Field(
        None,
        ge=0,
        description="Hours late for the most recent pill, if it was taken late "
        "rather than fully missed.",
    )
    unprotectedSex: bool = Field(
        False,
        description="Whether unprotected sex occurred during the at-risk window.",
    )


# --------------------------------------------------------------------------- #
# Logic engine — output
# --------------------------------------------------------------------------- #
class GuidanceResult(BaseModel):
    """The engine's structured guidance for a scenario.

    Phrasing for the user is the Answer Phraser's job; this is the raw decision.
    """

    riskLevel: RiskLevel = Field(..., description="Overall risk for the scenario.")
    takePillNow: bool = Field(
        True,
        description="Whether the user should take the missed/late pill immediately.",
    )
    useBackup: bool = Field(
        False,
        description="Whether barrier backup (e.g. condoms) is needed.",
    )
    backupDays: int = Field(
        0,
        ge=0,
        description="Number of days backup contraception is recommended.",
    )
    considerEmergencyContraception: bool = Field(
        False,
        description="Whether emergency contraception should be considered.",
    )
    skipPlaceboBreak: bool = Field(
        False,
        description="Whether to skip the pill-free/placebo break and start the "
        "next pack immediately (relevant in week 3).",
    )
    summary: str = Field(..., description="Short, human-readable explanation.")
    notes: list[str] = Field(
        default_factory=list,
        description="Additional caveats or follow-up notes.",
    )
