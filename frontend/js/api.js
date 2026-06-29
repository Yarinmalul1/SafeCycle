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
    const res = await fetch(`${API_BASE}/api/parse-input`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ userInput: text }),
    });
    const parsed = await res.json();
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

    const res = await fetch(`${API_BASE}/api/guidance`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(parsed),
    });
    const resp = await res.json();

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
   * STUB - Session history (Supabase, logged-in only).
   * Real version: GET /api/history (auth required).
   */
  async getHistory() {
    await delay(FAKE_LATENCY);
    return []; // empty until auth + DB are wired
  },

  /** STUB - Save a result (Supabase). */
  async saveSession(_session) {
    await delay(FAKE_LATENCY);
    return { ok: true, _stub: true };
  },

  /** STUB - Google OAuth via Supabase.
   * Real version: Supabase Google OAuth → returns the authed profile.
   * For the demo we return a mock signed-in user so the gated flow works. */
  async signInWithGoogle() {
    await delay(FAKE_LATENCY);
    return {
      ok: true,
      _stub: true,
      user: { name: "Sarah Levi", email: "sarah@example.com" },
    };
  },
};
