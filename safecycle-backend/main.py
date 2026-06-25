"""SafeCycle backend — FastAPI application.

SafeCycle is a contraception guidance app. This service exposes:
  - GET  /health           : liveness check
"""

from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel, Field

load_dotenv()

# Default to the latest, most capable Claude model. Override via env if needed.
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-8")

app = FastAPI(
    title="SafeCycle API",
    description="Contraception guidance, made clear.",
    version="0.1.0",
)


# --------------------------------------------------------------------------- #
# Health
# --------------------------------------------------------------------------- #
@app.get("/health")
def health() -> dict:
    """Liveness probe. Returns 200 with basic service info."""
    return {"status": "ok", "service": "safecycle-backend", "version": app.version}


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
