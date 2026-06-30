/* View: Catalog - plain-language explainers for methods & products.
   Read-only reference (the "smart patient leaflet" catalog).
   Methods come from a small static list (generic device families). Specific
   products are fetched from the backend's /api/products so there is one
   source of truth for what the engine actually supports. */
import { router } from "../router.js";
import { api } from "../api.js";
import { METHODS } from "../data/products.js";
import { escapeHtml } from "../util.js";
import { toast } from "../toast.js";

// Pretty labels for each pill-family `type` returned by /api/products. Keys
// match the backend's PillType enum exactly.
const TYPE_LABELS = {
  combined: "Combined pills",
  progestogen_only: "Progestogen-only pills",
  extended_cycle: "Extended-cycle pills",
  ring: "Vaginal ring",
};

// Display order so the catalog reads "everyday combined first, then POPs,
// then extended-cycle, then non-pill methods".
const TYPE_ORDER = ["combined", "progestogen_only", "extended_cycle", "ring"];

// Per-type icon for the thumbnail tile when we don't have a real product photo.
const TYPE_ICONS = {
  combined: "medication",
  progestogen_only: "medication",
  extended_cycle: "calendar_month",
  ring: "radio_button_unchecked",
};

function capitalize(s) {
  return s ? s[0].toUpperCase() + s.slice(1) : s;
}

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

function methodItem(m) {
  return `
    <div class="cat-item">
      ${thumb(m.icon, m.image, "")}
      <span class="cat-item__body">
        <span class="choice__title">${escapeHtml(m.label)}</span>
        <span class="choice__desc">${escapeHtml(m.desc)}</span>
      </span>
    </div>`;
}

function productItem(p, variant) {
  // The backend gives a lowercase name (e.g. "yasmin"); capitalize for display.
  // Append the regimen so users can match what's on their pack.
  const title = `${capitalize(p.name)} <span class="muted">- ${escapeHtml(p.regimen)}</span>`;
  return `
    <div class="cat-item">
      ${thumb(TYPE_ICONS[p.type] || "medication", null, variant)}
      <span class="cat-item__body">
        <span class="choice__title">${title}</span>
        <span class="choice__desc">${escapeHtml(p.description)}</span>
      </span>
    </div>`;
}

function renderProducts(products) {
  // Group by type, then render in the canonical order. Unknown types are
  // dropped silently so a stray backend value can't break the screen.
  const byType = new Map();
  for (const p of products) {
    if (!byType.has(p.type)) byType.set(p.type, []);
    byType.get(p.type).push(p);
  }
  const sections = [];
  for (const type of TYPE_ORDER) {
    const items = byType.get(type);
    if (!items || !items.length) continue;
    const variant = type === "progestogen_only" ? "cat-thumb--alt" : "";
    sections.push(`
      <h2 class="subtitle">${TYPE_LABELS[type]}</h2>
      <div class="list">${items.map((p) => productItem(p, variant)).join("")}</div>
    `);
  }
  return sections.join("");
}

export const CatalogView = {
  render() {
    return {
      title: "Catalog",
      html: `
        <div class="stack" style="gap:var(--space-2)">
          <h1 class="title">Methods & products</h1>
          <p class="muted">Plain-language explanations so you can check what
            you're using.</p>
        </div>

        <h2 class="subtitle">Methods</h2>
        <div class="list">
          ${METHODS.filter((m) => m.id !== "unknown").map(methodItem).join("")}
        </div>

        <div id="catalog-products">
          <div class="empty"><p class="muted">Loading products…</p></div>
        </div>

        <div class="action-bar">
          <button id="catalog-start" class="btn btn--primary btn--block btn--lg">
            Start a check
          </button>
        </div>
      `,
      async onMount(el) {
        el.querySelector("#catalog-start").addEventListener("click", () =>
          router.go("/entry")
        );

        const slot = el.querySelector("#catalog-products");
        let products;
        try {
          products = await api.getProducts();
        } catch (err) {
          slot.innerHTML = `<div class="empty"><p class="muted">Couldn't load products: ${escapeHtml(err.message)}</p></div>`;
          toast(err.message);
          return;
        }
        if (!products || !products.length) {
          slot.innerHTML = `<div class="empty"><p class="muted">No products available right now.</p></div>`;
          return;
        }
        slot.innerHTML = renderProducts(products);
      },
    };
  },
};
