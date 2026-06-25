/* View: History (logged-in users only). */
import { state } from "../state.js";
import { router } from "../router.js";
import { api } from "../api.js";

export const HistoryView = {
  render() {
    return {
      title: "Your history",
      html: `<div id="history-body"><p class="empty">Loading…</p></div>`,
      async onMount(el) {
        const body = el.querySelector("#history-body");

        if (!state.user) {
          body.innerHTML = `
            <div class="empty">
              <p class="lead">Sign in to save and revisit your answers</p>
              <p class="muted" style="margin-top:var(--space-2)">
                Your history is private to you. No sign-up needed to use SafeCycle.
              </p>
              <button id="hist-signin" class="btn btn--primary"
                style="margin-top:var(--space-4)">Continue with Google</button>
            </div>`;
          body.querySelector("#hist-signin").addEventListener("click", async () => {
            const res = await api.signInWithGoogle();
            if (!res.ok) alert(res.reason || "Sign-in is coming soon.");
          });
          return;
        }

        const sessions = await api.getHistory();
        if (!sessions.length) {
          body.innerHTML = `<div class="empty">
            <p class="lead">No saved answers yet</p>
            <button id="hist-new" class="btn btn--primary"
              style="margin-top:var(--space-4)">Start a check</button>
          </div>`;
          body.querySelector("#hist-new").addEventListener("click", () =>
            router.go("/entry")
          );
          return;
        }

        body.innerHTML = `<div class="list">
          ${sessions
            .map(
              (s) => `
            <button class="list-item" data-id="${s.id}">
              <span class="choice__title">${s.headline}</span>
              <span class="list-item__meta">${s.date} · ${s.product}</span>
            </button>`
            )
            .join("")}
        </div>`;
      },
    };
  },
};
