/* View: Result / Guidance - ordered, step-by-step answer. */
import { state } from "../state.js";
import { router } from "../router.js";
import { api } from "../api.js";
import { openEscalation } from "../escalation.js";
import { toast } from "../toast.js";
import { downloadPlanner } from "../planner.js";

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
    rows.push({ day: `${days} days`, date: `${fmtDate(tomorrow)}-${fmtDate(backupEnd)}`, action: `Use backup protection (${result.backup.method})` });
    rows.push({ day: fmtDay(protectedDate), date: fmtDate(protectedDate), action: "You're protected again", ok: true });
  } else {
    rows.push({ day: "Tomorrow", date: fmtDate(tomorrow), action: "Continue your pack as normal" });
    rows.push({ day: "Status", date: "", action: "No backup needed - you're protected", ok: true });
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
        // If we already have a result in state (e.g. user navigated back from
        // home via "Protection status"), reuse it instead of re-running the
        // engine. Re-running would write a duplicate row to the sessions
        // table and the user would see the same answer with a fresh latency.
        let result = state.session.result;
        try {
          if (!result) result = await api.getGuidance(s, state.user?.userId);
        } catch (err) {
          el.querySelector("#result-loading").hidden = true;
          const body = el.querySelector("#result-body");
          body.hidden = false;
          body.innerHTML = `
            <div class="card stack" style="gap:var(--space-2)">
              <strong>We couldn't work out your steps</strong>
              <p class="muted">${err.message}</p>
              <button id="result-retry" class="btn btn--primary btn--block">Try again</button>
              <button id="result-clinician" class="clinician-link">
                <span class="material-symbols-outlined" aria-hidden="true">stethoscope</span> Talk to a clinician
              </button>
            </div>`;
          body.querySelector("#result-retry").addEventListener("click", () => router.go("/result"));
          body.querySelector("#result-clinician").addEventListener("click", () => openEscalation());
          toast(err.message);
          return;
        }
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

          <p class="saved-line" id="saved-line">
            <span class="material-symbols-outlined" aria-hidden="true">check_circle</span>
            <a href="#/profile" id="saved-link">Saved to history</a>
          </p>

          <div class="action-bar">
            <button id="gcal-btn" class="btn btn--secondary btn--block">
              <span class="material-symbols-outlined" aria-hidden="true">calendar_add_on</span>
              Add to Google Calendar
            </button>
            <button id="planner-btn" class="btn btn--secondary btn--block">
              <span class="material-symbols-outlined" aria-hidden="true">image</span>
              Generate planner image
            </button>
            <button id="clinician-btn" class="clinician-link">
              <span class="material-symbols-outlined" aria-hidden="true">stethoscope</span> Talk to a clinician
            </button>
            <button id="restart-btn" class="btn btn--primary btn--block">
              Start another conversation
            </button>
            <button id="home-btn" class="btn btn--ghost btn--block">
              <span class="material-symbols-outlined" aria-hidden="true">home</span>
              Back to Home
            </button>
          </div>
        `;

        body.querySelector("#clinician-btn").addEventListener("click", () =>
          openEscalation({ urgent: result.status === "danger" })
        );
        body.querySelector("#restart-btn").addEventListener("click", () => {
          state.reset();
          router.go("/entry");
        });
        body.querySelector("#home-btn").addEventListener("click", () => {
          // Don't reset: keep session.result so "Protection status" on the
          // home cards can route back here. "Start another conversation"
          // is the explicit reset path.
          router.go("/home");
        });

        // Planner image: render the timeline as a designed PNG card and
        // download it. Pure client-side (Canvas API); no backend round-trip.
        body.querySelector("#planner-btn").addEventListener("click", () => {
          try {
            downloadPlanner({
              product: state.session.product?.name || state.session.method || "Your method",
              result,
              timeline,
            });
            toast("Your planner image is downloading.");
          } catch (err) {
            toast(`Couldn't generate planner image: ${err.message}`);
          }
        });

        // Calendar export: generate the 90-day schedule for the user's method,
        // then push events to their Google Calendar. Requires sign-in.
        body.querySelector("#gcal-btn").addEventListener("click", async () => {
          if (!loggedIn || !state.user?.userId) {
            return toast("Sign in to export your schedule.");
          }
          const method = state.session.method || "pill";
          const today = new Date().toISOString().slice(0, 10);
          toast("Generating your schedule...");
          const gen = await api.generateCalendar({
            userId: state.user.userId,
            product: method,
            startDate: today,
            hour: 9,
          });
          if (!gen.ok) return toast(gen.reason || "Could not generate schedule.");
          toast(`Asking Google for calendar access (${gen.calendar.schedule_data.length} events)...`);
          const exp = await api.exportToGoogleCalendar({
            userId: state.user.userId,
            product: method,
            events: gen.calendar.schedule_data,
          });
          if (!exp.ok) return toast(exp.reason || "Export failed.");
          const parts = [];
          if (exp.added) parts.push(`${exp.added} added`);
          if (exp.alreadyPresent) parts.push(`${exp.alreadyPresent} already in calendar`);
          if (exp.failed) parts.push(`${exp.failed} failed`);
          toast(`Calendar export: ${parts.join(", ") || "no events"}`);
        });

        // "Saved to history" is a confirmation line: /api/guidance already
        // persisted this session to Supabase under the user's id during the
        // initial fetch above. When the user isn't signed in there's no
        // history row, so we hide the line entirely rather than lie.
        const savedLine = body.querySelector("#saved-line");
        if (!loggedIn) savedLine.hidden = true;
      },
    };
  },
};
