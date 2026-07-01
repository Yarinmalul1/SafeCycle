/* View: Home / Entry */
import { state } from "../state.js";
import { router } from "../router.js";
import { api } from "../api.js";
import { openEscalation } from "../escalation.js";
import { showFieldError, clearFieldError } from "../util.js";

// `icon` values are Material Symbols Outlined ligature names (Stitch set).
const SITUATIONS = [
  { id: "missed-pill", icon: "event_busy", title: "I missed a pill", desc: "Forgot one or more active pills" },
  { id: "late-dose", icon: "schedule", title: "I'm late taking it", desc: "Took it late, or not sure how late" },
  { id: "switching", icon: "published_with_changes", title: "I'm switching methods", desc: "Changing pill, ring, or patch" },
];

export const HomeView = {
  render() {
    return {
      title: "SafeCycle",
      html: `
        <div class="stack" style="gap:var(--space-2)">
          <h1 class="title">What happened?</h1>
          <p class="lead">Tell us in your own words, and we'll walk you
            through what to do - one step at a time.</p>
        </div>

        <div class="field" style="margin-top:var(--space-2)">
          <label class="sr-only" for="home-input">Tell us what happened</label>
          <textarea id="home-input" class="textarea"
            placeholder="e.g. I forgot my pill yesterday and took two today…"></textarea>
          <p id="home-error" class="field-error" role="alert" hidden></p>
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
        const errorEl = el.querySelector("#home-error");
        input.value = state.session.rawInput || "";

        input.addEventListener("input", () => clearFieldError(input, errorEl));

        // Free text -> open an LLM chat conversation. Situation buttons
        // (below) still drive the structured Q&A flow; only the textbox
        // opens chat, per spec.
        // We don't state.reset() here so the user's previous structured
        // result stays available for Protection status / Latest Q&A cards.
        const proceed = () => {
          const text = input.value.trim();
          if (!text) {
            showFieldError(input, errorEl, "Please describe what happened, or pick an option below.");
            input.focus();
            return;
          }
          state.update({ rawInput: text });
          router.go("/chat?new=1");
        };

        el.querySelector("#home-continue").addEventListener("click", proceed);

        el.querySelectorAll("[data-situation]").forEach((btn) =>
          btn.addEventListener("click", () => {
            state.reset();
            const situation = btn.dataset.situation;
            state.update({ situation });
            // Switching is method-neutral - both from/to methods are asked
            // in /questions itself - so skip the method picker.
            if (situation === "switching") {
              router.go("/questions");
            } else {
              router.go("/method");
            }
          })
        );

        el.querySelector("#home-clinician").addEventListener("click", () =>
          openEscalation()
        );
      },
    };
  },
};
