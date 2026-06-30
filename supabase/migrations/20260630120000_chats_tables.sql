-- SafeCycle: chat conversations.
--
-- Free-text questions on /entry open an LLM chat conversation instead of the
-- structured Q&A flow. Each conversation is one chat_sessions row plus N
-- chat_messages rows (one per turn, user + assistant). Profile renders the
-- list from chat_sessions and the full transcript from chat_messages.

create table if not exists public.chat_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  -- Short summary of the conversation, derived from the user's first message.
  -- Used as the list-item title in Profile so users can find a past chat.
  summary text not null default '',
  -- Once the user (or the assistant) marks the chat done, this flips true.
  -- Lets us hide ongoing chats from the history list if we want to.
  complete boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists chat_sessions_user_id_created_at_idx
  on public.chat_sessions (user_id, created_at desc);

create table if not exists public.chat_messages (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.chat_sessions(id) on delete cascade,
  -- "user" or "assistant". Avoid "system" here -- the system prompt is
  -- baked into the backend and never persisted per-message.
  role text not null check (role in ('user', 'assistant')),
  content text not null,
  created_at timestamptz not null default now()
);

-- Reading a conversation is "all messages for this session, oldest first".
create index if not exists chat_messages_session_id_created_at_idx
  on public.chat_messages (session_id, created_at);

-- RLS on. Same defense-in-depth posture as the sessions table: only the
-- backend service role (which bypasses RLS) reads/writes, and the backend
-- filters by user_id manually.
alter table public.chat_sessions enable row level security;
alter table public.chat_messages enable row level security;
