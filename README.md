# SafeCycle

Mobile-first web app that gives people on hormonal contraception calm,
real-time, **step-by-step** guidance in stressful moments — a missed or
late pill, a timing mistake, a switch between methods, or a general
question about their contraception.

Guidance is framed like a smart patient leaflet: sourced from published
clinical references (FSRH, WHO MEC/SPR, CDC US MEC/SPR, FDA prescribing
information, and each product's manufacturer SmPC), phrased warmly, and
always disclaimed.

> SafeCycle is **not a diagnosis, prescription, or medical advice.** It
> is a decision-support tool that surfaces information from established
> guidelines and always recommends contacting a clinician when in doubt.

## What the app does

A signed-in user can:

- **Ask in their own words.** The Home screen accepts free text
  ("I forgot my pill yesterday and took two today…"). This opens a
  **multi-turn chat** with a Claude-powered contraception advisor that
  can ask clarifying questions before recommending a course of action.
- **Follow a guided flow.** Alternatively pick one of three situation
  cards — *I missed a pill*, *I'm late taking it*, *I'm switching
  methods* — which walks through a short structured Q&A (method,
  product, pack week, hours late / pills missed, unprotected sex) and
  returns a deterministic result from the rules engine.
- **Get structured guidance.** The Result screen shows a status pill
  ("Likely protected" / "Use backup" / "Seek medical help"), primary
  action, ordered steps, backup-contraception window, EC advice, and a
  short warm summary phrased by Claude.
- **Switch methods safely.** A dedicated switching engine reasons over
  from-method, to-method, gap days, and whether unprotected sex occurred
  during the gap.
- **Browse the catalog.** A read-only reference of supported methods and
  products (combined pills, progestogen-only pills, extended-cycle pills,
  the vaginal ring, and the contraceptive patch) grouped by family with
  plain-language explainers.
- **See a calendar / schedule.** Generate a rolling ~90-day reminder
  schedule for their method (daily pill, ring in-and-out cycle, or weekly
  patch), view it as a month grid, download it as an `.ics` file, or push
  it directly to their Google Calendar.
- **See history.** The Profile screen shows past guidance sessions and
  chat conversations, both scoped privately to the signed-in user.
- **Escalate.** An always-available "Talk to a clinician" overlay links
  to appropriate resources.

## Features (what users see)

| Screen | Route | Purpose |
|---|---|---|
| Welcome | `/` | Brand hero + Google sign-in (required). |
| Home hub | `/home` | 6-card dashboard: Reminders, History, Latest Q&A, Catalog, Info, Calendar. |
| Entry | `/entry` | Free-text box (→ chat) or situation cards (→ structured flow). |
| Method picker | `/method` | Pill / ring / patch / "I don't know" for the structured flow. |
| Questions | `/questions` | Adaptive Q&A: pack week, pills missed, hours late, red flags. |
| Result | `/result` | Status pill, ordered steps, backup card, EC advice, disclaimer. |
| Chat | `/chat` | Multi-turn LLM conversation, persisted per user. |
| Catalog | `/catalog` | Method families + supported products from `/api/products`. |
| Calendar | `/calendar` | Month-grid schedule; generate, `.ics` download, Google Calendar sync. |
| Profile | `/profile` | Signed-in account, past guidance sessions, past chats. |
| Info | `/info` | How SafeCycle works, clinical sources, disclaimers. |

The Welcome and Info screens are public; every other route requires a
signed-in user (enforced by the router).

## Technology

### Frontend — `frontend/`
- Vanilla ES-module SPA — no framework, no bundler.
- Hash-based router (`js/router.js`) with view modules under `js/views/`.
- CSS design tokens layered under `css/tokens.css` → `base.css` →
  `components.css`. Typography: Outfit + Inter. Icons: Material Symbols.
- PWA-ready shell (`manifest.webmanifest`, `service-worker.js`;
  the service worker is currently unregistered in dev so changes ship
  without cache lag — re-enable for offline).
- Google Identity Services for sign-in (rendered official button) and
  a separate `calendar.events` token popup for Google Calendar export.
- Zero-dependency dev server (`serve.js`, Node built-ins only).

### Backend — `safecycle-backend/` (FastAPI + Uvicorn)
- **AI roles** (`ai/`):
  - `input_parser.py` — Claude turns free text into a structured
    `ParsedScenario`.
  - `answer_phraser.py` — warm plain-language phrasing of engine output.
  - `guidance_fallback.py` — structured Claude fallback for products
    the deterministic engine has no rules for.
  - `chat.py` — multi-turn chat advisor with strict sourcing rules.
  - `question_generator.py`, `safety_filter.py`, `history_manager.py`,
    `product_catalog.py`.
- **Logic** (`logic/`):
  - `engine.py` — deterministic missed/late-pill rules for combined pills
    (by pack week), progestogen-only pills (by product-specific window),
    extended-cycle pills, and the vaginal ring.
  - `switching.py` — rules for switching between contraceptive methods.
  - `calendar.py` — schedule generation (daily pill / 21+7 ring / weekly patch).
- **Data access** (`db/`): thin Supabase clients for `users`, `sessions`,
  `calendars`, and `chats`.
- **Auth**: Google ID tokens verified strictly by `google-auth`
  (signature, issuer, audience, expiry) before upserting a Supabase user.
- **Models** (`models.py`): Pydantic v2 schemas for every request and
  response.

### Data layer — Supabase (Postgres)
Migrations in `supabase/migrations/`:
1. `0001_users_table.sql` — SafeCycle accounts (Google-authenticated).
2. `20260629175455_sessions_table.sql` — persisted structured-guidance sessions.
3. `20260629182251_calendars_table.sql` — one schedule per user (unique).
4. `20260630120000_chats_tables.sql` — chat sessions + messages.

RLS is enabled on every table; the backend uses the service-role key and
scopes reads/writes by `user_id` in code.

### External integrations
- **Anthropic Claude** (default: `claude-opus-4-7`) — input parsing,
  chat conversation, fallback guidance, answer phrasing.
- **Google Identity Services** — sign-in.
- **Google Calendar API v3** — one-click schedule export.

### Deployment
- Frontend + backend deployed as two Railway services (staging on `dev`,
  production on `main`) with automatic redeploys on push.
- CORS allow-list is code-controlled with an env-var override
  (`SAFECYCLE_EXTRA_CORS_ORIGINS`) for previews / custom domains.

## How it works

```
┌────────────┐   free text   ┌──────────────┐    JSON     ┌────────────┐
│  Frontend  │──────────────▶│ Input Parser │────────────▶│   Logic    │
│  (SPA)     │               │  (Claude)    │             │  engine    │
└────┬───────┘◀────result────└──────────────┘             └──────┬─────┘
     │                                                            │
     │  situation cards → structured Q&A ──────────────────────────┤
     │                                                            ▼
     │                                                     ┌────────────┐
     │                                                     │   Answer   │
     │◀────────────── warm phrased message ────────────────│  phraser   │
     │                                                     │  (Claude)  │
     ▼                                                     └────────────┘
┌────────────┐                                    unknown  ┌────────────┐
│  Chat mode │◀── multi-turn Claude advisor ──▶           │  Fallback  │
│  (Claude)  │                                             │  (Claude)  │
└────────────┘                                             └────────────┘
     │
     ▼
┌────────────┐
│ Supabase   │  users · sessions · calendars · chats
└────────────┘
```

- The **input parser** only *extracts and structures* what the user said —
  it never gives advice.
- The **logic engine** is deterministic and auditable: no LLM call
  happens between the parsed scenario and the decision, so results
  are reproducible.
- The **answer phraser** rewrites the engine's structured decision as
  warm plain language; the raw structured result is still returned.
- When the engine has no rules for a scenario (unknown brand, or a patch
  scenario today), the **fallback prompt** produces the same structured
  shape via Claude, sourced from the same clinical references.
- The **chat mode** enters when the user types free text — Claude can
  ask clarifying questions across turns before recommending action.

### Key API endpoints
| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness probe. |
| POST | `/api/parse-input` | Free text → `ParsedScenario`. |
| POST | `/api/guidance` | `ParsedScenario` → structured + phrased guidance (persisted). |
| POST | `/api/switch-guidance` | `MethodSwitchScenario` → structured + phrased guidance. |
| POST | `/api/safety-filter` | Deterministic red-flag screen. |
| POST | `/api/ask-question` | Next clarifying question for an in-progress scenario. |
| GET | `/api/products` | Product catalog. |
| GET | `/api/history` | Past guidance sessions for a user. |
| POST | `/api/auth/google` | Verify Google ID token, upsert Supabase user. |
| POST | `/api/calendar/generate` | Generate + persist a schedule. |
| GET | `/api/calendar/{user_id}` | The user's stored schedule. |
| GET | `/api/calendar/{user_id}/ics` | Download the schedule as `.ics`. |
| POST | `/api/chat/start` | Open a new chat conversation. |
| POST | `/api/chat/{id}/message` | Append a turn, get the assistant reply. |
| POST | `/api/chat/{id}/done` | Mark the chat complete. |
| GET | `/api/chat/{id}` | Replay a chat. |
| GET | `/api/chats` | List a user's recent chats. |

## Project structure

```
safecycle/
├── frontend/                     # Vanilla ES-module SPA (mobile-first)
│   ├── index.html                # App shell + per-host API base wiring
│   ├── serve.js                  # Zero-dep static dev server
│   ├── manifest.webmanifest, service-worker.js
│   ├── css/                      # tokens.css → base.css → components.css
│   ├── js/
│   │   ├── app.js, router.js, state.js
│   │   ├── api.js                # Backend client + Google sign-in + Calendar export
│   │   ├── escalation.js, planner.js, toast.js, util.js
│   │   ├── views/                # Welcome, Home, Entry, Method, Questions,
│   │   │                         # Result, Info, Catalog, Calendar, Chat, Profile
│   │   └── data/                 # Static method/question metadata
│   └── assets/                   # Logo + PWA icons
├── safecycle-backend/            # FastAPI backend
│   ├── main.py                   # Route definitions, CORS, model wiring
│   ├── models.py                 # Pydantic schemas
│   ├── ai/                       # Input parser, phraser, fallback, chat, catalog…
│   ├── logic/                    # engine, switching, calendar
│   ├── db/                       # Supabase-backed users/sessions/calendars/chats
│   ├── tests/                    # Pytest suite
│   └── requirements.txt
├── supabase/
│   ├── config.toml
│   └── migrations/               # Applied via `supabase db push --linked`
├── DEPLOYMENT.md                 # Railway topology + env vars + Supabase setup
└── package.json                  # Root-level @supabase/supabase-js pin
```

## Setup and local development

### Prerequisites
- Python 3.11+
- Node 18+
- A Supabase project (schema applied via CLI — see below)
- Anthropic API key
- Google OAuth Client ID (Web application)

### Backend
```sh
cd safecycle-backend
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt

# Create safecycle-backend/.env (never commit):
#   ANTHROPIC_API_KEY=sk-...
#   ANTHROPIC_MODEL=claude-opus-4-7          # optional
#   SUPABASE_URL=https://<project>.supabase.co
#   SUPABASE_SERVICE_ROLE_KEY=...
#   GOOGLE_CLIENT_ID=...apps.googleusercontent.com
#   SAFECYCLE_EXTRA_CORS_ORIGINS=            # optional, comma-separated

python main.py                    # serves http://localhost:8000
```

### Frontend
```sh
cd frontend
node serve.js                     # serves http://localhost:5500
# open http://localhost:5500
```

`frontend/index.html` picks the backend URL by hostname: `localhost` /
`127.0.0.1` → `http://localhost:8000`; deployed frontends map to their
paired Railway backend.

### Database
Apply migrations against the linked Supabase project:
```sh
supabase db push --linked
```

## Testing

Backend has a `pytest` suite under `safecycle-backend/tests/`:
- `test_api_routes.py` — FastAPI route contracts (health, `/api/*`).
- `test_logic_engine.py` — deterministic missed-pill rules per family.
- `test_switching.py` — method-switching engine.
- `test_calendar.py` — schedule generation (pill / ring / patch).
- `test_guidance_fallback.py` — Claude fallback shape + sourcing.
- `test_products.py` — product catalog integrity.

Run:
```sh
cd safecycle-backend
pytest                            # `ANTHROPIC_API_KEY` is stubbed inside the tests
```

No LLM or network calls are made — tests use FastAPI's `TestClient` and
never hit Anthropic, Google, or Supabase.

## Deployment

Live deployments are two Railway services per environment (frontend +
backend), wired to Git branches with automatic redeploys:

- **Staging**: `dev` branch.
- **Production**: `main` branch.

See [`DEPLOYMENT.md`](./DEPLOYMENT.md) for the full topology, the
environment-variable list, the CORS allow-list, the OAuth Console
configuration, and the Supabase migration workflow.

## Design tokens

All visual styling flows from CSS custom properties in
`frontend/css/tokens.css`. To rebrand: replace the values in that file's
`:root` block, keep the variable names. Nothing else needs to change.

## Safety and limits

- SafeCycle covers hormonal contraception only: combined oral
  contraceptives, progestogen-only pills, extended-cycle pills, the
  vaginal ring, and the contraceptive patch. It does **not** cover IUDs,
  implants, injections, or non-hormonal methods.
- All LLM prompts (parser, chat, fallback, phraser) are constrained to
  the same clinical source list — FSRH, WHO MEC/SPR, CDC US MEC/SPR,
  FDA prescribing information, and the manufacturer SmPC.
- The deterministic engine is the authority for supported products; the
  LLM fallback is only used when the engine cannot rule on the scenario
  (unknown brand, or patch scenarios today).
- Every result screen shows a disclaimer and offers escalation to a
  clinician. Emergency-contraception advice is surfaced whenever the
  rules or fallback flag it.
- Data is scoped to the signed-in user: RLS is on in Supabase and the
  backend filters by `user_id` in code.
