/* View: Home (6-card hub) - the main landing the user returns to between
   guided checks. Each card routes to a real, working destination -- there
   are no "coming soon" stubs. Reachable from the bottom-nav Home tab and
   from the result page's "Back to Home" button. */
import { state } from "../state.js";
import { router } from "../router.js";
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
    icon: "shield",
    title: "Protection status",
    content: "See your current status from your last check.",
    action: "Check current status",
    // Resolved at click time so we can route to the previous result if
    // state.session.result is populated, otherwise start a fresh check.
    // (state.result is undefined -- result lives on the session record.)
    resolve: () => (state.session?.result ? "/result" : "/entry"),
  },
  {
    icon: "chat",
    title: "Latest Q&A",
    content: "Open your most recent answer, or ask a new question.",
    action: "Ask a question",
    // Same behaviour as Protection status: jump to the last result if one
    // exists, otherwise open /entry to start a new conversation.
    resolve: () => (state.session?.result ? "/result" : "/entry"),
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

        <h2 class="subtitle" style="margin-top:var(--space-2)">Latest &amp; recent updates</h2>

        <div class="dash-grid">
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
          btn.addEventListener("click", () => {
            const card = CARDS[Number(btn.dataset.card)];
            const path = card.resolve ? card.resolve() : card.go;
            router.go(path);
          })
        );
      },
    };
  },
};
