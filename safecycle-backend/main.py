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
from datetime import date, datetime, timedelta

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from ai import (
    answer_phraser,
    chat as chat_module,
    guidance_fallback,
    history_manager,
    product_catalog,
    question_generator,
    safety_filter,
)
from ai.product_catalog import pill_type
from db import calendars, chats, queries, sessions, users
from logic import calendar as calendar_generator
from logic import engine, switching
from models import (
    AskQuestionRequest,
    AuthUser,
    CalendarGenerateRequest,
    CalendarResponse,
    ChatMessage,
    ChatMessageRequest,
    ChatStartRequest,
    ChatSummary,
    ChatTurnResponse,
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

# Default to the latest released Claude model. Override via env if needed.
# Note: claude-opus-4-8 does not exist; the latest Opus is 4.7. Using a
# non-existent model id makes every messages.create() 404, which previously
# silently degraded the phraser/fallback to their static safe defaults.
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-7")

app = FastAPI(
    title="SafeCycle API",
    description="Contraception guidance, made clear.",
    version="0.1.0",
)

# CORS: allow the local dev server (serve.js on :5500) and the deployed
# Railway staging frontend. No trailing slashes -- browsers compare Origin
# headers byte-for-byte. Production frontend (when it lands on main) should
# be appended here or supplied via the SAFECYCLE_EXTRA_CORS_ORIGINS env var
# (comma-separated) so we don't need a redeploy to add another host.
_DEFAULT_CORS_ORIGINS = [
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "https://frontend-staging-staging-a212.up.railway.app",
]
_extra = os.getenv("SAFECYCLE_EXTRA_CORS_ORIGINS", "").strip()
_EXTRA_CORS_ORIGINS = [o.strip() for o in _extra.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_DEFAULT_CORS_ORIGINS + _EXTRA_CORS_ORIGINS,
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

    # Persist the session for /api/history. We intentionally don't fail the
    # whole request if the Supabase write hiccups -- the user already has their
    # guidance; losing the history record is a tolerable degradation.
    try:
        sessions.record(
            user_id=user_id,
            input_text=None,
            product=scenario.product,
            parsed_data=scenario.model_dump(mode="json"),
            guidance_result=result.model_dump(mode="json"),
            message=message,
            source=source,
        )
    except Exception:  # noqa: BLE001 - intentional broad catch (write is best-effort)
        pass

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
def history(user_id: str = DEMO_USER, limit: int = 20) -> list[HistorySession]:
    """Return a user's past guidance sessions, newest first.

    Reads from the Supabase 'sessions' table. The frontend passes the user_id
    it received from /api/auth/google as a query param; the backend trusts that
    string and filters by it (see the Phase 2 architecture notes).
    """
    rows = sessions.recent_for_user(user_id, limit=limit)
    return [
        HistorySession(
            id=row["id"],
            createdAt=row["created_at"],
            scenario=row["parsed_data"],
            guidance=row["guidance_result"],
            message=row["message"],
        )
        for row in rows
    ]


# --------------------------------------------------------------------------- #
# Auth role — Google sign-in endpoint
# --------------------------------------------------------------------------- #
def _verify_google_token(token: str, audience: str) -> dict:
    """Verify a Google ID token and return its claims.

    Thin wrapper around google-auth's verify_oauth2_token so tests can stub one
    function (``main._verify_google_token``) instead of reaching into the
    google.oauth2 module. Verifies the JWT signature against Google's public
    keys, the issuer, the audience (must equal ``audience``), and the expiry.
    """
    return google_id_token.verify_oauth2_token(
        token, google_requests.Request(), audience
    )


@app.post("/api/auth/google", response_model=AuthUser)
def auth_google(req: GoogleAuthRequest) -> AuthUser:
    """Sign a user in from a Google ID token and store their session.

    Strictly verifies the ID token via google-auth (signature, issuer,
    audience, expiry), refuses unverified emails, then records the session.
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not client_id:
        raise HTTPException(
            status_code=500,
            detail="Google sign-in is not configured on the server.",
        )

    try:
        claims = _verify_google_token(req.credential, client_id)
    except ValueError as exc:
        # google-auth raises ValueError for any verification failure:
        # bad signature, wrong audience, expired, malformed.
        raise HTTPException(status_code=401, detail="Invalid Google credential.") from exc

    email = claims.get("email")
    if not email:
        raise HTTPException(status_code=401, detail="Google credential is missing an email.")
    if claims.get("email_verified") is False:
        raise HTTPException(status_code=401, detail="Google email is not verified.")

    # `sub` is Google's stable per-user id; fall back to the email if absent.
    google_id = claims.get("sub") or email
    name = claims.get("name") or email.split("@")[0]

    # Upsert into Supabase so concurrent sign-ins never produce duplicates.
    # The returned userId is the Supabase row id (uuid), not the Google sub.
    try:
        row = users.find_or_create(google_id=google_id, email=email)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Could not reach the user store. Please try again.",
        ) from exc

    return AuthUser(name=name, email=email, userId=row["id"])


# --------------------------------------------------------------------------- #
# Calendar role — endpoints (Phase 3)
# --------------------------------------------------------------------------- #
def _events_to_ics(events: list[dict], product: str) -> str:
    """Render schedule events as an RFC-5545 .ics file.

    Hand-rolled to avoid pulling in the `icalendar` library for ~10 lines of
    work. Each event is a 15-minute reminder (DTSTART + 15min) so calendar
    apps render it as a visible block rather than a 0-duration point.
    """
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//SafeCycle//EN", "CALSCALE:GREGORIAN"]
    for i, e in enumerate(events):
        # `starts_at` is an ISO-8601 string from CalendarEvent.as_dict().
        dt = datetime.fromisoformat(e["starts_at"])
        dt_start = dt.strftime("%Y%m%dT%H%M%SZ")
        dt_end = (dt + timedelta(minutes=15)).strftime("%Y%m%dT%H%M%SZ")
        lines += [
            "BEGIN:VEVENT",
            f"UID:safecycle-{product}-{i}-{dt_start}@safecycle.app",
            f"DTSTAMP:{dt_start}",
            f"DTSTART:{dt_start}",
            f"DTEND:{dt_end}",
            f"SUMMARY:{e['summary']}",
            f"DESCRIPTION:{e['description']}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    # ICS uses CRLF line endings.
    return "\r\n".join(lines) + "\r\n"


@app.post("/api/calendar/generate", response_model=CalendarResponse)
def calendar_generate(req: CalendarGenerateRequest) -> CalendarResponse:
    """Generate and persist a contraception schedule for the user.

    Overwrites any existing schedule for the same user_id (one row per user;
    see the calendars unique constraint). Returns the freshly-stored row.
    """
    try:
        start = date.fromisoformat(req.start_date)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail="start_date must be in YYYY-MM-DD format.",
        ) from exc

    events = calendar_generator.generate(req.product, start, hour=req.hour)
    schedule_data = [e.as_dict() for e in events]

    try:
        row = calendars.upsert_for_user(
            user_id=req.user_id,
            product=req.product,
            start_date=req.start_date,
            hour=req.hour,
            schedule_data=schedule_data,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=503,
            detail="Could not save the schedule. Please try again.",
        ) from exc

    return CalendarResponse(**row)


@app.get("/api/calendar/{user_id}", response_model=CalendarResponse)
def calendar_get(user_id: str) -> CalendarResponse:
    """Return the user's current schedule, or 404 if they have none."""
    row = calendars.get_for_user(user_id)
    if not row:
        raise HTTPException(status_code=404, detail="No schedule for this user.")
    return CalendarResponse(**row)


@app.get("/api/calendar/{user_id}/ics")
def calendar_ics(user_id: str) -> Response:
    """Return the user's schedule as a downloadable .ics file."""
    row = calendars.get_for_user(user_id)
    if not row:
        raise HTTPException(status_code=404, detail="No schedule for this user.")
    ics = _events_to_ics(row["schedule_data"], row["product"])
    filename = f"safecycle-{row['product']}.ics"
    return Response(
        content=ics,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# --------------------------------------------------------------------------- #
# Chat role -- endpoints
# --------------------------------------------------------------------------- #
def _summarise(text: str, limit: int = 80) -> str:
    """Cheap, deterministic summary used as the chat title in Profile.

    Trims to first sentence (or `limit` chars). No LLM call -- titles need to
    be stable across replays and we don't want a second Claude round-trip
    just to name the chat.
    """
    t = " ".join(text.split())
    cut = min((t.find(p) for p in (". ", "? ", "! ") if t.find(p) != -1), default=-1)
    if 0 < cut < limit:
        return t[: cut + 1]
    return t[:limit] + ("…" if len(t) > limit else "")


def _row_to_message(row: dict) -> ChatMessage:
    return ChatMessage(
        role=row["role"], content=row["content"], created_at=row.get("created_at")
    )


@app.post("/api/chat/start", response_model=ChatTurnResponse)
def chat_start(req: ChatStartRequest) -> ChatTurnResponse:
    """Open a new chat conversation and return the first assistant turn.

    Creates a chat_sessions row, records the user's first message, asks Claude
    for the next turn, records that too, and returns the full transcript.
    """
    try:
        session = chats.create_session(user_id=req.user_id, summary=_summarise(req.message))
        chats.append_message(session_id=session["id"], role="user", content=req.message)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=503,
            detail="Could not start chat. Please try again.",
        ) from exc

    reply = chat_module.respond(
        messages=[{"role": "user", "content": req.message}],
        client=client,
        model=MODEL,
    )
    try:
        chats.append_message(session_id=session["id"], role="assistant", content=reply)
    except Exception:  # noqa: BLE001 -- the reply is still returned to the user
        pass

    messages = chats.get_messages(session["id"])
    return ChatTurnResponse(
        session_id=session["id"],
        messages=[_row_to_message(m) for m in messages],
        summary=session["summary"],
        complete=False,
    )


@app.post("/api/chat/{session_id}/message", response_model=ChatTurnResponse)
def chat_message(session_id: str, req: ChatMessageRequest) -> ChatTurnResponse:
    """Append the user's next message and return the assistant's reply."""
    session = chats.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="No such chat.")
    if session.get("complete"):
        raise HTTPException(status_code=409, detail="This chat is already complete.")

    try:
        chats.append_message(session_id=session_id, role="user", content=req.content)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=503,
            detail="Could not save your message. Please try again.",
        ) from exc

    history = [
        {"role": m["role"], "content": m["content"]}
        for m in chats.get_messages(session_id)
    ]
    reply = chat_module.respond(messages=history, client=client, model=MODEL)
    try:
        chats.append_message(session_id=session_id, role="assistant", content=reply)
    except Exception:  # noqa: BLE001
        pass

    messages = chats.get_messages(session_id)
    return ChatTurnResponse(
        session_id=session_id,
        messages=[_row_to_message(m) for m in messages],
        summary=session["summary"],
        complete=bool(session.get("complete")),
    )


@app.post("/api/chat/{session_id}/done", response_model=ChatTurnResponse)
def chat_done(session_id: str) -> ChatTurnResponse:
    """Mark the chat complete (user clicked Done). Returns the final state."""
    session = chats.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="No such chat.")
    chats.mark_complete(session_id)
    session = chats.get_session(session_id) or session
    messages = chats.get_messages(session_id)
    return ChatTurnResponse(
        session_id=session_id,
        messages=[_row_to_message(m) for m in messages],
        summary=session["summary"],
        complete=True,
    )


@app.get("/api/chat/{session_id}", response_model=ChatTurnResponse)
def chat_get(session_id: str) -> ChatTurnResponse:
    """Return a saved chat conversation (for the Profile history view)."""
    session = chats.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="No such chat.")
    messages = chats.get_messages(session_id)
    return ChatTurnResponse(
        session_id=session_id,
        messages=[_row_to_message(m) for m in messages],
        summary=session["summary"],
        complete=bool(session.get("complete")),
    )


@app.get("/api/chats", response_model=list[ChatSummary])
def chat_list(user_id: str = DEMO_USER, limit: int = 20) -> list[ChatSummary]:
    """List a user's recent chat conversations, newest activity first."""
    rows = chats.recent_for_user(user_id, limit=limit)
    return [
        ChatSummary(
            id=row["id"],
            summary=row["summary"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            complete=bool(row["complete"]),
        )
        for row in rows
    ]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
