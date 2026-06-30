/* SafeCycle - API client.
   ------------------------------------------------------------
   Talks to the FastAPI backend (/api/*), which runs the logic engine,
   Claude, and history. Each method translates between the backend's
   schemas and the shapes the views render (see the shape adapters below).
   /api/guidance persists each call to the sessions table, so saveSession
   is just a UI confirmation -- the row already exists in Supabase. */

// Base URL of the FastAPI backend. Override at runtime by setting
// window.SAFECYCLE_API_BASE before this module loads (e.g. in index.html).
const API_BASE = (typeof window !== "undefined" && window.SAFECYCLE_API_BASE) || "http://localhost:8000";

const FAKE_LATENCY = 450; // ms - mimic a network round-trip for realistic UI

const delay = (ms) => new Promise((r) => setTimeout(r, ms));

/**
 * Shared fetch wrapper. Throws an Error with a user-readable `message` on
 * network failure or any non-2xx response, so callers can surface it (e.g.
 * via a toast) instead of getting a half-parsed body. FastAPI reports errors
 * as { detail }, where detail is either a string (our 422 clarifying
 * questions) or a list of validation errors.
 */
async function request(path, options) {
  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, options);
  } catch {
    throw new Error("Can't reach SafeCycle right now. Check your connection and try again.");
  }

  let body = null;
  try {
    body = await res.json();
  } catch {
    /* empty or non-JSON body - leave body null */
  }

  if (!res.ok) {
    const detail = body && body.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail) && detail[0] && detail[0].msg
        ? detail[0].msg
        : `Something went wrong (${res.status}). Please try again.`;
    throw new Error(message);
  }

  return body;
}

// --------------------------------------------------------------------------- #
// Google Identity Services (GIS) sign-in
// --------------------------------------------------------------------------- #
// Public Google OAuth Client ID for SafeCycle. Safe to commit (it is not a secret;
// the matching client *secret* lives only in the backend's .env). Can be overridden
// at runtime via window.SAFECYCLE_GOOGLE_CLIENT_ID (set before this module loads).
const GOOGLE_CLIENT_ID =
  (typeof window !== "undefined" && window.SAFECYCLE_GOOGLE_CLIENT_ID) ||
  "649046048632-7e134020mfee0pk0l53tfc5rf7tt55f6.apps.googleusercontent.com";
// hl=en forces English in all GIS UI (button labels, error messages) regardless
// of the user's browser locale. Belt-and-braces alongside renderButton's
// locale: "en" option below.
const GSI_SRC = "https://accounts.google.com/gsi/client?hl=en";

let gsiScriptPromise = null;

/** Lazy-load the Google Identity Services client, once. */
function loadGsi() {
  if (gsiScriptPromise) return gsiScriptPromise;
  gsiScriptPromise = new Promise((resolve, reject) => {
    if (window.google && window.google.accounts && window.google.accounts.id) {
      return resolve();
    }
    const s = document.createElement("script");
    s.src = GSI_SRC;
    s.async = true;
    s.defer = true;
    s.onload = () => resolve();
    s.onerror = () => {
      gsiScriptPromise = null; // allow a later retry
      reject(new Error("Couldn't load Google sign-in. Check your connection and try again."));
    };
    document.head.appendChild(s);
  });
  return gsiScriptPromise;
}

// We use GIS's official rendered button (google.accounts.id.renderButton)
// instead of One Tap. The button is far more robust: it always displays, has
// no FedCM dependency, no 24h cooldown after a dismissal, and works in
// incognito. The trade-off is that we cannot trigger sign-in programmatically;
// the user must click the GIS-rendered button itself.

let gsiInitialized = false;
let pendingCredentialResolve = null;

/** Initialise GIS once with a callback that hands ID tokens to whichever
 *  caller is currently waiting (see mountGoogleSignInButton). */
async function ensureGsiInitialized() {
  await loadGsi();
  if (gsiInitialized) return;
  window.google.accounts.id.initialize({
    client_id: GOOGLE_CLIENT_ID,
    callback: (response) => {
      const resolve = pendingCredentialResolve;
      pendingCredentialResolve = null;
      if (resolve && response && response.credential) resolve(response.credential);
    },
  });
  gsiInitialized = true;
}

// Google Calendar scope: needed for adding events. Requested via a separate
// OAuth token-client popup (not the sign-in ID-token flow), so users can grant
// or decline calendar access independently of signing in.
const GCAL_SCOPE = "https://www.googleapis.com/auth/calendar.events";

/** Open the OAuth consent popup for the Calendar scope and resolve with an
 *  access token. The token lives in memory only; it never goes to our backend.
 *
 *  `prompt: "consent"` forces Google to show the consent dialog every time
 *  instead of silently reusing the previous decision. Important after a
 *  denial: without this, Google keeps returning the cached "denied" result
 *  even after the user (or project owner) fixes the consent-screen config. */
async function getCalendarAccessToken() {
  await loadGsi();
  return new Promise((resolve, reject) => {
    const tokenClient = window.google.accounts.oauth2.initTokenClient({
      client_id: GOOGLE_CLIENT_ID,
      scope: GCAL_SCOPE,
      prompt: "consent",
      callback: (response) => {
        if (response.error) {
          // Surface Google's full error payload (error + error_description +
          // error_uri) so the user sees the actionable detail rather than a
          // generic "access_denied" string.
          const parts = [response.error, response.error_description, response.error_uri].filter(Boolean);
          reject(new Error(parts.join(" — ") || "Google sign-in failed."));
        } else {
          resolve(response.access_token);
        }
      },
    });
    tokenClient.requestAccessToken();
  });
}

/** Deterministic Google Calendar event id per (userId, product, time, index).
 *  Google requires base32hex chars (a-v, 0-9) only, 5-1024 chars long. */
function makeEventId(userId, product, startsAt, index) {
  const safe = (s) => String(s).toLowerCase().replace(/[^a-v0-9]/g, "");
  const t = String(startsAt).replace(/[^0-9]/g, "");
  return `safecycle${safe(userId)}${safe(product)}${t}${index}`.slice(0, 1024);
}

/** Render the Sign in with Google button into `containerEl` and return a
 *  promise that resolves with the ID token (JWT) once the user clicks it. */
async function mountGoogleSignInButton(containerEl) {
  await ensureGsiInitialized();
  return new Promise((resolve) => {
    pendingCredentialResolve = resolve;
    // GIS standard button: max width 400px, locale forced to English so the
    // label doesn't switch to the browser locale (e.g. Hebrew on RTL systems).
    window.google.accounts.id.renderButton(containerEl, {
      type: "standard",
      theme: "outline",
      size: "large",
      text: "signin_with",
      shape: "rectangular",
      logo_alignment: "left",
      locale: "en",
      width: Math.min(400, Math.max(280, containerEl.offsetWidth || 360)),
    });
  });
}

// --------------------------------------------------------------------------- #
// Shape adapters
// --------------------------------------------------------------------------- #
// The backend speaks ParsedScenario / GuidanceResponse / HistorySession, while
// the views render our own session/result/history shapes. These translate
// between the two in one place.

/** Backend ParsedScenario -> the hint shape the Home view consumes. Every
 *  product the backend knows about today is a pill, so a detected product
 *  implies the pill flow. */
function adaptParsedScenario(parsed) {
  return {
    ...parsed,
    method: parsed.product ? "pill" : null,
  };
}

/** In-progress session (method/product/answers) -> backend ParsedScenario. */
function sessionToParsedScenario(session) {
  const a = session.answers || {};
  const HOURS = { "<24": 12, "24-48": 36, ">48": 72, "<48": 24 };
  const WEEK = { week1: 1, week2: 2, week3: 3 };
  const MISSED = { "1": 1, "2+": 2, "0": 0 };

  return {
    product: session.product?.id || null,
    hoursLate: a.hoursLate in HOURS ? HOURS[a.hoursLate] : null,
    pillsMissed: a.missedCount in MISSED ? MISSED[a.missedCount] : null,
    cycleWeek: a.packWeek in WEEK ? WEEK[a.packWeek] : null,
    unprotectedSex: a.redFlags ? a.redFlags === "ubp" : null,
    confidence: 1.0, // these are explicit user selections, not inferred
    clarifyingQuestion: null,
  };
}

/** Backend GuidanceResponse -> the result shape the Result view renders. */
function adaptGuidance(resp, session) {
  const g = resp.guidance;
  const status =
    g.riskLevel === "high" ? "danger" : g.riskLevel === "moderate" ? "warn" : "ok";

  const steps = [];
  if (g.takePillNow)
    steps.push({
      primary: true,
      text: "Take the most recent missed or late pill as soon as you can - even if that means two pills in one day.",
    });
  if (g.skipPlaceboBreak)
    steps.push({ text: "Skip the pill-free / placebo break and start your next pack straight away." });
  if (g.useBackup)
    steps.push({ text: `Use condoms (backup) for the next ${g.backupDays || 7} days.` });
  if (g.considerEmergencyContraception)
    steps.push({ text: "You may need emergency contraception - ask a pharmacist as soon as possible." });
  for (const note of g.notes || []) steps.push({ text: note });
  if (!steps.length) steps.push({ primary: true, text: resp.message || g.summary });

  return {
    status,
    statusLabel:
      status === "danger" ? "Seek medical help" : status === "warn" ? "Use backup" : "Likely protected",
    headline: g.summary,
    escalate: g.riskLevel === "high",
    steps,
    backup: { needed: g.useBackup, days: g.backupDays || 7, method: "condoms" },
    message: resp.message,
    disclaimer:
      "This is general information based on common contraceptive guidance - not a diagnosis, prescription, or medical advice. If unsure, contact a clinician.",
    product: session.product?.name || "Your method",
  };
}

/** Backend HistorySession[] -> the compact list shape the Profile view renders. */
function adaptHistory(sessions) {
  return sessions.map((s) => ({
    id: s.id,
    headline: s.guidance?.summary || s.message,
    date: new Date(s.createdAt).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
    product: s.scenario?.product || "Your method",
  }));
}

export const api = {
  /**
   * Input parser (Claude, via the backend).
   * POST /api/parse-input { userInput } -> ParsedScenario
   *   { product, hoursLate, pillsMissed, cycleWeek, unprotectedSex,
   *     confidence, clarifyingQuestion }
   * The Home view only needs a `method` hint to pre-fill the next step (see
   * adaptParsedScenario).
   */
  async parseInput(text) {
    const parsed = await request("/api/parse-input", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ userInput: text }),
    });
    return adaptParsedScenario(parsed);
  },

  /**
   * Logic engine + answer phraser (via the backend).
   * POST /api/guidance?user_id=... <ParsedScenario> -> GuidanceResponse
   * The backend persists each call to the Supabase sessions table under
   * `user_id`, which is why we pass the signed-in user's id through. Without
   * it the row is attributed to "demo-user", whose FK doesn't resolve and
   * the insert is silently dropped.
   */
  async getGuidance(session, userId) {
    const path = userId
      ? `/api/guidance?user_id=${encodeURIComponent(userId)}`
      : "/api/guidance";
    const resp = await request(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(sessionToParsedScenario(session)),
    });
    return adaptGuidance(resp, session);
  },

  /**
   * Product catalog (via the backend).
   * GET /api/products -> ProductInfo[] { name, type, supported, regimen, description }
   * The catalog screen renders these grouped by pill family.
   */
  async getProducts() {
    return await request("/api/products");
  },

  /**
   * Session history (via the backend).
   * GET /api/history?user_id=... -> HistorySession[]; mapped by adaptHistory
   * into the compact shape the Profile list renders. Scoped to the signed-in
   * user via the same user_id used at write time.
   */
  async getHistory(userId) {
    const path = userId
      ? `/api/history?user_id=${encodeURIComponent(userId)}`
      : "/api/history";
    const sessions = await request(path);
    return adaptHistory(sessions);
  },

  /** UI confirmation. The session was already persisted server-side during
   *  the matching getGuidance call, so no extra round-trip is needed. */
  async saveSession(_session) {
    await delay(FAKE_LATENCY);
    return { ok: true };
  },

  /**
   * Google sign-in.
   * Mounts the official Google sign-in button into `containerEl`. When the
   * user clicks it, the resulting ID token is sent to the backend
   * (POST /api/auth/google) which verifies it and returns the user profile.
   * Returns { ok, user } on success or { ok:false, reason } on failure, so
   * the view can show a toast.
   */
  async signInWithGoogle(containerEl) {
    let credential;
    try {
      credential = await mountGoogleSignInButton(containerEl);
    } catch (err) {
      return { ok: false, reason: err.message };
    }
    try {
      const body = await request("/api/auth/google", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ credential }),
      });
      return { ok: true, user: body.user || body };
    } catch (err) {
      return { ok: false, reason: err.message };
    }
  },

  /**
   * Calendar - generate and persist a contraception schedule for the user.
   * Returns the stored row (or { ok: false, reason } on failure).
   */
  async generateCalendar({ userId, product, startDate, hour = 9 }) {
    try {
      const body = await request("/api/calendar/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          product,
          start_date: startDate,
          hour,
        }),
      });
      return { ok: true, calendar: body };
    } catch (err) {
      return { ok: false, reason: err.message };
    }
  },

  /** Trigger a browser download of the user's schedule as an .ics file. */
  downloadCalendarIcs(userId) {
    const url = `${API_BASE}/api/calendar/${encodeURIComponent(userId)}/ics`;
    const a = document.createElement("a");
    a.href = url;
    // The Content-Disposition response header already supplies a filename;
    // setting download here is a hint for browsers that ignore it.
    a.download = `safecycle.ics`;
    document.body.appendChild(a);
    a.click();
    a.remove();
  },

  /**
   * Push events to the signed-in user's Google Calendar.
   * Triggers a separate OAuth consent for the calendar.events scope (the
   * sign-in flow only got `openid email profile`), then POSTs each event to
   * the Calendar v3 API. Event ids are deterministic per (userId, product,
   * starts_at) so re-exports are idempotent: Google returns 409 for events
   * it already has and we count them as already-exported.
   * Returns { ok, added, alreadyPresent, failed } or { ok:false, reason }.
   */
  async exportToGoogleCalendar({ userId, product, events }) {
    let accessToken;
    try {
      accessToken = await getCalendarAccessToken();
    } catch (err) {
      return { ok: false, reason: err.message };
    }
    let added = 0,
      alreadyPresent = 0,
      failed = 0;
    for (let i = 0; i < events.length; i++) {
      const e = events[i];
      const id = makeEventId(userId, product, e.starts_at, i);
      const startsAt = e.starts_at;
      const endsAt = new Date(new Date(startsAt).getTime() + 15 * 60 * 1000).toISOString();
      const res = await fetch(
        "https://www.googleapis.com/calendar/v3/calendars/primary/events",
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${accessToken}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            id,
            summary: e.summary,
            description: e.description,
            start: { dateTime: startsAt, timeZone: "UTC" },
            end: { dateTime: endsAt, timeZone: "UTC" },
          }),
        }
      );
      if (res.ok) added++;
      else if (res.status === 409) alreadyPresent++;
      else failed++;
    }
    return { ok: true, added, alreadyPresent, failed };
  },
};
