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

import base64
import binascii
import json
import os

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from ai import (
    answer_phraser,
    guidance_fallback,
    history_manager,
    product_catalog,
    question_generator,
    safety_filter,
)
from ai.product_catalog import pill_type
from db import queries
from logic import engine, switching
from models import (
    AskQuestionRequest,
    AuthUser,
    GoogleAuthRequest,
    GuidanceResponse,
    HistorySession,
    MethodSwitchScenario,
    ParsedScenario,
    ParseInputRequest,
    PillScenario,
    PillType,
    ProductInfo,
    QuestionResult,
    SafetyFilterResult,
)

# Default user id used until real auth is wired up.
DEMO_USER = "demo-user"

load_dotenv()

# Default to the latest, most capable Claude model. Override via env if needed.
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-8")

app = FastAPI(
    title="SafeCycle API",
    description="Contraception guidance, made clear.",
    version="0.1.0",
)

# Allow the static frontend dev server (serve.js on :5500) to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500"],
    allow_methods=["*"],
    allow_headers=["*"],
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
    "- Set 'unprotectedSex' to true or false only if the user indicates whether "
    "unprotected sex occurred during the at-risk window; leave it null if not "
    "mentioned.\n"
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

    The engine always needs a product. cycleWeek is only meaningful for combined
    pills (their rules branch on week 1/2/3/4); progestogen-only pills, the
    vaginal ring, and extended-cycle pills ignore it. We therefore only demand
    cycleWeek when the product is a combined pill.
    """
    if not parsed.product:
        raise HTTPException(
            status_code=422,
            detail="Which contraceptive product is this about?",
        )
    if pill_type(parsed.product) is PillType.COMBINED and parsed.cycleWeek is None:
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
            unprotectedSex=bool(parsed.unprotectedSex),
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors(include_url=False)) from exc


@app.post("/api/guidance", response_model=GuidanceResponse)
def guidance(parsed: ParsedScenario, user_id: str = DEMO_USER) -> GuidanceResponse:
    """Run the logic engine over a parsed scenario and phrase the result.

    Pipeline: ParsedScenario -> PillScenario -> deterministic engine decision
    -> Answer Phraser (for known products) OR Claude fallback (for unknown
    products the engine has no rules for) -> user-facing message. The session
    is recorded so it shows up under GET /api/history.
    """
    scenario = _to_pill_scenario(parsed)
    result = engine.evaluate(scenario)

    # Unknown products land in the engine's "unsupported" branch; instead of
    # showing the canned "speak to a pharmacist" string, ask Claude to generate
    # safe, scenario-specific guidance.
    if pill_type(scenario.product) is PillType.UNKNOWN:
        message = guidance_fallback.fallback_guidance(parsed, result, client=client)
        source = "fallback"
    else:
        message = answer_phraser.phrase(result, client=client)
        source = "engine"

    history_manager.record(user_id, scenario, result, message)
    return GuidanceResponse(guidance=result, message=message, source=source)


# --------------------------------------------------------------------------- #
# Method-switching guidance — endpoint
# --------------------------------------------------------------------------- #
@app.post("/api/switch-guidance", response_model=GuidanceResponse)
def switch_guidance(scenario: MethodSwitchScenario) -> GuidanceResponse:
    """Guide a user through switching from one contraceptive method to another.

    Runs the deterministic switching engine and phrases the result. No history
    is recorded — switching is advisory and not tied to a dated pill event.
    """
    result = switching.evaluate_switch(scenario)
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


# --------------------------------------------------------------------------- #
# History Manager role — endpoint
# --------------------------------------------------------------------------- #
@app.get("/api/history", response_model=list[HistorySession])
def history(user_id: str = DEMO_USER, limit: int = 5) -> list[HistorySession]:
    """Return a user's past guidance sessions, newest first."""
    return [HistorySession(**s) for s in history_manager.recent(user_id, limit)]


# --------------------------------------------------------------------------- #
# Auth role — Google sign-in endpoint
# --------------------------------------------------------------------------- #
def _decode_jwt_claims(token: str) -> dict:
    """Decode (without verifying) the claims from a JWT's payload segment.

    NOTE: this only base64url-decodes the middle segment — it does NOT verify
    the signature, issuer, audience, or expiry. That is a deliberate shortcut
    for local development; before production this must be replaced with proper
    verification of the Google ID token (e.g. google-auth's verify_oauth2_token).
    """
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=401, detail="Invalid Google credential.")
    payload = parts[1]
    # JWT uses base64url without padding; restore it before decoding.
    payload += "=" * (-len(payload) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(payload))
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid Google credential.") from exc


@app.post("/api/auth/google", response_model=AuthUser)
def auth_google(req: GoogleAuthRequest) -> AuthUser:
    """Sign a user in from a Google ID token and store their session.

    Decodes the token's claims for name/email, derives a stable user id, and
    records the session in memory so the rest of the app can recognise the user.
    """
    claims = _decode_jwt_claims(req.credential)

    email = claims.get("email")
    if not email:
        raise HTTPException(status_code=401, detail="Google credential is missing an email.")

    # `sub` is Google's stable per-user id; fall back to the email if absent.
    user_id = claims.get("sub") or email
    name = claims.get("name") or email.split("@")[0]

    user = AuthUser(name=name, email=email, userId=user_id)
    queries.save_user(user_id, user.model_dump())
    return user


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
