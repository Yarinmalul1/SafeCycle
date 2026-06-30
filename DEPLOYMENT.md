# SafeCycle — Deployment

Records the manual Railway setup as it currently stands. Update this file
whenever the topology, services, env vars, or branch mappings change.

## Topology

```
+---------------------+         +---------------------+
| Frontend (static)   |  fetch  | Backend (FastAPI)   |
| serve.js / Railway  | ──────▶ | uvicorn / Railway   |
+---------------------+         +─────────┬───────────+
                                          │
                                          ▼
                                    +─────────────+
                                    |  Supabase   |
                                    |  (Postgres) |
                                    +─────────────+
```

## Environments → branches → URLs

| Environment | Git branch | Frontend URL                                                     | Backend URL                                                     |
|-------------|------------|------------------------------------------------------------------|-----------------------------------------------------------------|
| Staging     | `dev`      | https://frontend-staging-staging-a212.up.railway.app             | https://backend-staging-staging-64b6.up.railway.app             |
| Production  | `main`     | (provisioned when promoted)                                      | (provisioned when promoted)                                     |

Each Railway service is wired to its branch — pushes to `dev` rebuild the
staging services automatically; `main` triggers production rebuilds.

## Services

### Backend (`backend-staging`)
- **Type:** Web service, FastAPI + Uvicorn.
- **Source:** `safecycle-backend/` directory in this repo.
- **Build command:** `pip install -r requirements.txt`
- **Start command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Public port:** assigned by Railway via `$PORT`.

### Frontend (`frontend-staging`)
- **Type:** Static site.
- **Source:** `frontend/` directory in this repo.
- **Build / Start commands:** blank (static files served directly).
- **Public port:** `8080`.

## Environment variables (backend)

Injected via the Railway **Variables** tab on `backend-staging` (and the
production sibling once promoted). Never committed to the repo.

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Claude calls (input parser, answer phraser, fallback, chat). |
| `ANTHROPIC_MODEL`   | Optional override. Default in code is `claude-opus-4-7`. |
| `SUPABASE_URL`      | Supabase project URL. |
| `SUPABASE_SERVICE_ROLE_KEY` | Service-role key used by `db/users.py:_get_client`. Bypasses RLS; backend filters by `user_id` in code. |
| `GOOGLE_CLIENT_ID`  | OAuth Client ID. Audience strictly validated by `google-auth` for every sign-in token. |
| `SAFECYCLE_EXTRA_CORS_ORIGINS` | Optional, comma-separated. Appended to the default CORS allow-list at startup so new hosts (PR previews, prod) can be added without a code change. |

## CORS allow-list

Maintained in `safecycle-backend/main.py`. Origins compared byte-for-byte
by the browser — no trailing slashes.

- `http://localhost:5500`
- `http://127.0.0.1:5500`
- `https://frontend-staging-staging-a212.up.railway.app`
- plus anything in `SAFECYCLE_EXTRA_CORS_ORIGINS`

## Frontend API base resolution

`frontend/js/api.js` `defaultApiBase()`:

1. `window.SAFECYCLE_API_BASE` if set in `index.html` before `api.js` loads.
2. Hostname match: staging frontend → staging backend.
3. Fallback: `http://localhost:8000`.

Add a new mapping here whenever a new public frontend service is created.

## Google OAuth

Configured in the Google Cloud Console for the SafeCycle OAuth client:

- **Authorized JavaScript origins:** `http://localhost:5500` and
  `https://frontend-staging-staging-a212.up.railway.app`.
- **Authorized redirect URIs:** the backend's `/api/auth/google` callback.
- **Scopes:** `openid email profile` (sign-in) + `calendar.events` (added
  on demand by the in-app "Add to Google Calendar" button, separate popup).

## Supabase

Migrations live in `supabase/migrations/`. Apply with:

```sh
supabase db push --linked
```

Currently applied (in order):

1. `0001_users_table.sql`
2. `20260629175455_sessions_table.sql`
3. `20260629182251_calendars_table.sql`
4. `20260630120000_chats_tables.sql`

## Local development

```sh
# Backend
cd safecycle-backend
python -m venv .venv && .venv/Scripts/activate    # or source .venv/bin/activate
pip install -r requirements.txt
python main.py                                    # serves :8000

# Frontend (separate terminal)
cd frontend
node serve.js                                     # serves :5500
```

Open http://localhost:5500.
