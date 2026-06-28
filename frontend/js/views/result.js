/* View: Result / Guidance — ordered, step-by-step answer. */
import { state } from "../state.js";
import { router } from "../router.js";
import { api } from "../api.js";
import { openEscalation } from "../escalation.js";

const STATUS_META = {
  ok: { cls: "result-header--ok", icon: "check_circle" },
  warn: { cls: "result-header--warn", icon: "warning" },
  danger: { cls: "result-header--danger", icon: "medical_information" },
};

const addDays = (d, n) => {
  const x = new Date(d);
  x.setDate(x.getDate() + n);
  return x;
};
const fmtDate = (d) => d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
const fmtDay = (d) => d.toLocaleDateString(undefined, { weekday: "short" });

/* Day-by-day timeline derived from the guidance result. */
function buildTimeline(result) {
  if (result.escalate) return []; // urgent cases skip the calendar
  const today = new Date();
  const tomorrow = addDays(today, 1);
  const primary = result.steps.find((s) => s.primary) || result.steps[0];
  const rows = [
    { day: "Today", date: fmtDate(today), action: primary ? primary.text : "Follow the steps above" },
  ];

  if (result.backup && result.backup.needed) {
    const days = result.backup.days || 7;
    const backupEnd = addDays(today, days);
    const protectedDate = addDays(today, days + 1);
    rows.push({ day: "Tomorrow", date: fmtDate(tomorrow), action: "Take your next pill at the usual time" });
    rows.push({ day: `${days} days`, date: `${fmtDate(tomorrow)}–${fmtDate(backupEnd)}`, action: `Use backup protection (${result.backup.method})` });
    rows.push({ day: fmtDay(protectedDate), date: fmtDate(protectedDate), action: "You're protected again", ok: true });
  } else {
    rows.push({ day: "Tomorrow", date: fmtDate(tomorrow), action: "Continue your pack as normal" });
    rows.push({ day: "Status", date: "", action: "No backup needed — you're protected", ok: true });
  }
  return rows;
}

export const ResultView = {
  render() {
    const s = state.session;
    if (!s.method) {
      router.go("/");
      return { title: "", html: "", showBack: false };
    }

    return {
      title: "Your guidance",
      html: `
        <div id="result-loading" class="empty">
          <p class="lead">Working out your steps…</p>
        </div>
        <div id="result-body" hidden></div>
      `,
      async onMount(el) {
        const result = await api.getGuidance(s);
        state.update({ result });

        // Safety filter: hard-route urgent cases.
        if (result.escalate) openEscalation({ urgent: true });

        const meta = STATUS_META[result.status] || STATUS_META.warn;
        const loggedIn = !!state.user;

        const stepsHtml = result.steps
          .map(
            (step) => `
            <li class="steps__item ${step.primary ? "steps__item--primary" : ""}">
              <span>${step.text}</span>
            </li>`
          )
          .join("");

        const backupHtml =
          result.backup && result.backup.needed
            ? `<div class="card">
                 <strong>Backup protection</strong>
                 <p class="muted" style="margin-top:var(--space-1)">
                   Use ${result.backup.method} for the next
                   ${result.backup.days} days.
                 </p>
               </div>`
            : result.backup && result.backup.needed === false
            ? `<div class="card">
                 <strong>Backup protection</strong>
                 <p class="muted" style="margin-top:var(--space-1)">
                   Not usually needed in this situation.
                 </p>
               </div>`
            : "";

        const timeline = buildTimeline(result);
        const timelineHtml = timeline.length
          ? `<h2 class="subtitle" style="margin-top:var(--space-3)">Your timeline</h2>
             <ul class="timeline">
               ${timeline
                 .map(
                   (r) => `
                 <li class="timeline__row ${r.ok ? "timeline__row--ok" : ""}">
                   <span class="timeline__date">
                     <strong>${r.day}</strong>
                     ${r.date ? `<span>${r.date}</span>` : ""}
                   </span>
                   <span class="timeline__action">${r.action}</span>
                 </li>`
                 )
                 .join("")}
             </ul>`
          : "";

        el.querySelector("#result-loading").hidden = true;
        const body = el.querySelector("#result-body");
        body.hidden = false;
        body.innerHTML = `
          ${
            result._stub
              ? `<span class="stub-badge" title="Placeholder logic"><span class="material-symbols-outlined" aria-hidden="true">science</span> Demo guidance — not clinically reviewed</span>`
              : ""
          }

          <div class="result-header ${meta.cls}" role="status">
            <span class="result-header__icon material-symbols-outlined is-filled" aria-hidden="true">${meta.icon}</span>
            <span class="result-header__text">
              <span class="result-header__status">${result.statusLabel}</span>
              <span class="result-header__headline">${result.headline}</span>
            </span>
          </div>

          <h2 class="subtitle" style="margin-top:var(--space-3)">What to do</h2>
          <ol class="steps">${stepsHtml}</ol>

          ${backupHtml}

          ${timelineHtml}

          <p class="disclaimer">${result.disclaimer}</p>

          <div class="action-bar">
            <button id="gcal-btn" class="btn btn--secondary btn--block">
              <span class="material-symbols-outlined" aria-hidden="true">calendar_add_on</span>
              Add to Google Calendar
            </button>
            <button id="savetl-btn" class="btn btn--secondary btn--block">Save to timeline</button>
            <button id="clinician-btn" class="clinician-link">
              <span class="material-symbols-outlined" aria-hidden="true">stethoscope</span> Talk to a clinician
            </button>
            <button id="restart-btn" class="btn btn--primary btn--block">
              Start another conversation
            </button>
            <button id="dash-btn" class="btn btn--ghost btn--block">Back to dashboard</button>
          </div>
        `;

        body.querySelector("#clinician-btn").addEventListener("click", () =>
          openEscalation({ urgent: result.status === "danger" })
        );
        body.querySelector("#restart-btn").addEventListener("click", () => {
          state.reset();
          router.go("/entry");
        });
        body.querySelector("#dash-btn").addEventListener("click", () =>
          router.go("/dashboard")
        );
        body.querySelector("#gcal-btn").addEventListener("click", () =>
          alert("Google Calendar sync is coming soon.")
        );

        const saveBtn = body.querySelector("#savetl-btn");
        saveBtn.addEventListener("click", async () => {
          if (!loggedIn) {
            alert("Sign in on your profile to save answers to your timeline.");
            return;
          }
          saveBtn.disabled = true;
          saveBtn.textContent = "Saving…";
          await api.saveSession(s);
          saveBtn.textContent = "Saved ✓";
        });
      },
    };
  },
};
