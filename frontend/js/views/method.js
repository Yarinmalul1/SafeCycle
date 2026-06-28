/* View: Method & Product selection */
import { state } from "../state.js";
import { router } from "../router.js";
import { METHODS, PILLS, searchPills } from "../data/products.js";
import { escapeHtml, showFieldError, clearFieldError } from "../util.js";

export const MethodView = {
  render() {
    const chosen = state.session.method;
    return {
      title: "Your method",
      html: `
        <div class="stack" style="gap:var(--space-2)">
          <h1 class="title">Which are you using?<span class="required" aria-hidden="true">*</span></h1>
          <p class="muted">Each method — and each pill — has its own rules.</p>
        </div>

        <p id="method-error" class="field-error" role="alert" hidden></p>

        <div class="stack" id="methods">
          ${METHODS.map(
            (m) => `
            <button class="choice" data-method="${m.id}"
              aria-pressed="${chosen === m.id}">
              <span class="choice__icon material-symbols-outlined" aria-hidden="true">${m.icon}</span>
              <span class="choice__body">
                <span class="choice__title">${m.label}</span>
                <span class="choice__desc">${m.desc}</span>
              </span>
            </button>`
          ).join("")}
        </div>

        <!-- Pill brand picker (revealed when "Pill" is chosen) -->
        <div id="pill-picker" ${chosen === "pill" ? "" : "hidden"}>
          <div class="field" style="margin-top:var(--space-4)">
            <label class="field__label" for="pill-search">Find your pill</label>
            <div class="search">
              <input id="pill-search" class="input" type="search"
                placeholder="Search brand, e.g. Microgynon" autocomplete="off" />
            </div>
          </div>
          <div class="stack" id="pill-results" style="margin-top:var(--space-2)"></div>
        </div>

        <div class="spacer"></div>
        <div class="action-bar">
          <button id="method-next" class="btn btn--primary btn--block btn--lg">
            Continue
          </button>
        </div>
      `,
      onMount(el) {
        const picker = el.querySelector("#pill-picker");
        const nextBtn = el.querySelector("#method-next");
        const results = el.querySelector("#pill-results");
        const methodsEl = el.querySelector("#methods");
        const errorEl = el.querySelector("#method-error");

        const renderPills = (q = "") => {
          const list = searchPills(q);
          results.innerHTML = list.length
            ? list
                .map(
                  (p) => `
              <button class="choice" data-pill="${p.id}"
                aria-pressed="${state.session.product?.id === p.id}">
                <span class="choice__body">
                  <span class="choice__title">${escapeHtml(p.name)}</span>
                  <span class="choice__desc">${escapeHtml(p.userExplainer)}</span>
                </span>
              </button>`
                )
                .join("")
            : `<p class="empty">No match. Try "I don't know my pill".</p>`;

          results.querySelectorAll("[data-pill]").forEach((b) =>
            b.addEventListener("click", () => {
              const product = PILLS.find((p) => p.id === b.dataset.pill);
              state.update({ product: { id: product.id, name: product.name } });
              results
                .querySelectorAll("[data-pill]")
                .forEach((x) => x.setAttribute("aria-pressed", "false"));
              b.setAttribute("aria-pressed", "true");
              clearFieldError(results, errorEl);
            })
          );
        };

        el.querySelectorAll("[data-method]").forEach((btn) =>
          btn.addEventListener("click", () => {
            const method = btn.dataset.method;
            state.update({ method, product: null });
            el.querySelectorAll("[data-method]").forEach((x) =>
              x.setAttribute("aria-pressed", "false")
            );
            btn.setAttribute("aria-pressed", "true");

            picker.hidden = method !== "pill";
            if (method === "pill") renderPills();
            // Clear any error state on either container.
            clearFieldError(methodsEl, errorEl);
            clearFieldError(results, errorEl);
          })
        );

        const search = el.querySelector("#pill-search");
        if (search) {
          search.addEventListener("input", (e) => renderPills(e.target.value));
        }

        if (chosen === "pill") renderPills();

        nextBtn.addEventListener("click", () => {
          const s = state.session;
          if (!s.method) {
            showFieldError(methodsEl, errorEl, "Please select your contraceptive method.");
            return;
          }
          if (s.method === "pill" && !s.product) {
            picker.hidden = false;
            showFieldError(results, errorEl, "Please select your pill (or “I don't know my pill”).");
            return;
          }
          clearFieldError(methodsEl, errorEl);
          state.update({ questionIndex: 0 });
          router.go("/questions");
        });
      },
    };
  },
};
