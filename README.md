# SafeCycle

Mobile-first web app giving people on hormonal contraception calm,
real-time, **step-by-step** guidance in stressful moments (missed/late pill,
timing error, switching methods).

> SafeCycle surfaces information framed like a smart patient leaflet.
> It is **not a diagnosis, prescription, or medical advice.**

## Status

**Step 1 — Frontend** is in place. The medical logic and all integrations
(Supabase, Claude, Google auth) are **stubbed** and clearly marked.

⚠️ The medical content in this build is **placeholder logic only and has not
been clinically reviewed.** Do not present it as real guidance.

## Project structure

```
safecycle/
├── frontend/          # Mobile-first SPA (HTML, CSS tokens, vanilla JS) — DONE
│   ├── index.html
│   ├── manifest.webmanifest, service-worker.js   # PWA shell
│   ├── css/           # tokens.css = ONLY file to swap for Stitch tokens
│   ├── js/            # router, state, stubbed api, views/, data/
│   └── assets/icons/  # placeholder PWA icons
├── backend/           # FastAPI server — Step 2 (not yet built)
├── supabase/          # Supabase CLI project (already linked)
├── railway.toml       # Deployment config — Step 12
└── .gitignore
```

## Run locally

The frontend uses ES modules, so serve it over HTTP (not `file://`):

```bash
cd frontend
python -m http.server 5173
# open http://localhost:5173
```

Test on a phone width (375px+) or your browser's device toolbar.

## Design tokens (Stitch)

All visual styling flows from CSS custom properties in
`frontend/css/tokens.css`. The current values are calm, neutral
**placeholders**. To apply Stitch: replace the values in that file's
`:root` block, keeping the variable names. Nothing else needs to change.

## Roadmap

See the build spec. Next: **Step 2 — FastAPI backend skeleton**, then
Supabase integration, AI input parser, and the real clinician-reviewed
logic engine.
