"""Safety Filter role.

Guards the pipeline against out-of-scope or unsafe requests before they reach
the guidance engine. Examples of things to catch:
  - requests for content unrelated to contraception guidance
  - scenarios that warrant immediate medical / emergency attention
  - attempts to get the assistant to give unsafe dosing advice

NOTE: skeleton — not yet implemented.
"""

from __future__ import annotations

from models import ParsedScenario


def check(scenario: ParsedScenario) -> tuple[bool, str | None]:
    """Decide whether a scenario is safe to proceed with.

    Returns:
        (is_safe, reason). When `is_safe` is False, `reason` explains why and
        should be surfaced to the user (e.g. "please seek medical attention").
    """
    raise NotImplementedError("Safety filtering is not yet implemented.")
