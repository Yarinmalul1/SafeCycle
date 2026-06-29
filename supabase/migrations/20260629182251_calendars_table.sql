-- Phase 3 migration: SafeCycle calendars table.
--
-- One row per user (unique constraint on user_id): the user's *current*
-- generated schedule. Regenerating overwrites the row via upsert. Storing
-- the materialised schedule_data (jsonb) lets the frontend render and export
-- without re-running the generator.

create table if not exists public.calendars (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null unique references public.users(id) on delete cascade,
  product text not null,
  start_date date not null,
  hour integer not null default 9 check (hour between 0 and 23),
  schedule_data jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- RLS on. No public policies; service role bypasses. Defense-in-depth.
alter table public.calendars enable row level security;
