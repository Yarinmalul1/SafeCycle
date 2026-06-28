/* SafeCycle — lightweight toast notification.
   A calm, non-blocking replacement for alert(). Renders into
   #overlay-root, floats above the bottom nav, and auto-dismisses. */

const root = () => document.getElementById("overlay-root");

let hideTimer = null;

export function toast(message, { duration = 2800 } = {}) {
  const r = root();

  // Reuse a single toast node so rapid calls don't stack.
  let el = r.querySelector(".toast");
  if (!el) {
    el = document.createElement("div");
    el.className = "toast";
    el.setAttribute("role", "status");
    el.setAttribute("aria-live", "polite");
    r.appendChild(el);
  }

  el.textContent = message;
  // Restart the enter animation.
  el.classList.remove("toast--in");
  void el.offsetWidth;
  el.classList.add("toast--in");

  clearTimeout(hideTimer);
  hideTimer = setTimeout(() => {
    el.classList.remove("toast--in");
    setTimeout(() => el.remove(), 250);
  }, duration);
}
