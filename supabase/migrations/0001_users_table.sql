-- Phase 1 migration: SafeCycle users table.
--
-- Stores one row per Google-authenticated SafeCycle account. Subsequent
-- tables (sessions in Phase 2, calendars in Phase 3) will foreign-key on
-- users.id, so this is the foundation for the whole persistence layer.
--
-- How to apply (manual for now -- the project doesn't yet use the Supabase
-- CLI for migrations):
--   1. Open your Supabase dashboard.
--   2. Project -> SQL Editor -> "+ New query".
--   3. Paste this file's contents and click "Run".
--   4. Verify the table exists under Project -> Table Editor.

create table if not exists public.users (
  id uuid primary key default gen_random_uuid(),
  google_id text not null unique,
  email text not null unique,
  created_at timestamptz not null default now()
);

-- Index for the sign-in lookup (find-or-create by Google sub).
create index if not exists users_google_id_idx on public.users (google_id);

-- Row Level Security is ON from day one. With no policies attached, only the
-- service role key can read/write -- which is exactly what the backend uses.
-- Phase 2 will add JWT-based policies so the frontend can read its own user.
alter table public.users enable row level security;
