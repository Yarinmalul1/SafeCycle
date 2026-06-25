/* SafeCycle — API client (STUBBED for Step 1).
   ------------------------------------------------------------
   Every function here returns mock data so the frontend runs with
   NO backend, NO secrets. In later steps these become real fetch()
   calls to the FastAPI backend (/api/*) which talks to the logic
   engine, Claude, and Supabase.

   Search for "STUB" to find what gets replaced. */

import { runEngine } from "./data/questions.js";

const FAKE_LATENCY = 450; // ms — mimic a network round-trip for realistic UI

const delay = (ms) => new Promise((r) => setTimeout(r, ms));

export const api = {
  /**
   * STUB — Input parser (Claude).
   * Real version: POST /api/parse { text } -> { method, hoursLate, ... }
   * For now we do naive keyword sniffing just so the UI can pre-fill.
   */
  async parseInput(text) {
    await delay(FAKE_LATENCY);
    const t = (text || "").toLowerCase();
    let method = null;
    if (/\bpill|pack|tablet\b/.test(t)) method = "pill";
    else if (/\bring|nuvaring\b/.test(t)) method = "ring";
    else if (/\bpatch\b/.test(t)) method = "patch";
    return {
      method,
      missedCount: /\btwo|2\b/.test(t) ? 2 : /\bone|1|a pill\b/.test(t) ? 1 : null,
      // confidence + clarifying question would come from Claude
      clarifyingQuestion: null,
      _stub: true,
    };
  },

  /**
   * STUB — Logic engine + answer phraser.
   * Real version: POST /api/guidance { method, product, answers }
   * -> deterministic engine result, phrased by Claude.
   * Here we call a local conservative stub engine.
   */
  async getGuidance(session) {
    await delay(FAKE_LATENCY);
    return runEngine(session);
  },

  /**
   * STUB — Session history (Supabase, logged-in only).
   * Real version: GET /api/history (auth required).
   */
  async getHistory() {
    await delay(FAKE_LATENCY);
    return []; // empty until auth + DB are wired
  },

  /** STUB — Save a result (Supabase). */
  async saveSession(_session) {
    await delay(FAKE_LATENCY);
    return { ok: true, _stub: true };
  },

  /** STUB — Google OAuth via Supabase. */
  async signInWithGoogle() {
    await delay(FAKE_LATENCY);
    return { ok: false, _stub: true, reason: "Auth is wired in a later step." };
  },
};
