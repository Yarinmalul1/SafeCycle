/* View: Profile — sign-in (Google) and account actions.
   Auth is stubbed until Supabase Google OAuth is wired in a later step. */
import { state } from "../state.js";
import { router } from "../router.js";
import { api } from "../api.js";
import { googleButton, escapeHtml } from "../util.js";

export const ProfileView = {
  render() {
    const user = state.user;

    if (!user) {
      return {
        title: "Profile",
        html: `
          <div class="stack" style="gap:var(--space-2)">
            <h1 class="title">Your profile</h1>
            <p class="muted">SafeCycle works with no account. Sign in only if
              you'd like to save your answers and revisit them later.</p>
          </div>

          <div class="card stack" style="align-items:center;text-align:center;gap:var(--space-3)">
            <span class="material-symbols-outlined" aria-hidden="true"
              style="font-size:48px;color:var(--color-primary)">account_circle</span>
            <div>
              <strong>Save your guidance privately</strong>
              <p class="muted" style="margin-top:var(--space-1)">
                Your history stays private to you. No data selling, ever.
              </p>
            </div>
            ${googleButton("profile-google")}
          </div>

          <p class="subtle" style="text-align:center">
            Signing in is optional and never required to get guidance.
          </p>
        `,
        onMount(el) {
          el.querySelector("#profile-google").addEventListener("click", async () => {
            const res = await api.signInWithGoogle();
            if (!res.ok) alert(res.reason || "Sign-in is coming soon.");
          });
        },
      };
    }

    // Signed-in state
    return {
      title: "Profile",
      html: `
        <div class="stack" style="gap:var(--space-2)">
          <h1 class="title">Your profile</h1>
        </div>
        <div class="card">
          <strong>${escapeHtml(user.name || "Signed in")}</strong>
          <p class="muted">${escapeHtml(user.email || "")}</p>
        </div>
        <div class="stack">
          <button id="profile-history" class="btn btn--secondary btn--block">
            View saved answers
          </button>
          <button id="profile-signout" class="btn btn--ghost btn--block">
            Sign out
          </button>
        </div>
      `,
      onMount(el) {
        el.querySelector("#profile-history").addEventListener("click", () =>
          router.go("/history")
        );
        el.querySelector("#profile-signout").addEventListener("click", () => {
          state.setUser(null);
          router.go("/profile");
        });
      },
    };
  },
};
