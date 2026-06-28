/* SafeCycle - escalation overlay ("Talk to a person").
   Always reachable. Hard-routes urgent cases. Rendered into
   #overlay-root so it floats above any view. */

const root = () => document.getElementById("overlay-root");

export function openEscalation({ urgent = false } = {}) {
  const heading = urgent
    ? "Please seek medical help"
    : "Talk to a clinician";

  root().innerHTML = `
    <div class="overlay" role="dialog" aria-modal="true" aria-labelledby="esc-title">
      <div class="overlay__sheet">
        <h2 id="esc-title" class="subtitle">${heading}</h2>
        <p class="muted" style="margin-top:var(--space-2)">
          SafeCycle gives general information, not medical care. A clinician
          or pharmacist can give advice specific to you.
        </p>

        <div class="stack" style="margin-top:var(--space-4)">
          <div class="card">
            <strong>Seek urgent care if you have:</strong>
            <ul class="muted" style="margin-top:var(--space-2)">
              <li>Severe abdominal or chest pain</li>
              <li>Heavy or unusual bleeding</li>
              <li>Trouble breathing, or a swollen, painful leg</li>
              <li>Signs you might be pregnant and feel unwell</li>
            </ul>
          </div>

          <a class="btn btn--secondary btn--block" href="tel:111">
            Call a non-emergency health line
          </a>
          <a class="btn btn--secondary btn--block"
             href="https://www.nhs.uk/conditions/contraception/" target="_blank" rel="noopener">
            Find contraception services
          </a>
        </div>

        <button type="button" class="btn btn--ghost btn--block"
                id="esc-close" style="margin-top:var(--space-3)">
          Close
        </button>
        <p class="subtle" style="text-align:center;margin-top:var(--space-2)">
          In an emergency, call your local emergency number.
        </p>
      </div>
    </div>
  `;

  const overlay = root().querySelector(".overlay");
  const close = () => (root().innerHTML = "");

  document.getElementById("esc-close").addEventListener("click", close);
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) close();
  });
  document.addEventListener("keydown", function onEsc(e) {
    if (e.key === "Escape") {
      close();
      document.removeEventListener("keydown", onEsc);
    }
  });

  // Focus the dialog for screen readers.
  root().querySelector(".overlay__sheet").focus?.();
}
