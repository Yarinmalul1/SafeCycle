"""Question Generator role.

When a parsed scenario is missing information the logic engine needs, this role
produces a single, clear follow-up question to ask the user — one field at a
time, in a sensible order.

The flow is deterministic: given the same known context, it always asks for the
same next missing field. The engine needs a product, a pack week, and how many
pills were missed (or how late the pill was), so those are the steps.
"""

from __future__ import annotations

from collections.abc import Callable

from models import AskQuestionRequest, ParsedScenario, QuestionResult


def _missed_known(ctx: ParsedScenario) -> bool:
    """We have enough on the lapse if either a missed count or lateness is set."""
    return ctx.pillsMissed is not None or ctx.hoursLate is not None


# Ordered intake flow: (field name, "is this still missing?", question text).
# The first step whose predicate is True is the next question to ask.
FLOW: list[tuple[str, Callable[[ParsedScenario], bool], str]] = [
    (
        "product",
        lambda ctx: not ctx.product,
        "Which contraceptive pill are you taking? (for example, Yasmin)",
    ),
    (
        "cycleWeek",
        lambda ctx: ctx.cycleWeek is None,
        "Which week of your pill pack are you in (1-4)?",
    ),
    (
        "pillsMissed",
        lambda ctx: not _missed_known(ctx),
        "How many pills did you miss, or how many hours late were you?",
    ),
]


def generate(request: AskQuestionRequest) -> QuestionResult:
    """Pick the next clarifying question for an in-progress scenario.

    Args:
        request: The user's intent plus what is already known.

    Returns:
        A `QuestionResult`. When every required field is known, `question` and
        `fieldToFill` are null and `questionNumber` points past the last step.
    """
    ctx = request.existingContext
    for number, (field, is_missing, text) in enumerate(FLOW, start=1):
        if is_missing(ctx):
            return QuestionResult(
                question=text,
                fieldToFill=field,
                questionNumber=number,
            )

    # Nothing missing — enough to run the engine.
    return QuestionResult(
        question=None,
        fieldToFill=None,
        questionNumber=len(FLOW) + 1,
    )


def next_question(scenario: ParsedScenario) -> str | None:
    """Convenience wrapper: just the next question string, or None if complete."""
    result = generate(
        AskQuestionRequest(userIntent="(unspecified)", existingContext=scenario)
    )
    return result.question
