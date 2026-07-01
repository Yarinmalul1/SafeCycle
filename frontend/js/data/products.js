/* SafeCycle - product catalog (STUB / partial seed).
   ------------------------------------------------------------
   ⚠️  This is a small, illustrative subset - NOT a complete or
   clinically-reviewed catalog. The real catalog (30+ pills + ring
   + patch, each with its own rules) lives in Supabase and is seeded
   in the Supabase step. Each product needs a clinician-reviewed
   rule set before going live.

   `type`:  "combined" (estrogen+progestogen) | "progestogen-only" (POP)
   `userExplainer`: plain-language leaflet line shown to the user. */

// `icon` values are Material Symbols Outlined ligature names (Stitch set).
export const METHODS = [
  { id: "pill", label: "Pill", icon: "medication", desc: "Daily oral contraceptive" },
  { id: "ring", label: "Ring", icon: "radio_button_unchecked", desc: "Vaginal ring" },
  { id: "patch", label: "Patch", icon: "layers", desc: "Skin patch" },
  {
    id: "unknown",
    label: "I don't know",
    icon: "question_mark",
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

  // ---- Progestogen-only pills (POP) - different, stricter timing rules ----
  { id: "cerazette", name: "Cerazette (desogestrel)", type: "progestogen-only", regimen: "continuous", userExplainer: "Taken every day, no break. 12-hour window." },
  { id: "noriday", name: "Noriday (norethisterone)", type: "progestogen-only", regimen: "continuous", userExplainer: "Taken every day, no break. 3-hour window." },
  { id: "hana", name: "Hana / Lovima (desogestrel)", type: "progestogen-only", regimen: "continuous", userExplainer: "Taken every day, no break. 12-hour window." },

  // Always-available conservative fallback
  { id: "unknown-pill", name: "I don't know my pill", type: "unknown", regimen: "unknown", userExplainer: "We'll route you to the safest, most cautious guidance." },
];

// ---- Non-pill methods -----------------------------------------------------
// Users on the ring or the patch previously had no product picker at all, so
// state.session.product stayed null and /api/guidance 422'd on the missing
// product. The lists below give each non-pill method a small, real choice
// set so a product id is always sent to the backend.
//
// Product ids match the backend product_catalog keys (lowercase, single
// token) so the engine + fallback route the scenario to the right family.

export const RING_OPTIONS = [
  {
    id: "nuvaring",
    name: "NuvaRing",
    type: "ring",
    regimen: "21+7",
    userExplainer: "In for 3 weeks, out for the 4th, then start a new one.",
  },
];

export const PATCH_OPTIONS = [
  {
    id: "evra",
    name: "Evra",
    type: "patch",
    regimen: "3 weekly + 1 patch-free",
    userExplainer: "Apply a new patch each week for 3 weeks, then 1 patch-free week.",
  },
  {
    id: "xulane",
    name: "Xulane",
    type: "patch",
    regimen: "3 weekly + 1 patch-free",
    userExplainer: "Generic of Evra. Same weekly regimen with 1 patch-free week.",
  },
  {
    id: "twirla",
    name: "Twirla",
    type: "patch",
    regimen: "3 weekly + 1 patch-free",
    userExplainer: "Levonorgestrel patch. Weekly, with 1 patch-free week after 3.",
  },
];

// When a user picks "I don't know" method, we still send a product id so the
// backend can respond. The id doesn't match any known product, so the engine
// returns UNKNOWN and the Claude fallback prompt takes over with sourced
// safe defaults - the intended behaviour for an unspecified method.
export const UNKNOWN_METHOD_PRODUCT = {
  id: "unspecified",
  name: "Unspecified method",
  type: "unknown",
  regimen: "unknown",
  userExplainer: "We'll use the safest, most cautious guidance.",
};

export function findProduct(id) {
  return (
    PILLS.find((p) => p.id === id) ||
    RING_OPTIONS.find((p) => p.id === id) ||
    PATCH_OPTIONS.find((p) => p.id === id) ||
    (UNKNOWN_METHOD_PRODUCT.id === id ? UNKNOWN_METHOD_PRODUCT : null)
  );
}

export function searchPills(query) {
  const q = (query || "").trim().toLowerCase();
  if (!q) return PILLS;
  return PILLS.filter((p) => p.name.toLowerCase().includes(q));
}

// Returns the option list for a non-pill method, or [] if the method has no
// picker (e.g. an unrecognised method id).
export function productsForMethod(methodId) {
  if (methodId === "ring") return RING_OPTIONS;
  if (methodId === "patch") return PATCH_OPTIONS;
  return [];
}
