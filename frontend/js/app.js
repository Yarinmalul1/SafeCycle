/* SafeCycle - app bootstrap.
   Registers routes, starts the router, installs the PWA service worker. */
import { router } from "./router.js";
import { WelcomeView } from "./views/welcome.js";
import { HomeView } from "./views/home.js";
import { MethodView } from "./views/method.js";
import { QuestionsView } from "./views/questions.js";
import { ResultView } from "./views/result.js";
import { InfoView } from "./views/info.js";
import { CatalogView } from "./views/catalog.js";
import { ProfileView } from "./views/profile.js";

const NotFoundView = {
  render() {
    return {
      title: "Not found",
      html: `
        <div class="empty">
          <p class="lead">That page doesn't exist.</p>
          <a class="btn btn--primary" href="#/" style="margin-top:var(--space-4)">Go home</a>
        </div>`,
    };
  },
};

router
  .add("/", WelcomeView)
  .add("/entry", HomeView)
  .add("/method", MethodView)
  .add("/questions", QuestionsView)
  .add("/result", ResultView)
  .add("/info", InfoView)
  .add("/catalog", CatalogView)
  .add("/profile", ProfileView)
  .setNotFound(NotFoundView);

router.start();

// Service worker is DISABLED during active development so changes show
// immediately (no stale cache). This also unregisters any worker a browser
// already installed and clears its caches. Re-enable for production PWA/offline.
if ("serviceWorker" in navigator) {
  navigator.serviceWorker
    .getRegistrations()
    .then((regs) => regs.forEach((r) => r.unregister()))
    .catch(() => {});
}
if (window.caches) {
  caches.keys().then((keys) => keys.forEach((k) => caches.delete(k))).catch(() => {});
}
