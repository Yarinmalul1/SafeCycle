/* SafeCycle — minimal hash-based SPA router.
   No page reloads. Each route maps to a view module that exports
   `render(params)` -> { html, title, showBack, onMount? }. */

const routes = new Map();
let notFound = null;

const headerEl = () => document.getElementById("app-header");
const titleEl = () => document.getElementById("app-title");
const backBtn = () => document.getElementById("back-btn");
const viewEl = () => document.getElementById("view");

export const router = {
  /** Register a route. path e.g. "/", "/method", "/result". */
  add(path, view) {
    routes.set(path, view);
    return this;
  },

  setNotFound(view) {
    notFound = view;
    return this;
  },

  /** Navigate programmatically. */
  go(path) {
    if (location.hash === "#" + path) {
      this.render(); // same route: force re-render
    } else {
      location.hash = path;
    }
  },

  back() {
    history.back();
  },

  start() {
    window.addEventListener("hashchange", () => this.render());
    backBtn().addEventListener("click", () => this.back());
    if (!location.hash) location.hash = "/";
    else this.render();
  },

  parse() {
    // "#/method?foo=bar" -> { path:"/method", params:{foo:"bar"} }
    const hash = location.hash.slice(1) || "/";
    const [path, query = ""] = hash.split("?");
    const params = Object.fromEntries(new URLSearchParams(query));
    return { path: path || "/", params };
  },

  async render() {
    const { path, params } = this.parse();
    const view = routes.get(path) || notFound;
    if (!view) return;

    const out = await view.render(params);
    const main = viewEl();

    main.innerHTML = out.html;
    main.scrollTop = 0;

    // Header: home has no chrome; inner pages get a titled bar + back.
    const isHome = path === "/";
    headerEl().hidden = isHome;
    if (!isHome) {
      titleEl().textContent = out.title || "SafeCycle";
      backBtn().hidden = out.showBack === false;
    }

    // Bottom nav shows on every page except the welcome/landing page.
    document.getElementById("bottom-nav").hidden = isHome;

    // Highlight the active bottom-nav item.
    const navKey =
      path === "/catalog" ? "catalog" :
      path === "/profile" ? "profile" :
      ["/", "/dashboard", "/entry", "/method", "/questions", "/result"].includes(path) ? "home" :
      null;
    document.querySelectorAll(".bottom-nav__item").forEach((a) => {
      if (a.dataset.nav === navKey) a.setAttribute("aria-current", "page");
      else a.removeAttribute("aria-current");
    });

    // Move focus to the view for screen-reader + keyboard users.
    main.focus({ preventScroll: true });

    if (typeof out.onMount === "function") out.onMount(main, params);
  },
};
