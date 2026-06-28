/* SafeCycle - session state store
   Holds the in-progress guidance session (method, product, answers).
   Persists the current draft to sessionStorage so a refresh mid-flow
   doesn't lose the user's place. No PII, no network here. */

const DRAFT_KEY = "safecycle:draft";

function emptySession() {
  return {
    rawInput: "", // free-text the user typed on Home
    situation: null, // quick-card id, if used
    method: null, // "pill" | "ring" | "patch" | "unknown"
    product: null, // { id, name } once chosen
    answers: {}, // questionId -> answerValue
    questionIndex: 0,
    result: null, // populated by the (stubbed) engine
  };
}

const store = {
  session: load() || emptySession(),
  // Stub auth state - wired to Supabase Google OAuth in a later step.
  user: null,
  listeners: new Set(),
};

function load() {
  try {
    const raw = sessionStorage.getItem(DRAFT_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function persist() {
  try {
    sessionStorage.setItem(DRAFT_KEY, JSON.stringify(store.session));
  } catch {
    /* storage may be unavailable (private mode) - fine, keep in memory */
  }
}

export const state = {
  get session() {
    return store.session;
  },
  get user() {
    return store.user;
  },

  /** Merge a patch into the current session and notify listeners. */
  update(patch) {
    Object.assign(store.session, patch);
    persist();
    this.emit();
  },

  setAnswer(questionId, value) {
    store.session.answers[questionId] = value;
    persist();
    this.emit();
  },

  /** Start a brand-new session (e.g. from Home). */
  reset() {
    store.session = emptySession();
    persist();
    this.emit();
  },

  setUser(user) {
    store.user = user;
    this.emit();
  },

  subscribe(fn) {
    store.listeners.add(fn);
    return () => store.listeners.delete(fn);
  },

  emit() {
    store.listeners.forEach((fn) => fn(store.session));
  },
};
