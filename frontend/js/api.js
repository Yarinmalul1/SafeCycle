/* SafeCycle - API client (STUBBED for Step 1).
   ------------------------------------------------------------
   Every function here returns mock data so the frontend runs with
   NO backend, NO secrets. In later steps these become real fetch()
   calls to the FastAPI backend (/api/*) which talks to the logic
   engine, Claude, and Supabase.

   Search for "STUB" to find what gets replaced. */

import { runEngine } from "./data/questions.js";

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
// TODO: replace with the real Google OAuth Client ID for this project.
const GOOGLE_CLIENT_ID =
  (typeof window !== "undefined" && window.SAFECYCLE_GOOGLE_CLIENT_ID) ||
  "YOUR_GOOGLE_OAUTH_CLIENT_ID.apps.googleusercontent.com";
const GSI_SRC = "https://accounts.google.com/gsi/client";

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

/** Prompt the user with Google sign-in and resolve with the ID token (JWT). */
async function getGoogleCredential() {
  await loadGsi();
  return new Promise((resolve, reject) => {
    window.google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: (response) => {
        if (response && response.credential) resolve(response.credential);
        else reject(new Error("Google sign-in was cancelled."));
      },
    });
    window.google.accounts.id.prompt((notification) => {
      // If the One Tap prompt can't be shown or the user dismisses it, reject.
      // (Harmless if it fires after `callback` already resolved.)
      if (
        notification.isNotDisplayed() ||
        notification.isSkippedMoment() ||
        notification.isDismissedMoment()
      ) {
        reject(new Error("Google sign-in didn't complete. Please try again."));
      }
    });
  });
}

export const api = {
  /**
   * Input parser (Claude, via the backend).
   * POST /api/parse-input { userInput } -> ParsedScenario
   *   { product, hoursLate, pillsMissed, cycleWeek, unprotectedSex,
   *     confidence, clarifyingQuestion }
   * The Home view only needs a `method` hint to pre-fill the next step; every
   * product the backend knows about today is a pill, so a detected product
   * implies the pill flow. (Full response mapping lives in the adapters below.)
   */
  async parseInput(text) {
    const parsed = await request("/api/parse-input", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ userInput: text }),
    });
    return {
      ...parsed,
      method: parsed.product ? "pill" : null,
    };
  },

  /**
   * Logic engine + answer phraser (via the backend).
   * POST /api/guidance <ParsedScenario> -> GuidanceResponse { guidance, message }
   *
   * The backend speaks `ParsedScenario` in and `GuidanceResponse` out, while the
   * Result view renders our own session/result shapes. We translate on the way
   * in and out (these inline maps get pulled into named adapters in a later
   * commit).
   */
  async getGuidance(session) {
    const a = session.answers || {};
    const HOURS = { "<24": 12, "24-48": 36, ">48": 72, "<48": 24 };
    const WEEK = { week1: 1, week2: 2, week3: 3 };
    const MISSED = { "1": 1, "2+": 2, "0": 0 };

    const parsed = {
      product: session.product?.id || null,
      hoursLate: a.hoursLate in HOURS ? HOURS[a.hoursLate] : null,
      pillsMissed: a.missedCount in MISSED ? MISSED[a.missedCount] : null,
      cycleWeek: a.packWeek in WEEK ? WEEK[a.packWeek] : null,
      unprotectedSex: a.redFlags ? a.redFlags === "ubp" : null,
      confidence: 1.0, // these are explicit user selections, not inferred
      clarifyingQuestion: null,
    };

    const resp = await request("/api/guidance", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(parsed),
    });

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
  },

  /**
   * Session history (via the backend).
   * GET /api/history -> HistorySession[] { id, createdAt, scenario, guidance, message }
   * Mapped into the compact shape the Profile list renders.
   */
  async getHistory() {
    const sessions = await request("/api/history");
    return sessions.map((s) => ({
      id: s.id,
      headline: s.guidance?.summary || s.message,
      date: new Date(s.createdAt).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
      product: s.scenario?.product || "Your method",
    }));
  },

  /** STUB - Save a result (Supabase). */
  async saveSession(_session) {
    await delay(FAKE_LATENCY);
    return { ok: true, _stub: true };
  },

  /**
   * Google sign-in.
   * Prompts Google Identity Services for an ID token, then verifies it with
   * the backend (POST /api/auth/google { credential }) which returns the
   * authenticated user profile. The caller stores the returned user as the
   * session. Returns { ok, user } on success or { ok:false, reason } so the
   * views can show a toast.
   */
  async signInWithGoogle() {
    let credential;
    try {
      credential = await getGoogleCredential();
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
};
