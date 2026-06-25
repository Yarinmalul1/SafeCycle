/* View: Catalog — plain-language explainers for methods & products.
   Read-only reference (the "smart patient leaflet" catalog). */
import { router } from "../router.js";
import { METHODS, PILLS } from "../data/products.js";
import { escapeHtml } from "../util.js";

export const CatalogView = {
  render() {
    const combined = PILLS.filter((p) => p.type === "combined");
    const pop = PILLS.filter((p) => p.type === "progestogen-only");

    const pillItem = (p) => `
      <div class="list-item">
        <span class="choice__title">${escapeHtml(p.name)}</span>
        <span class="choice__desc">${escapeHtml(p.userExplainer)}</span>
      </div>`;

    return {
      title: "Catalog",
      html: `
        <div class="stack" style="gap:var(--space-2)">
          <h1 class="title">Methods & products</h1>
          <p class="muted">Plain-language explanations. Each method and pill
            has its own rules.</p>
          <span class="stub-badge" title="Partial seed">
            <span class="material-symbols-outlined" aria-hidden="true">science</span>
            Sample catalog — not the full clinical list
          </span>
        </div>

        <h2 class="subtitle">Methods</h2>
        <div class="list">
          ${METHODS.filter((m) => m.id !== "unknown")
            .map(
              (m) => `
            <div class="list-item">
              <span class="choice__title">
                <span class="material-symbols-outlined" aria-hidden="true"
                  style="vertical-align:middle;color:var(--color-primary)">${m.icon}</span>
                ${m.label}
              </span>
              <span class="choice__desc">${m.desc}</span>
            </div>`
            )
            .join("")}
        </div>

        <h2 class="subtitle">Combined pills</h2>
        <div class="list">${combined.map(pillItem).join("")}</div>

        <h2 class="subtitle">Progestogen-only pills</h2>
        <div class="list">${pop.map(pillItem).join("")}</div>

        <div class="action-bar">
          <button id="catalog-start" class="btn btn--primary btn--block btn--lg">
            Start a check
          </button>
        </div>
      `,
      onMount(el) {
        el.querySelector("#catalog-start").addEventListener("click", () =>
          router.go("/entry")
        );
      },
    };
  },
};
