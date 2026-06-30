/* View: Profile - sign-in (Google), account actions, and saved-answer
   History embedded inline (history comes from the backend; sign-in uses
   Google Identity Services via api.signInWithGoogle). */
import { state } from "../state.js";
import { router } from "../router.js";
import { api } from "../api.js";
import { escapeHtml } from "../util.js";
import { toast } from "../toast.js";

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
                Sign in and your saved answers will appear here. Private to you -
                no data selling, ever.
              </p>
            </div>
            <div id="profile-google" class="gsi-container"
                 style="display:flex;justify-content:center"></div>
          </div>

          <p class="subtle" style="text-align:center">
            Signing in is optional and never required to get guidance.
          </p>
        `,
        onMount(el) {
          const container = el.querySelector("#profile-google");
          api.signInWithGoogle(container).then((res) => {
            if (res.ok && res.user) {
              state.setUser(res.user);
              router.go("/profile");
            } else if (res.reason) {
              toast(res.reason);
            }
          });
        },
      };
    }

    // Signed-in: account card + inline History.
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

        <h2 class="subtitle">Saved answers</h2>
        <div id="profile-history"><p class="empty">Loading…</p></div>

        <h2 class="subtitle" style="margin-top:var(--space-3)">Chat history</h2>
        <div id="profile-chats"><p class="empty">Loading…</p></div>

        <div class="stack" style="margin-top:var(--space-3)">
          <button id="profile-calendar" class="btn btn--secondary btn--block">
            <span class="material-symbols-outlined" aria-hidden="true">calendar_month</span>
            View your calendar
          </button>
          <button id="profile-signout" class="btn btn--ghost btn--block">
            Sign out
          </button>
        </div>
      `,
      async onMount(el) {
        el.querySelector("#profile-calendar").addEventListener("click", () =>
          router.go("/calendar")
        );
        el.querySelector("#profile-signout").addEventListener("click", () => {
          state.setUser(null);
          router.go("/"); // back to the sign-in / welcome screen
        });

        const histEl = el.querySelector("#profile-history");
        const chatsEl = el.querySelector("#profile-chats");

        // Sessions and chats are independent; load both concurrently and
        // render each into its own slot.
        const [sessionsResult, chatsResult] = await Promise.allSettled([
          api.getHistory(state.user?.userId),
          api.getChats(state.user?.userId),
        ]);

        // --- Saved answers (structured Q&A sessions) ---
        if (sessionsResult.status === "rejected") {
          histEl.innerHTML = `<div class="empty"><p class="muted">${escapeHtml(sessionsResult.reason.message)}</p></div>`;
        } else {
          const sessions = sessionsResult.value;
          if (!sessions.length) {
            histEl.innerHTML = `
              <div class="empty">
                <p class="muted">No saved answers yet.</p>
                <button id="profile-start" class="btn btn--primary"
                  style="margin-top:var(--space-3)">Start a check</button>
              </div>`;
            histEl.querySelector("#profile-start").addEventListener("click", () =>
              router.go("/entry")
            );
          } else {
            histEl.innerHTML = `<div class="list">
              ${sessions
                .map(
                  (s) => `
                <button class="list-item" data-id="${escapeHtml(s.id)}">
                  <span class="choice__title">${escapeHtml(s.headline)}</span>
                  <span class="list-item__meta">${escapeHtml(s.date)} · ${escapeHtml(s.product)}</span>
                </button>`
                )
                .join("")}
            </div>`;
          }
        }

        // --- Chat history (free-text LLM conversations) ---
        if (chatsResult.status === "rejected") {
          chatsEl.innerHTML = `<div class="empty"><p class="muted">${escapeHtml(chatsResult.reason.message)}</p></div>`;
          return;
        }
        const chats = chatsResult.value;
        if (!chats || !chats.length) {
          chatsEl.innerHTML = `<div class="empty"><p class="muted">No chat conversations yet.</p></div>`;
          return;
        }
        chatsEl.innerHTML = `<div class="list">
          ${chats
            .map((c) => {
              const date = new Date(c.updated_at || c.created_at).toLocaleDateString(
                undefined, { month: "short", day: "numeric" }
              );
              const status = c.complete ? "complete" : "in progress";
              return `
                <a class="list-item" href="#/chat?id=${encodeURIComponent(c.id)}">
                  <span class="choice__title">${escapeHtml(c.summary || "Untitled chat")}</span>
                  <span class="list-item__meta">${escapeHtml(date)} · ${status}</span>
                </a>`;
            })
            .join("")}
        </div>`;
      },
    };
  },
};
