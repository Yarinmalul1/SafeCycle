/* View: Catalog - plain-language explainers for methods & products.
   Read-only reference (the "smart patient leaflet" catalog).
   Each item shows a thumbnail so users can visually match their product.
   If a product has an `image` (e.g. "assets/products/yasmin.png") it's shown;
   otherwise a tinted icon stands in. */
import { router } from "../router.js";
import { METHODS, PILLS } from "../data/products.js";
import { escapeHtml } from "../util.js";

// Build a thumbnail: real photo if provided, else a tinted icon tile.
function thumb(icon, image, variant = "") {
  if (image) {
    return `<span class="cat-thumb ${variant}">
      <img src="${escapeHtml(image)}" alt="" loading="lazy" />
    </span>`;
  }
  return `<span class="cat-thumb ${variant}">
    <span class="material-symbols-outlined" aria-hidden="true">${icon}</span>
  </span>`;
}

function item({ icon, image, title, desc, variant }) {
  return `
    <div class="cat-item">
      ${thumb(icon, image, variant)}
      <span class="cat-item__body">
        <span class="choice__title">${escapeHtml(title)}</span>
        <span class="choice__desc">${escapeHtml(desc)}</span>
      </span>
    </div>`;
}

export const CatalogView = {
  render() {
    const combined = PILLS.filter((p) => p.type === "combined");
    const pop = PILLS.filter((p) => p.type === "progestogen-only");

    const pillItem = (p, variant) =>
      item({
        icon: "medication",
        image: p.image,
        title: p.name,
        desc: p.userExplainer,
        variant,
      });

    return {
      title: "Catalog",
      html: `
        <div class="stack" style="gap:var(--space-2)">
          <h1 class="title">Methods & products</h1>
          <p class="muted">Plain-language explanations with a picture, so you
            can check it matches what you have.</p>
          <span class="stub-badge" title="Partial seed">
            <span class="material-symbols-outlined" aria-hidden="true">science</span>
            Sample catalog - not the full clinical list
          </span>
        </div>

        <h2 class="subtitle">Methods</h2>
        <div class="list">
          ${METHODS.filter((m) => m.id !== "unknown")
            .map((m) => item({ icon: m.icon, image: m.image, title: m.label, desc: m.desc }))
            .join("")}
        </div>

        <h2 class="subtitle">Combined pills</h2>
        <div class="list">${combined.map((p) => pillItem(p, "")).join("")}</div>

        <h2 class="subtitle">Progestogen-only pills</h2>
        <div class="list">${pop.map((p) => pillItem(p, "cat-thumb--alt")).join("")}</div>

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
