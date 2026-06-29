/* SafeCycle - guided question flow.
   ============================================================
   Builds the adaptive intake questions shown to the user. The actual
   medical decision-making is a deterministic engine on the BACKEND
   (encoding FSRH / WHO / CDC rules, clinician-reviewed); see
   api.getGuidance. This module only decides *what to ask*.

   Frontend contract used by views:
     getQuestions(session) -> [ { id, text, help?, options:[{value,label}] } ]
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
  } else {
    // Ring / patch / unknown method - minimal conservative branch for now.
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

  // Universal safety screen - feeds the safety filter.
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
