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
   * STUB - Logic engine + answer phraser.
   * Real version: POST /api/guidance { method, product, answers }
   * -> deterministic engine result, phrased by Claude.
   * Here we call a local conservative stub engine.
   */
  async getGuidance(session) {
    await delay(FAKE_LATENCY);
    return runEngine(session);
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
