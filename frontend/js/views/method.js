/* View: Method & Product selection */
import { state } from "../state.js";
import { router } from "../router.js";
import { METHODS, PILLS, searchPills } from "../data/products.js";
import { escapeHtml } from "../util.js";

export const MethodView = {
  render() {
    const chosen = state.session.method;
    return {
      title: "Your method",
      html: `
        <div class="stack" style="gap:var(--space-2)">
          <h1 class="title">Which are you using?</h1>
          <p class="muted">Each method — and each pill — has its own rules.</p>
        </div>

        <div class="stack" id="methods">
          ${METHODS.map(
            (m) => `
            <button class="choice" data-method="${m.id}"
              aria-pressed="${chosen === m.id}">
              <span class="choice__icon" aria-hidden="true">${m.icon}</span>
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
          <button id="method-next" class="btn btn--primary btn--block btn--lg" disabled>
            Continue
          </button>
        </div>
      `,
      onMount(el) {
        const picker = el.querySelector("#pill-picker");
        const nextBtn = el.querySelector("#method-next");
        const results = el.querySelector("#pill-results");

        const refreshNext = () => {
          const s = state.session;
          const ready =
            (s.method && s.method !== "pill") ||
            (s.method === "pill" && s.product);
          nextBtn.disabled = !ready;
        };

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
              refreshNext();
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
            refreshNext();
          })
        );

        const search = el.querySelector("#pill-search");
        if (search) {
          search.addEventListener("input", (e) => renderPills(e.target.value));
        }

        if (chosen === "pill") renderPills();
        refreshNext();

        nextBtn.addEventListener("click", () => {
          state.update({ questionIndex: 0 });
          router.go("/questions");
        });
      },
    };
  },
};
