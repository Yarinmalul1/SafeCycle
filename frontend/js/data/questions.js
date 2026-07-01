/* SafeCycle - guided question flow.
   ============================================================
   Builds the adaptive intake questions shown to the user. The actual
   medical decision-making is a deterministic engine on the BACKEND
   (encoding FSRH / WHO / CDC / FDA / manufacturer SmPC rules); see
   api.getGuidance and api.getSwitchGuidance. This module only decides
   *what to ask*.

   Frontend contract used by views:
     getQuestions(session) -> [ { id, text, help?, options:[{value,label}] } ]

   Branching:
     - situation === "switching" -> 4-question switching flow (fromMethod,
       toMethod, reason, startWhen). Ignores method / product because the
       user is choosing methods here, not scoping a missed-dose scenario.
     - method === "pill"  -> pill flow (existing).
     - method === "ring"  -> ring flow (existing 48h check + red flags).
     - method === "patch" -> patch flow (new: location, off/overdue duration,
       cause, first-time use).
     - method === "unknown" -> conservative shared branch.
   ============================================================ */

import { findProduct } from "./products.js";

/* Build the adaptive question list from what we know so far.
   Questions are filtered/added based on situation + method + product type. */
export function getQuestions(session) {
  // Switching sits above the method-based branching: neither method nor
  // product is meaningful when the user is choosing between methods.
  if (session.situation === "switching") {
    return switchingQuestions();
  }

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
        { value: "0", label: "None - I'm just unsure" },
      ],
    });

    q.push({
      id: "hoursLate",
      text: "How late are you (since it was due)?",
      options: [
        { value: "<24", label: "Less than 24 hours" },
        { value: "24-48", label: "24-48 hours" },
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
  } else if (session.method === "patch") {
    // Patch-specific flow. Backend rules only act on `hoursLate` (mapped
    // from patchHoursOff) and `pillsMissed` (mapped from patchCause when
    // the user says they never applied one), so patchLocation and
    // patchFirstTime are UX-only for now - they help the user think
    // through their situation without inventing rules the engine isn't
    // clinically reviewed for.
    q.push({
      id: "patchLocation",
      text: "Where is your patch applied?",
      help: "Patches should go on clean, dry skin on the buttock, abdomen, upper outer arm, or upper back - not on breasts or damaged/irritated skin.",
      options: [
        { value: "upper-arm", label: "Upper outer arm" },
        { value: "back", label: "Upper back or shoulder" },
        { value: "abdomen", label: "Lower abdomen (below the belly button)" },
        { value: "buttock", label: "Buttock (outer)" },
        { value: "none", label: "I don't have a patch on right now" },
      ],
    });

    q.push({
      id: "hoursLate",
      text: "How long has the patch been off or overdue for a change?",
      help: "For patches, protection generally holds for a lapse under 48 hours (FSRH Contraceptive Patch guidance / SmPC).",
      options: [
        { value: "<48", label: "Less than 48 hours" },
        { value: ">48", label: "48 hours or more" },
        { value: "unsure", label: "I'm not sure" },
      ],
    });

    q.push({
      id: "patchCause",
      text: "Did the patch come off, or did you take it off / forget it?",
      options: [
        { value: "fell-off", label: "It came off on its own" },
        { value: "removed", label: "I took it off intentionally" },
        { value: "forgot", label: "I forgot to change or replace it" },
        { value: "never-applied", label: "I haven't applied a patch yet" },
      ],
    });

    q.push({
      id: "patchFirstTime",
      text: "Is this your first patch cycle?",
      help: "New patch users may need extra care during the first 7 days of use.",
      options: [
        { value: "first-time", label: "Yes, this is my first time" },
        { value: "experienced", label: "No, I've used the patch before" },
      ],
    });
  } else {
    // Ring / unknown method - conservative shared branch (existing).
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

  // Universal safety screen - feeds the safety filter. Applies to every
  // non-switching flow (missed pill, late dose, ring, patch, unknown).
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

/* Switching flow: four questions, method-neutral. Maps 1:1 to the
   backend's MethodSwitchScenario (fromMethod, toMethod, gapDays) with an
   extra `reason` field that we capture for UX context only. */
function switchingQuestions() {
  const methodOptions = [
    { value: "combined_pill", label: "Combined pill (e.g. Yasmin, Yaz, Microgynon)" },
    { value: "progestogen_only_pill", label: "Mini-pill / POP (e.g. Cerazette, Micronor)" },
    { value: "extended_cycle_pill", label: "Extended-cycle pill (e.g. Seasonique)" },
    { value: "vaginal_ring", label: "Vaginal ring (NuvaRing)" },
    { value: "patch", label: "Skin patch (Evra, Xulane, Twirla)" },
  ];

  return [
    {
      id: "fromMethod",
      text: "What method are you currently using?",
      help: "The method you're switching away from.",
      options: methodOptions,
    },
    {
      id: "toMethod",
      text: "What method do you want to switch to?",
      help: "The new method you're starting.",
      options: methodOptions,
    },
    {
      id: "switchReason",
      text: "Why are you switching?",
      help: "For context - your reason doesn't change the medical steps.",
      options: [
        { value: "side-effects", label: "Side effects" },
        { value: "convenience", label: "Convenience or lifestyle" },
        { value: "cost", label: "Cost or availability" },
        { value: "clinician", label: "My doctor or pharmacist recommended it" },
        { value: "other", label: "Something else" },
      ],
    },
    {
      id: "startWhen",
      text: "When do you want to start the new method?",
      help: "How soon after your last dose of the current method.",
      options: [
        { value: "immediately", label: "Today or tomorrow (no gap)" },
        { value: "soon", label: "In a few days" },
        { value: "next-week", label: "In about a week" },
        { value: "longer", label: "Longer than a week" },
      ],
    },
  ];
}
