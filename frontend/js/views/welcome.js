/* View: Welcome / Landing (the first screen, per Stitch "Welcome").
   Brand hero + "Start privately" → entry, "Learn how it works" → info. */
import { state } from "../state.js";
import { router } from "../router.js";

const TRUST = [
  {
    icon: "security",
    title: "No accounts",
    desc: "We don't require names, emails, or phone numbers to help you.",
  },
  {
    icon: "verified_user",
    title: "Clinical logic",
    desc: "Built on medical guidelines for accurate, method-specific guidance.",
  },
  {
    icon: "favorite",
    title: "Empathetic care",
    desc: "Calm, judgment-free support designed to keep you informed.",
  },
];

export const WelcomeView = {
  render() {
    return {
      title: "SafeCycle",
      html: `
        <div class="welcome">
          <span class="hero-badge">
            <span class="material-symbols-outlined" aria-hidden="true">lock</span>
            Always private
          </span>

          <h1 class="title welcome__title">Welcome to your private guidance space</h1>
          <p class="subtitle welcome__tagline">Where clarity meets privacy.</p>
          <p class="lead">
            Calm, step-by-step support for missed pills, late pills, timing
            mistakes, or switching methods — without judgment, pressure, or
            sign-up.
          </p>

          <div class="stack" style="margin-top:var(--space-2)">
            <button id="welcome-start" class="btn btn--primary btn--block btn--lg">
              Start privately
            </button>
            <button id="welcome-learn" class="btn btn--secondary btn--block">
              Learn how SafeCycle works
            </button>
          </div>

          <div class="bento">
            ${TRUST.map(
              (t) => `
              <div class="bento__card">
                <span class="material-symbols-outlined bento__icon" aria-hidden="true">${t.icon}</span>
                <h3 class="bento__title">${t.title}</h3>
                <p class="bento__desc">${t.desc}</p>
              </div>`
            ).join("")}
          </div>

          <div class="spacer"></div>
          <p class="disclaimer">Private by design. Not a diagnosis or prescription.</p>
        </div>
      `,
      onMount(el) {
        el.querySelector("#welcome-start").addEventListener("click", () => {
          state.reset();
          router.go("/entry");
        });
        el.querySelector("#welcome-learn").addEventListener("click", () =>
          router.go("/info")
        );
      },
    };
  },
};
