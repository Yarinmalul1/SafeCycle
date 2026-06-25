/* View: Guided questions — one question per screen, adaptive.
   Each question is its own history entry (#/questions?q=N) so the
   browser/back button naturally returns to the previous question
   for editing, per spec. */
import { state } from "../state.js";
import { router } from "../router.js";
import { getQuestions } from "../data/questions.js";

export const QuestionsView = {
  render(params) {
    const s = state.session;

    // Guard: must have a method to ask questions.
    if (!s.method) {
      router.go("/method");
      return { title: "", html: "", showBack: false };
    }

    const questions = getQuestions(s);
    const total = questions.length;
    let idx = parseInt(params.q ?? s.questionIndex ?? 0, 10);
    if (isNaN(idx) || idx < 0) idx = 0;
    if (idx > total - 1) idx = total - 1;

    state.update({ questionIndex: idx });

    const q = questions[idx];
    const pct = Math.round(((idx + 1) / total) * 100);
    const current = s.answers[q.id];

    return {
      title: "A few questions",
      html: `
        <div class="progress">
          <span class="progress__label">Question ${idx + 1} of ${total}</span>
          <div class="progress__track">
            <div class="progress__bar" style="width:${pct}%"></div>
          </div>
        </div>

        <div class="stack" style="gap:var(--space-2);margin-top:var(--space-3)">
          <h1 class="subtitle">${q.text}</h1>
          ${q.help ? `<p class="muted">${q.help}</p>` : ""}
        </div>

        <div class="stack" id="answers" style="margin-top:var(--space-2)">
          ${q.options
            .map(
              (o) => `
            <button class="choice" data-value="${o.value}"
              aria-pressed="${current === o.value}">
              <span class="choice__body">
                <span class="choice__title">${o.label}</span>
              </span>
            </button>`
            )
            .join("")}
        </div>
      `,
      onMount(el) {
        el.querySelectorAll("[data-value]").forEach((btn) =>
          btn.addEventListener("click", () => {
            state.setAnswer(q.id, btn.dataset.value);

            if (idx + 1 < total) {
              router.go(`/questions?q=${idx + 1}`);
            } else {
              router.go("/result");
            }
          })
        );
      },
    };
  },
};
