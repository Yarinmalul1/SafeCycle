"""SafeCycle backend — FastAPI application.

SafeCycle is a contraception guidance app. This service exposes:
  - GET  /health           : liveness check
  - POST /api/parse-input  : Input Parser role — turns a user's free-text
                             description of a contraception scenario into a
                             structured object for downstream guidance logic.

Note: the Input Parser only *extracts and structures* what the user said. It
does not provide medical advice or risk assessment — that is the job of later
stages in the SafeCycle agent pipeline.
"""

from __future__ import annotations

import os
from typing import Optional

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

load_dotenv()

# Default to the latest, most capable Claude model. Override via env if needed.
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-8")

app = FastAPI(
    title="SafeCycle API",
    description="Contraception guidance, made clear.",
    version="0.1.0",
)

# A single client is created once and reused. It reads ANTHROPIC_API_KEY from
# the environment (loaded from .env above).
client = anthropic.Anthropic()


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


# --------------------------------------------------------------------------- #
# Input Parser role — endpoint
# --------------------------------------------------------------------------- #
PARSER_SYSTEM = (
    "You are the Input Parser for SafeCycle, a contraception guidance app. "
    "Your only job is to convert the user's free-text description of a "
    "contraception scenario into the structured schema. "
    "Rules:\n"
    "- Normalize the product name to lowercase (e.g. 'Yasmin' -> 'yasmin').\n"
    "- Only extract values the user actually states or clearly implies; never "
    "invent timing, counts, or products. Leave unmentioned fields null.\n"
    "- 'hoursLate' is for a pill taken late; 'pillsMissed' is for pills fully "
    "skipped. These are different — do not conflate them.\n"
    "- Set 'confidence' to reflect how certain you are about the extraction "
    "(1.0 = explicit and unambiguous, lower when you had to infer).\n"
    "- If essential information is missing or ambiguous (e.g. no product, or it "
    "is unclear whether a pill was late vs. missed), set 'clarifyingQuestion' to "
    "one concise question. Otherwise set it to null.\n"
    "Do NOT give medical advice, risk levels, or recommendations — only parse."
)


@app.post("/api/parse-input", response_model=ParsedScenario)
def parse_input(req: ParseInputRequest) -> ParsedScenario:
    """Parse a user's contraception scenario into a structured object."""
    try:
        response = client.messages.parse(
            model=MODEL,
            max_tokens=1024,
            system=PARSER_SYSTEM,
            messages=[{"role": "user", "content": req.userInput}],
            output_format=ParsedScenario,
        )
    except anthropic.APIStatusError as exc:
        raise HTTPException(status_code=502, detail=f"LLM error: {exc.message}") from exc
    except anthropic.APIConnectionError as exc:
        raise HTTPException(status_code=503, detail="Could not reach the LLM.") from exc

    if response.stop_reason == "refusal":
        raise HTTPException(status_code=422, detail="Request was declined.")

    return response.parsed_output
