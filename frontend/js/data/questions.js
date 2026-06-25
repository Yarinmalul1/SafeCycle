/* SafeCycle — guided question flow + STUB logic engine.
   ============================================================
   ⚠️⚠️  NOT CLINICALLY REVIEWED. PLACEHOLDER LOGIC ONLY.  ⚠️⚠️
   The real medical decision-making is a deterministic engine on
   the BACKEND, encoding rules from FSRH / WHO / CDC, reviewed by a
   clinician. The functions below are a small, deliberately
   CONSERVATIVE stub so the frontend flow is demonstrable. They
   must NOT be shipped as medical guidance.

   Frontend contract used by views:
     getQuestions(session) -> [ { id, text, help?, options:[{value,label}] } ]
     runEngine(session)    -> result object (see shape below)
   ============================================================ */

import { findProduct } from "./products.js";

/* Build the adaptive question list from what we know so far.
   Questions are filtered/added based on method + product type. */
export function getQuestions(session) {
  const product = session.product ? findProduct(session.product.id) : null;
  const type = product?.type;

  const q = [];

  if (session.method === "pill") {
    q.push({
      id: "missedCount",
      text: "How many pills did you miss?",
      help: "Count only active (hormone) pills.",
      options: [
        { value: "1", label: "One pill" },
        { value: "2+", label: "Two or more" },
        { value: "0", label: "None — I'm just unsure" },
      ],
    });

    q.push({
      id: "hoursLate",
      text: "How late are you (since it was due)?",
      options: [
        { value: "<24", label: "Less than 24 hours" },
        { value: "24-48", label: "24–48 hours" },
        { value: ">48", label: "More than 48 hours" },
      ],
    });

    // Combined pills care a lot about WHICH week; POPs do not.
    if (type === "combined" || type === "unknown") {
      q.push({
        id: "packWeek",
        text: "Where are you in the pack?",
        help: "Roughly which week of active pills?",
        options: [
          { value: "week1", label: "Week 1 (just started the pack)" },
          { value: "week2", label: "Week 2" },
          { value: "week3", label: "Week 3 (near the break)" },
          { value: "unsure", label: "I'm not sure" },
        ],
      });
    }
  } else {
    // Ring / patch / unknown method — minimal conservative branch for now.
    q.push({
      id: "hoursLate",
      text: "How long has it been out of place / overdue?",
      options: [
        { value: "<48", label: "Less than 48 hours" },
        { value: ">48", label: "More than 48 hours" },
        { value: "unsure", label: "I'm not sure" },
      ],
    });
  }

  // Universal safety screen — feeds the safety filter.
  q.push({
    id: "redFlags",
    text: "Do any of these apply right now?",
    help: "Pick the closest one.",
    options: [
      { value: "none", label: "None of these" },
      { value: "ubp", label: "Unprotected sex in the last few days" },
      { value: "pregnant", label: "I might be pregnant" },
      { value: "symptoms", label: "Severe pain, heavy bleeding, or feeling very unwell" },
    ],
  });

  return q;
}

/* ---- STUB conservative engine ----
   Returns a result the Result view can render directly.
   Statuses: "ok" (green) | "warn" (amber) | "danger" (red).
   When uncertain, escalate. Never invent a reassuring answer. */
export function runEngine(session) {
  const a = session.answers || {};
  const product = session.product ? findProduct(session.product.id) : null;

  const base = {
    _stub: true, // <-- views show a "not clinically reviewed" badge
    product: product?.name || "Your method",
    disclaimer:
      "This is general information based on common contraceptive guidance — not a diagnosis, prescription, or medical advice. If unsure, contact a clinician.",
    escalate: false,
  };

  // 1) Hard safety routing first (mirrors the Safety Filter role).
  if (a.redFlags === "pregnant" || a.redFlags === "symptoms") {
    return {
      ...base,
      status: "danger",
      headline: "Please speak to a clinician now",
      statusLabel: "Seek medical help",
      escalate: true,
      steps: [
        { primary: true, text: "Contact a clinician, pharmacist, or urgent care today." },
        { text: "If you have severe symptoms, seek urgent medical care." },
      ],
      backup: null,
    };
  }

  if (session.method === "unknown" || product?.type === "unknown") {
    return {
      ...base,
      status: "warn",
      headline: "Use backup protection and confirm your method",
      statusLabel: "Use backup",
      steps: [
        { primary: true, text: "Use condoms (backup) until you can confirm your exact product and its rules." },
        { text: "Find your pill name on the pack or leaflet, then start a new check." },
        { text: "If you had unprotected sex recently, ask a pharmacist about emergency contraception." },
      ],
      backup: { needed: true, days: 7, method: "condoms" },
    };
  }

  // 2) Very simplified combined-pill style logic (PLACEHOLDER).
  if (session.method === "pill") {
    const missedMany = a.missedCount === "2+";
    const veryLate = a.hoursLate === ">48";
    const week3 = a.packWeek === "week3";
    const week1 = a.packWeek === "week1";

    if (missedMany || veryLate) {
      return {
        ...base,
        status: "warn",
        headline: "Take action now and use backup",
        statusLabel: "Use backup",
        steps: [
          { primary: true, text: "Take the most recent missed pill as soon as you remember — even if that means two pills in one day." },
          { text: "Keep taking one pill a day at your usual time." },
          { text: "Use condoms (backup) for the next 7 days." },
          week3
            ? { text: "Because you're near the end of the pack, skip the pill-free break and start the next pack straight away." }
            : { text: "Continue your pack as normal." },
          a.redFlags === "ubp"
            ? { text: "You had unprotected sex recently — ask a pharmacist about emergency contraception." }
            : null,
        ].filter(Boolean),
        backup: { needed: true, days: 7, method: "condoms" },
      };
    }

    // One pill, <48h late — typically lower risk for combined pills.
    return {
      ...base,
      status: "ok",
      headline: "You're likely still protected — take it now",
      statusLabel: "Likely protected",
      steps: [
        { primary: true, text: "Take the missed pill as soon as you remember, even if it means two in one day." },
        { text: "Carry on with the rest of the pack at your usual time." },
        { text: "No backup is usually needed for a single pill taken within this window." },
        week1
          ? { text: "Since you're in week 1, if you had unprotected sex recently, ask a pharmacist about emergency contraception." }
          : null,
      ].filter(Boolean),
      backup: { needed: false },
    };
  }

  // 3) Ring / patch — conservative default for now.
  return {
    ...base,
    status: "warn",
    headline: "Use backup and follow up",
    statusLabel: "Use backup",
    steps: [
      { primary: true, text: "Reapply or replace your method as soon as possible." },
      { text: "Use condoms (backup) for the next 7 days." },
      { text: "Check your product leaflet for the exact restart timing, or ask a pharmacist." },
    ],
    backup: { needed: true, days: 7, method: "condoms" },
  };
}
