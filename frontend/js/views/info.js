/* View: Info / Trust & Legal */
import { openEscalation } from "../escalation.js";

export const InfoView = {
  render() {
    return {
      title: "About & trust",
      html: `
        <h1 class="title">How SafeCycle works</h1>

        <div class="card">
          <strong>Three layers</strong>
          <ol class="muted" style="margin-top:var(--space-2)">
            <li><b>You describe it</b> - in your own words or with a quick card.</li>
            <li><b>A rules engine decides</b> - based on recognised clinical
              guidelines, not guesswork.</li>
            <li><b>We explain it calmly</b> - clear, ordered steps you can act on.</li>
          </ol>
        </div>

        <div class="card">
          <strong>Clinical sources</strong>
          <ul class="muted" style="margin-top:var(--space-2)">
            <li><a href="https://www.fsrh.org/standards-and-guidance/" target="_blank" rel="noopener">FSRH - Faculty of Sexual & Reproductive Healthcare</a></li>
            <li><a href="https://www.who.int/teams/sexual-and-reproductive-health-and-research" target="_blank" rel="noopener">WHO - Sexual & Reproductive Health</a></li>
            <li><a href="https://www.cdc.gov/contraception/" target="_blank" rel="noopener">CDC - Contraception</a></li>
          </ul>
        </div>

        <div class="card">
          <strong>Clinician review</strong>
          <p class="muted" style="margin-top:var(--space-1)">
            Guidance content is intended to be reviewed by a qualified clinician
            before release. The current build uses placeholder logic for
            demonstration and is clearly marked as such.
          </p>
        </div>

        <div class="card">
          <strong>When to get help now</strong>
          <p class="muted" style="margin-top:var(--space-1)">
            Severe pain, heavy bleeding, trouble breathing, or a possible
            pregnancy with feeling unwell - seek medical care.
          </p>
          <button id="info-clinician" class="btn btn--secondary btn--block"
            style="margin-top:var(--space-3)">Talk to a clinician</button>
        </div>

        <div class="card">
          <strong>Privacy</strong>
          <p class="muted" style="margin-top:var(--space-1)">
            No data selling. Saved answers are private to your account.
            Sensitive health prompts use no-retention AI calls. Full privacy
            policy and terms will be linked here before launch.
          </p>
        </div>

        <p class="disclaimer">
          SafeCycle provides general information based on contraceptive
          guidelines. It is not a diagnosis, prescription, or medical advice.
        </p>
      `,
      onMount(el) {
        el.querySelector("#info-clinician").addEventListener("click", () =>
          openEscalation()
        );
      },
    };
  },
};
