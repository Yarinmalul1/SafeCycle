/* View: Welcome / Landing (the first screen, per Stitch "Welcome").
   Brand hero + required Google sign-in → /entry; "Learn how it works" → info. */
import { state } from "../state.js";
import { router } from "../router.js";
import { api } from "../api.js";
import { toast } from "../toast.js";

const TRUST = [
  {
    icon: "security",
    title: "Private account",
    desc: "Your guidance is private to you and never sold or shared.",
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
            mistakes, or switching methods - without judgment or pressure.
          </p>

          <div class="stack" style="margin-top:var(--space-2)">
            <div id="welcome-google" class="gsi-container"
                 style="display:flex;justify-content:center"></div>
            <button id="welcome-learn" class="btn btn--secondary btn--block">
              Learn how SafeCycle works
            </button>
            <p class="subtle">Sign in keeps your answers private and saved to your account.</p>
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
        el.querySelector("#welcome-learn").addEventListener("click", () =>
          router.go("/info")
        );

        // Mount the official Google sign-in button. The promise resolves when
        // the user actually clicks it and Google returns an ID token; until
        // then this just awaits silently in the background.
        const googleContainer = el.querySelector("#welcome-google");
        api.signInWithGoogle(googleContainer).then((res) => {
          if (res.ok && res.user) {
            state.setUser(res.user);
            state.reset();
            router.go("/entry");
          } else if (res.reason) {
            toast(res.reason);
          }
        });
      },
    };
  },
};
