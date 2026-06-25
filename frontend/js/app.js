/* SafeCycle — app bootstrap.
   Registers routes, starts the router, installs the PWA service worker. */
import { router } from "./router.js";
import { HomeView } from "./views/home.js";
import { MethodView } from "./views/method.js";
import { QuestionsView } from "./views/questions.js";
import { ResultView } from "./views/result.js";
import { HistoryView } from "./views/history.js";
import { InfoView } from "./views/info.js";

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
  .add("/", HomeView)
  .add("/method", MethodView)
  .add("/questions", QuestionsView)
  .add("/result", ResultView)
  .add("/history", HistoryView)
  .add("/info", InfoView)
  .setNotFound(NotFoundView);

router.start();

// PWA: register the service worker (basic offline shell).
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("./service-worker.js").catch(() => {
      /* offline support is optional; ignore failures */
    });
  });
}
