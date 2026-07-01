/* View: Method & Product selection */
import { state } from "../state.js";
import { router } from "../router.js";
import {
  METHODS,
  PILLS,
  RING_OPTIONS,
  PATCH_OPTIONS,
  UNKNOWN_METHOD_PRODUCT,
  productsForMethod,
  searchPills,
} from "../data/products.js";
import { escapeHtml, showFieldError, clearFieldError } from "../util.js";

// Methods for which the user must additionally pick a specific product.
// "unknown" auto-selects UNKNOWN_METHOD_PRODUCT and needs no picker.
const METHODS_WITH_PICKER = new Set(["pill", "ring", "patch"]);

export const MethodView = {
  render() {
    const chosen = state.session.method;
    return {
      title: "Your method",
      html: `
        <div class="stack" style="gap:var(--space-2)">
          <h1 class="title">Which are you using?<span class="required" aria-hidden="true">*</span></h1>
          <p class="muted">Each method - and each pill - has its own rules.</p>
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

        <!-- Pill brand picker: search + list. Revealed when "Pill" is chosen. -->
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

        <!-- Ring / patch pickers: fixed list (small option set, no search). -->
        <div id="brand-picker" ${chosen === "ring" || chosen === "patch" ? "" : "hidden"}
             style="margin-top:var(--space-4)">
          <p class="field__label" id="brand-picker-label">Which brand?</p>
          <div class="stack" id="brand-results" style="margin-top:var(--space-2)"></div>
        </div>

        <div class="spacer"></div>
        <div class="action-bar">
          <button id="method-next" class="btn btn--primary btn--block btn--lg">
            Continue
          </button>
        </div>
      `,
      onMount(el) {
        const pillPicker = el.querySelector("#pill-picker");
        const brandPicker = el.querySelector("#brand-picker");
        const brandLabel = el.querySelector("#brand-picker-label");
        const pillResults = el.querySelector("#pill-results");
        const brandResults = el.querySelector("#brand-results");
        const methodsEl = el.querySelector("#methods");
        const errorEl = el.querySelector("#method-error");

        /* Common renderer for a "list of choice buttons" picker. Used by the
           ring and patch brand pickers. */
        const renderBrandList = (items) => {
          brandResults.innerHTML = items
            .map(
              (p) => `
              <button class="choice" data-brand="${p.id}"
                aria-pressed="${state.session.product?.id === p.id}">
                <span class="choice__body">
                  <span class="choice__title">${escapeHtml(p.name)}</span>
                  <span class="choice__desc">${escapeHtml(p.userExplainer)}</span>
                </span>
              </button>`
            )
            .join("");
          brandResults.querySelectorAll("[data-brand]").forEach((b) =>
            b.addEventListener("click", () => {
              const product = items.find((p) => p.id === b.dataset.brand);
              state.update({ product: { id: product.id, name: product.name } });
              brandResults
                .querySelectorAll("[data-brand]")
                .forEach((x) => x.setAttribute("aria-pressed", "false"));
              b.setAttribute("aria-pressed", "true");
              clearFieldError(brandResults, errorEl);
            })
          );
        };

        const renderPills = (q = "") => {
          const list = searchPills(q);
          pillResults.innerHTML = list.length
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

          pillResults.querySelectorAll("[data-pill]").forEach((b) =>
            b.addEventListener("click", () => {
              const product = PILLS.find((p) => p.id === b.dataset.pill);
              state.update({ product: { id: product.id, name: product.name } });
              pillResults
                .querySelectorAll("[data-pill]")
                .forEach((x) => x.setAttribute("aria-pressed", "false"));
              b.setAttribute("aria-pressed", "true");
              clearFieldError(pillResults, errorEl);
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

            // Pill = search picker; ring/patch = short brand list; unknown =
            // auto-selects the "unspecified" product and needs no picker (the
            // backend's fallback prompt handles unknown scenarios).
            pillPicker.hidden = method !== "pill";
            const showBrandPicker = method === "ring" || method === "patch";
            brandPicker.hidden = !showBrandPicker;

            if (method === "pill") {
              renderPills();
            } else if (method === "ring") {
              brandLabel.textContent = "Which ring?";
              renderBrandList(RING_OPTIONS);
            } else if (method === "patch") {
              brandLabel.textContent = "Which patch?";
              renderBrandList(PATCH_OPTIONS);
            } else if (method === "unknown") {
              // Auto-set a placeholder product so the backend accepts the
              // request and routes it to the fallback prompt.
              state.update({
                product: {
                  id: UNKNOWN_METHOD_PRODUCT.id,
                  name: UNKNOWN_METHOD_PRODUCT.name,
                },
              });
            }
            clearFieldError(methodsEl, errorEl);
            clearFieldError(pillResults, errorEl);
            clearFieldError(brandResults, errorEl);
          })
        );

        const search = el.querySelector("#pill-search");
        if (search) {
          search.addEventListener("input", (e) => renderPills(e.target.value));
        }

        // Restore the correct picker on remount (e.g. router back-nav).
        if (chosen === "pill") renderPills();
        else if (chosen === "ring") {
          brandLabel.textContent = "Which ring?";
          renderBrandList(RING_OPTIONS);
        } else if (chosen === "patch") {
          brandLabel.textContent = "Which patch?";
          renderBrandList(PATCH_OPTIONS);
        }

        const nextBtn = el.querySelector("#method-next");

        nextBtn.addEventListener("click", () => {
          const s = state.session;
          if (!s.method) {
            showFieldError(methodsEl, errorEl, "Please select your contraceptive method.");
            return;
          }
          if (METHODS_WITH_PICKER.has(s.method) && !s.product) {
            if (s.method === "pill") {
              pillPicker.hidden = false;
              showFieldError(pillResults, errorEl, "Please select your pill (or “I don't know my pill”).");
            } else {
              brandPicker.hidden = false;
              const label = s.method === "ring" ? "ring" : "patch";
              showFieldError(brandResults, errorEl, `Please select your ${label}.`);
            }
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
