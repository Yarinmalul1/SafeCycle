/* SafeCycle — product catalog (STUB / partial seed).
   ------------------------------------------------------------
   ⚠️  This is a small, illustrative subset — NOT a complete or
   clinically-reviewed catalog. The real catalog (30+ pills + ring
   + patch, each with its own rules) lives in Supabase and is seeded
   in the Supabase step. Each product needs a clinician-reviewed
   rule set before going live.

   `type`:  "combined" (estrogen+progestogen) | "progestogen-only" (POP)
   `userExplainer`: plain-language leaflet line shown to the user. */

export const METHODS = [
  { id: "pill", label: "Pill", icon: "💊", desc: "Daily oral contraceptive" },
  { id: "ring", label: "Ring", icon: "⭕", desc: "Vaginal ring" },
  { id: "patch", label: "Patch", icon: "🩹", desc: "Skin patch" },
  {
    id: "unknown",
    label: "I don't know",
    icon: "❓",
    desc: "We'll use the safest, most cautious guidance",
  },
];

/* NOTE: brand names below are common examples for UI demonstration.
   Verify spelling, availability, and rules per region before launch. */
export const PILLS = [
  // ---- Combined pills (illustrative subset) ----
  { id: "microgynon", name: "Microgynon 30", type: "combined", regimen: "21+7", userExplainer: "21 active + 7 inactive (or pill-free) days." },
  { id: "rigevidon", name: "Rigevidon", type: "combined", regimen: "21+7", userExplainer: "21 active + 7 inactive days." },
  { id: "yasmin", name: "Yasmin", type: "combined", regimen: "21+7", userExplainer: "21 active + 7 inactive days." },
  { id: "yaz", name: "Yaz", type: "combined", regimen: "24+4", userExplainer: "24 active + 4 inactive days." },
  { id: "marvelon", name: "Marvelon", type: "combined", regimen: "21+7", userExplainer: "21 active + 7 inactive days." },
  { id: "cilest", name: "Cilest", type: "combined", regimen: "21+7", userExplainer: "21 active + 7 inactive days." },
  { id: "loestrin", name: "Loestrin", type: "combined", regimen: "21+7", userExplainer: "21 active + 7 inactive days." },

  // ---- Progestogen-only pills (POP) — different, stricter timing rules ----
  { id: "cerazette", name: "Cerazette (desogestrel)", type: "progestogen-only", regimen: "continuous", userExplainer: "Taken every day, no break. 12-hour window." },
  { id: "noriday", name: "Noriday (norethisterone)", type: "progestogen-only", regimen: "continuous", userExplainer: "Taken every day, no break. 3-hour window." },
  { id: "hana", name: "Hana / Lovima (desogestrel)", type: "progestogen-only", regimen: "continuous", userExplainer: "Taken every day, no break. 12-hour window." },

  // Always-available conservative fallback
  { id: "unknown-pill", name: "I don't know my pill", type: "unknown", regimen: "unknown", userExplainer: "We'll route you to the safest, most cautious guidance." },
];

export function findProduct(id) {
  return PILLS.find((p) => p.id === id) || null;
}

export function searchPills(query) {
  const q = (query || "").trim().toLowerCase();
  if (!q) return PILLS;
  return PILLS.filter((p) => p.name.toLowerCase().includes(q));
}
