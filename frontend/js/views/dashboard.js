/* View: Dashboard - the main landing after the welcome screen.
   Welcome banner + primary CTA + grid of update cards.
   Uses the existing Dusty Rose card styling. */
import { state } from "../state.js";
import { router } from "../router.js";
import { escapeHtml } from "../util.js";
import { toast } from "../toast.js";

function firstName() {
  const n = state.user?.name;
  return n ? escapeHtml(n.split(" ")[0]) : null;
}

// Each card: icon + title + content + a link/action.
// `go` routes internally; `stub` shows a "coming soon" note.
const CARDS = [
  { icon: "notifications_active", title: "Reminders", content: "No reminders set yet.", link: "Set a reminder", stub: true },
  { icon: "shield", title: "Protection status", content: "Run a check to see your current status.", link: "Check now", go: "/entry" },
  { icon: "chat", title: "Latest Q&A", content: "You haven't asked a question yet.", link: "Ask a question", go: "/entry" },
  { icon: "medical_services", title: "New methods", content: "Explore pills, ring, and patch options.", link: "Browse catalog", go: "/catalog" },
  { icon: "lightbulb", title: "New info", content: "How SafeCycle works and where guidance comes from.", link: "Learn more", go: "/info" },
  { icon: "calendar_month", title: "Google Calendar", content: "Sync pill and backup reminders to your calendar.", link: "Connect", stub: true },
];

export const DashboardView = {
  render() {
    const name = firstName();

    return {
      title: "SafeCycle",
      html: `
        <div class="welcome-banner">
          <h1 class="title">${name ? `Welcome back, ${name}!` : "Welcome to SafeCycle"}</h1>
          <p class="muted">Let's help you stay on track with your contraception.</p>
        </div>

        <button id="dash-start" class="btn btn--primary btn--block btn--lg">
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
                ${c.link}
                <span class="material-symbols-outlined" aria-hidden="true">chevron_right</span>
              </button>
            </div>`
          ).join("")}
        </div>
      `,
      onMount(el) {
        el.querySelector("#dash-start").addEventListener("click", () => {
          state.reset();
          router.go("/entry");
        });

        el.querySelectorAll("[data-card]").forEach((btn) =>
          btn.addEventListener("click", () => {
            const card = CARDS[Number(btn.dataset.card)];
            if (card.go) router.go(card.go);
            else toast(`${card.title} is coming soon.`);
          })
        );
      },
    };
  },
};
