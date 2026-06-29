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

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import ValidationError

from ai import answer_phraser, product_catalog, question_generator, safety_filter
from logic import engine
from models import (
    AskQuestionRequest,
    GuidanceResponse,
    ParsedScenario,
    ParseInputRequest,
    PillScenario,
    ProductInfo,
    QuestionResult,
    SafetyFilterResult,
)

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


# --------------------------------------------------------------------------- #
# Guidance role — endpoint
# --------------------------------------------------------------------------- #
def _to_pill_scenario(parsed: ParsedScenario) -> PillScenario:
    """Narrow a parsed scenario into the engine's validated `PillScenario`.

    The engine needs a product and a known pack week. When either is missing,
    we return a 422 with a single, user-facing clarifying question rather than
    guessing — gap-filling is the parser / question-generator's job upstream.
    """
    if not parsed.product:
        raise HTTPException(
            status_code=422,
            detail="Which contraceptive product is this about?",
        )
    if parsed.cycleWeek is None:
        raise HTTPException(
            status_code=422,
            detail="Which week of your pill pack are you in (1-4)?",
        )
    try:
        return PillScenario(
            product=parsed.product,
            cycleWeek=parsed.cycleWeek,
            pillsMissed=parsed.pillsMissed or 0,
            hoursLate=parsed.hoursLate,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors(include_url=False)) from exc


@app.post("/api/guidance", response_model=GuidanceResponse)
def guidance(parsed: ParsedScenario) -> GuidanceResponse:
    """Run the logic engine over a parsed scenario and phrase the result.

    Pipeline: ParsedScenario -> PillScenario -> deterministic engine decision
    -> Answer Phraser -> user-facing message.
    """
    scenario = _to_pill_scenario(parsed)
    result = engine.evaluate(scenario)
    message = answer_phraser.phrase(result, client=client)
    return GuidanceResponse(guidance=result, message=message)


# --------------------------------------------------------------------------- #
# Safety Filter role — endpoint
# --------------------------------------------------------------------------- #
@app.post("/api/safety-filter", response_model=SafetyFilterResult)
def safety_filter_endpoint(parsed: ParsedScenario) -> SafetyFilterResult:
    """Screen a parsed scenario for urgent red flags (deterministic, no LLM)."""
    return safety_filter.screen(parsed)


# --------------------------------------------------------------------------- #
# Question Generator role — endpoint
# --------------------------------------------------------------------------- #
@app.post("/api/ask-question", response_model=QuestionResult)
def ask_question(req: AskQuestionRequest) -> QuestionResult:
    """Return the next clarifying question for an in-progress scenario."""
    return question_generator.generate(req)


# --------------------------------------------------------------------------- #
# Product Catalog role — endpoint
# --------------------------------------------------------------------------- #
@app.get("/api/products", response_model=list[ProductInfo])
def products() -> list[ProductInfo]:
    """List the contraceptive products SafeCycle knows about."""
    return [ProductInfo(**p) for p in product_catalog.list_products()]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
