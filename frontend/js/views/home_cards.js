/* View: Home (6-card hub) - the main landing the user returns to between
   guided checks. Each card routes to a real, working destination -- there
   are no "coming soon" stubs. Reachable from the bottom-nav Home tab and
   from the result page's "Back to Home" button. */
import { state } from "../state.js";
import { router } from "../router.js";
import { api } from "../api.js";
import { escapeHtml } from "../util.js";

function firstName() {
  const n = state.user?.name;
  return n ? escapeHtml(n.split(" ")[0]) : null;
}

// Each card: icon + title + content + the action label + the route it opens.
// Order kept the same as the original dashboard spec.
const CARDS = [
  {
    icon: "notifications_active",
    title: "Reminders",
    content: "See your daily reminders in one visual schedule.",
    action: "Set a reminder",
    go: "/calendar",
  },
  {
    icon: "history",
    title: "History",
    content: "View your past answers and previous guidance sessions.",
    action: "See all previous sessions",
    go: "/profile",
  },
  {
    icon: "chat",
    title: "Latest Q&A",
    content: "Open your most recent answer.",
    action: "Open last answer",
    // "Latest" = most recent thing the user has. Chats are the primary Q&A
    // path now, so prefer the newest chat. Fall back to the last structured
    // result if there are no chats, then to /entry as a last resort.
    resolve: async () => {
      const userId = state.user?.userId;
      if (userId) {
        try {
          const chats = await api.getChats(userId);
          if (chats && chats.length) {
            return `/chat?id=${encodeURIComponent(chats[0].id)}`;
          }
        } catch {
          /* fall through to the structured result fallback */
        }
      }
      if (state.session?.result) return "/result";
      return "/entry";
    },
  },
  {
    icon: "medical_services",
    title: "New methods",
    content: "Explore pills, ring, and patch options.",
    action: "Browse catalog",
    go: "/catalog",
  },
  {
    icon: "lightbulb",
    title: "New info",
    content: "How SafeCycle works and where guidance comes from.",
    action: "Learn more",
    go: "/info",
  },
  {
    icon: "calendar_month",
    title: "Calendar",
    content: "View your schedule and sync it to your Google Calendar.",
    action: "View schedule",
    go: "/calendar",
  },
];

export const HomeCardsView = {
  render() {
    const name = firstName();
    return {
      title: "Home",
      html: `
        <div class="welcome-banner">
          <h1 class="title">${name ? `Welcome back, ${name}!` : "Welcome to SafeCycle"}</h1>
          <p class="muted">Let's help you stay on track with your contraception.</p>
        </div>

        <button id="home-start" class="btn btn--primary btn--block btn--lg">
          <span class="material-symbols-outlined" aria-hidden="true">chat_bubble</span>
          Start new conversation privately
        </button>

        <div class="dash-grid" style="margin-top:var(--space-3)">
          ${CARDS.map(
            (c, i) => `
            <div class="dash-card">
              <span class="material-symbols-outlined dash-card__icon" aria-hidden="true">${c.icon}</span>
              <h3 class="dash-card__title">${c.title}</h3>
              <p class="dash-card__content">${c.content}</p>
              <button class="dash-card__link" data-card="${i}">
                ${c.action}
                <span class="material-symbols-outlined" aria-hidden="true">chevron_right</span>
              </button>
            </div>`
          ).join("")}
        </div>
      `,
      onMount(el) {
        el.querySelector("#home-start").addEventListener("click", () => {
          state.reset();
          router.go("/entry");
        });

        el.querySelectorAll("[data-card]").forEach((btn) =>
          btn.addEventListener("click", async () => {
            const card = CARDS[Number(btn.dataset.card)];
            // Disable while resolving so a double-click can't fire twice.
            btn.disabled = true;
            try {
              const path = card.resolve ? await card.resolve() : card.go;
              router.go(path);
            } finally {
              btn.disabled = false;
            }
          })
        );
      },
    };
  },
};
