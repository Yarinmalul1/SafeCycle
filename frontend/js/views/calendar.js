/* View: Calendar - visual month-grid of the user's contraception schedule.
   Fetches the user's persisted schedule from /api/calendar/{userId} and
   lays it out as one or more month grids with each day cell showing the
   events for that day. If the user has no schedule yet, lets them pick a
   method and generate one in place. */
import { state } from "../state.js";
import { router } from "../router.js";
import { api } from "../api.js";
import { escapeHtml } from "../util.js";
import { toast } from "../toast.js";

const WEEKDAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTH_LABELS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

// Method options offered on the empty-state generator. Matches what the
// backend's logic.calendar.generate() dispatches on.
const METHOD_CHOICES = [
  { id: "pill", label: "Pill (daily)" },
  { id: "ring", label: "Vaginal ring (21 in / 7 out)" },
  { id: "patch", label: "Patch (weekly)" },
];

/** Group event records by YYYY-MM-DD date key. */
function indexByDay(events) {
  const map = new Map();
  for (const e of events) {
    const key = e.starts_at.slice(0, 10);
    if (!map.has(key)) map.set(key, []);
    map.get(key).push(e);
  }
  return map;
}

/** Return the YYYY-MM keys for every month touched by the schedule, in order. */
function monthKeys(events) {
  const seen = new Set();
  const keys = [];
  for (const e of events) {
    const k = e.starts_at.slice(0, 7);
    if (!seen.has(k)) {
      seen.add(k);
      keys.push(k);
    }
  }
  return keys;
}

function todayKey() {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/** Render one month's 7-col grid. `monthKey` is "YYYY-MM"; `byDay` is the
 *  index of date -> events from indexByDay. */
function renderMonth(monthKey, byDay) {
  const [y, m] = monthKey.split("-").map(Number);
  const monthName = MONTH_LABELS[m - 1];
  const firstWeekday = new Date(y, m - 1, 1).getDay(); // 0..6 (Sun..Sat)
  const daysInMonth = new Date(y, m, 0).getDate();
  const today = todayKey();

  const cells = [];
  // Leading blanks so day 1 lands under its weekday column.
  for (let i = 0; i < firstWeekday; i++) cells.push(`<div class="cal-cell cal-cell--empty"></div>`);
  for (let day = 1; day <= daysInMonth; day++) {
    const key = `${y}-${String(m).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    const events = byDay.get(key) || [];
    const isToday = key === today;
    const classes = [
      "cal-cell",
      events.length ? "cal-cell--has-event" : "",
      isToday ? "cal-cell--today" : "",
    ].filter(Boolean).join(" ");
    // First event's summary is enough for a tooltip; full list shows under
    // the grid via the event list below.
    const titleAttr = events.length
      ? ` title="${escapeHtml(events.map((e) => e.summary).join(" · "))}"`
      : "";
    const dot = events.length ? `<span class="cal-cell__dot" aria-hidden="true"></span>` : "";
    cells.push(`<div class="${classes}"${titleAttr}>
      <span class="cal-cell__num">${day}</span>
      ${dot}
    </div>`);
  }

  return `
    <section class="cal-month">
      <h3 class="cal-month__title">${monthName} ${y}</h3>
      <div class="cal-weekdays">
        ${WEEKDAY_LABELS.map((w) => `<span>${w}</span>`).join("")}
      </div>
      <div class="cal-grid">${cells.join("")}</div>
    </section>`;
}

/** Render the full list of upcoming events under the grids. */
function renderUpcoming(events) {
  const today = todayKey();
  const upcoming = events.filter((e) => e.starts_at.slice(0, 10) >= today).slice(0, 14);
  if (!upcoming.length) {
    return `<p class="muted">No upcoming reminders.</p>`;
  }
  return `
    <ul class="cal-list">
      ${upcoming
        .map((e) => {
          const d = new Date(e.starts_at);
          const dateLabel = d.toLocaleDateString(undefined, {
            weekday: "short", month: "short", day: "numeric",
          });
          const timeLabel = d.toLocaleTimeString(undefined, {
            hour: "numeric", minute: "2-digit",
          });
          return `
          <li class="cal-list__row">
            <span class="cal-list__when">
              <strong>${dateLabel}</strong>
              <span class="muted">${timeLabel}</span>
            </span>
            <span class="cal-list__what">
              <strong>${escapeHtml(e.summary)}</strong>
              <span class="muted">${escapeHtml(e.description)}</span>
            </span>
          </li>`;
        })
        .join("")}
    </ul>`;
}

function renderEmpty() {
  return `
    <div class="card stack" style="gap:var(--space-2)">
      <strong>No schedule yet</strong>
      <p class="muted">Pick your method and we'll generate a 90-day schedule
        you can view here and add to Google Calendar.</p>
      <label for="cal-method" class="sr-only">Choose your method</label>
      <select id="cal-method" class="textarea" style="height:auto;padding:var(--space-2)">
        ${METHOD_CHOICES.map((m) => `<option value="${m.id}">${m.label}</option>`).join("")}
      </select>
      <button id="cal-generate" class="btn btn--primary btn--block">
        Generate schedule
      </button>
    </div>`;
}

function renderSchedule(calendar) {
  const events = calendar.schedule_data || [];
  const byDay = indexByDay(events);
  const months = monthKeys(events).map((k) => renderMonth(k, byDay)).join("");
  const product = (calendar.product || "your method").toLowerCase();
  return `
    <div class="card stack" style="gap:var(--space-1)">
      <strong>Schedule for ${escapeHtml(product)}</strong>
      <p class="muted">Starting ${escapeHtml(calendar.start_date)} at ${calendar.hour}:00.
        ${events.length} reminders saved.</p>
    </div>

    <div class="cal-months">${months}</div>

    <h2 class="subtitle">Upcoming reminders</h2>
    ${renderUpcoming(events)}

    <div class="action-bar">
      <button id="cal-gcal" class="btn btn--primary btn--block">
        <span class="material-symbols-outlined" aria-hidden="true">calendar_add_on</span>
        Add to Google Calendar
      </button>
      <button id="cal-regenerate" class="btn btn--ghost btn--block">
        Generate a new schedule
      </button>
    </div>`;
}

async function generateAndRender(el, userId, product) {
  const slot = el.querySelector("#cal-slot");
  slot.innerHTML = `<div class="empty"><p class="muted">Generating your schedule…</p></div>`;
  const today = todayKey();
  const gen = await api.generateCalendar({
    userId, product, startDate: today, hour: 9,
  });
  if (!gen.ok) {
    slot.innerHTML = `<div class="empty"><p class="muted">${escapeHtml(gen.reason)}</p></div>`;
    toast(gen.reason || "Could not generate schedule.");
    return;
  }
  slot.innerHTML = renderSchedule(gen.calendar);
  wireScheduleActions(el, userId, gen.calendar);
}

function wireScheduleActions(el, userId, calendar) {
  el.querySelector("#cal-gcal")?.addEventListener("click", async () => {
    const events = calendar.schedule_data || [];
    if (!events.length) return toast("No events to export.");
    toast(`Asking Google for calendar access (${events.length} events)…`);
    const exp = await api.exportToGoogleCalendar({
      userId, product: calendar.product, events,
    });
    if (!exp.ok) return toast(exp.reason || "Export failed.");
    const parts = [];
    if (exp.added) parts.push(`${exp.added} added`);
    if (exp.alreadyPresent) parts.push(`${exp.alreadyPresent} already in calendar`);
    if (exp.failed) parts.push(`${exp.failed} failed`);
    toast(`Calendar export: ${parts.join(", ") || "no events"}`);
  });

  el.querySelector("#cal-regenerate")?.addEventListener("click", () => {
    const slot = el.querySelector("#cal-slot");
    slot.innerHTML = renderEmpty();
    wireGenerateForm(el, userId);
  });
}

function wireGenerateForm(el, userId) {
  el.querySelector("#cal-generate")?.addEventListener("click", () => {
    const product = el.querySelector("#cal-method").value;
    generateAndRender(el, userId, product);
  });
}

export const CalendarView = {
  render() {
    if (!state.user?.userId) {
      // Auth-gated route, but guard anyway in case of state races.
      router.go("/");
      return { title: "", html: "", showBack: false };
    }
    return {
      title: "Calendar",
      html: `
        <div class="stack" style="gap:var(--space-2)">
          <h1 class="title">Your calendar</h1>
          <p class="muted">A visual view of your contraception schedule.</p>
        </div>
        <div id="cal-slot">
          <div class="empty"><p class="muted">Loading your schedule…</p></div>
        </div>
      `,
      async onMount(el) {
        const userId = state.user.userId;
        const res = await api.getCalendar(userId);
        const slot = el.querySelector("#cal-slot");
        if (res.ok) {
          slot.innerHTML = renderSchedule(res.calendar);
          wireScheduleActions(el, userId, res.calendar);
        } else {
          // 404 from the backend means "no schedule yet" -- normal first-run
          // state, not an error. Anything else (5xx, network) is shown verbatim.
          slot.innerHTML = renderEmpty();
          wireGenerateForm(el, userId);
        }
      },
    };
  },
};
