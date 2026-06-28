/* View: Home / Entry */
import { state } from "../state.js";
import { router } from "../router.js";
import { api } from "../api.js";
import { openEscalation } from "../escalation.js";

// `icon` values are Material Symbols Outlined ligature names (Stitch set).
const SITUATIONS = [
  { id: "missed-pill", icon: "event_busy", title: "I missed a pill", desc: "Forgot one or more active pills" },
  { id: "late-dose", icon: "schedule", title: "I'm late taking it", desc: "Took it late, or not sure how late" },
  { id: "switching", icon: "published_with_changes", title: "I'm switching methods", desc: "Changing pill, ring, or patch" },
  { id: "unsure", icon: "help_outline", title: "Something else", desc: "Not sure how to describe it" },
];

export const HomeView = {
  render() {
    return {
      title: "SafeCycle",
      html: `
        <div class="stack" style="gap:var(--space-2)">
          <h1 class="title">What happened?</h1>
          <p class="lead">Tell us in your own words, and we'll walk you
            through what to do — one step at a time.</p>
        </div>

        <div class="field" style="margin-top:var(--space-2)">
          <label class="sr-only" for="home-input">Tell us what happened</label>
          <textarea id="home-input" class="textarea"
            placeholder="e.g. I forgot my pill yesterday and took two today…"></textarea>
          <button id="home-continue" class="btn btn--primary btn--block btn--lg">
            Continue
          </button>
        </div>

        <p class="muted" style="text-align:center">or pick what fits</p>

        <div class="stack" id="situations">
          ${SITUATIONS.map(
            (s) => `
            <button class="choice" data-situation="${s.id}">
              <span class="choice__icon material-symbols-outlined" aria-hidden="true">${s.icon}</span>
              <span class="choice__body">
                <span class="choice__title">${s.title}</span>
                <span class="choice__desc">${s.desc}</span>
              </span>
            </button>`
          ).join("")}
        </div>

        <div class="spacer"></div>

        <div class="stack" style="gap:var(--space-3)">
          <button id="home-clinician" class="btn btn--ghost btn--block">
            Talk to a clinician
          </button>
          <p class="trust-line">
            <span class="material-symbols-outlined" aria-hidden="true">lock</span>
            <span>Real guidance based on medical guidelines. Not a diagnosis.
            Private to your account.</span>
          </p>
          <p class="subtle" style="text-align:center">
            <a href="#/profile">Saved answers</a>
            &nbsp;·&nbsp;
            <a href="#/info">How it works & sources</a>
          </p>
        </div>
      `,
      onMount(el) {
        const input = el.querySelector("#home-input");
        input.value = state.session.rawInput || "";

        const proceed = async () => {
          state.reset();
          state.update({ rawInput: input.value.trim() });
          // STUB parse — may pre-fill method to skip a step later.
          if (input.value.trim()) {
            const parsed = await api.parseInput(input.value);
            if (parsed.method) state.update({ method: parsed.method });
          }
          router.go("/method");
        };

        el.querySelector("#home-continue").addEventListener("click", proceed);

        el.querySelectorAll("[data-situation]").forEach((btn) =>
          btn.addEventListener("click", () => {
            state.reset();
            state.update({ situation: btn.dataset.situation });
            router.go("/method");
          })
        );

        el.querySelector("#home-clinician").addEventListener("click", () =>
          openEscalation()
        );
      },
    };
  },
};
