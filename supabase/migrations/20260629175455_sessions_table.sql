-- Phase 2 migration: SafeCycle sessions table.
--
-- One row per /api/guidance call: the user it belongs to, the raw and parsed
-- input, the engine's structured decision, and a timestamp. Powers the history
-- view (GET /api/history) and is the foundation for any future analytics.

create table if not exists public.sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  input_text text,
  product text,
  parsed_data jsonb,
  guidance_result jsonb,
  message text,
  source text not null default 'engine',
  created_at timestamptz not null default now()
);

-- The history query is "most recent N sessions for this user" -- this composite
-- index supports both filtering (user_id) and ordering (created_at desc) in one.
create index if not exists sessions_user_id_created_at_idx
  on public.sessions (user_id, created_at desc);

-- RLS on. No public policies attached, so only the backend's service role
-- (which bypasses RLS) can read/write. The backend filters by user_id manually
-- in code; RLS is here as defense-in-depth.
alter table public.sessions enable row level security;
