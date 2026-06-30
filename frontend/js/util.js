/* SafeCycle - tiny shared utilities. */

/** Show a form validation error: reveal message + shake the field. */
export function showFieldError(fieldEl, errorEl, message) {
  errorEl.textContent = message;
  errorEl.hidden = false;
  if (fieldEl) {
    fieldEl.classList.add("is-invalid");
    fieldEl.classList.remove("shake");
    void fieldEl.offsetWidth; // restart the animation
    fieldEl.classList.add("shake");
  }
}

/** Clear a previously shown validation error. */
export function clearFieldError(fieldEl, errorEl) {
  if (errorEl) errorEl.hidden = true;
  if (fieldEl) fieldEl.classList.remove("is-invalid");
}

/** Escape user-supplied text before injecting into innerHTML. */
export function escapeHtml(str) {
  return String(str ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[c]));
}
