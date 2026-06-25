/* View: Result / Guidance — ordered, step-by-step answer. */
import { state } from "../state.js";
import { router } from "../router.js";
import { api } from "../api.js";
import { openEscalation } from "../escalation.js";

const STATUS_META = {
  ok: { cls: "result-header--ok", icon: "✅" },
  warn: { cls: "result-header--warn", icon: "⚠️" },
  danger: { cls: "result-header--danger", icon: "⛔" },
};

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

        el.querySelector("#result-loading").hidden = true;
        const body = el.querySelector("#result-body");
        body.hidden = false;
        body.innerHTML = `
          ${
            result._stub
              ? `<span class="stub-badge" title="Placeholder logic">⚠ Demo guidance — not clinically reviewed</span>`
              : ""
          }

          <div class="result-header ${meta.cls}" role="status">
            <span class="result-header__icon" aria-hidden="true">${meta.icon}</span>
            <span class="result-header__text">
              <span class="result-header__status">${result.statusLabel}</span>
              <span class="result-header__headline">${result.headline}</span>
            </span>
          </div>

          <h2 class="subtitle" style="margin-top:var(--space-3)">What to do</h2>
          <ol class="steps">${stepsHtml}</ol>

          ${backupHtml}

          <p class="disclaimer">${result.disclaimer}</p>

          <div class="action-bar">
            ${
              loggedIn
                ? `<button id="save-btn" class="btn btn--secondary btn--block">Save this answer</button>`
                : ""
            }
            <button id="clinician-btn" class="clinician-link">
              <span aria-hidden="true">🩺</span> Talk to a clinician
            </button>
            <button id="restart-btn" class="btn btn--ghost btn--block">
              Start a new check
            </button>
          </div>
        `;

        body.querySelector("#clinician-btn").addEventListener("click", () =>
          openEscalation({ urgent: result.status === "danger" })
        );
        body.querySelector("#restart-btn").addEventListener("click", () => {
          state.reset();
          router.go("/");
        });

        const saveBtn = body.querySelector("#save-btn");
        if (saveBtn) {
          saveBtn.addEventListener("click", async () => {
            saveBtn.disabled = true;
            saveBtn.textContent = "Saving…";
            await api.saveSession(s);
            saveBtn.textContent = "Saved ✓";
          });
        }
      },
    };
  },
};
