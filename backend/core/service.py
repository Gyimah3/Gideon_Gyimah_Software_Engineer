"""Entry point that wires parsing, validation, and evaluation.

Takes raw text rather than parsed JSON so that a malformed document is handled
by exactly one code path, exercised identically by the tests, the API, and the
browser.
"""

from __future__ import annotations

import json

from backend.core.models import Result
from backend.core.rules import evaluate
from backend.core.validation import validate


def check_release(raw_text: str) -> Result:
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        return Result(
            verdict="BLOCKED",
            validation_errors=[f"Invalid JSON: {exc.msg} (line {exc.lineno}, column {exc.colno})."],
        )
    except RecursionError:
        # json.loads raises this, not JSONDecodeError, once nesting exceeds the
        # decoder's limit. Without this clause the API returns a 500, which would
        # break the promise that invalid input is a verdict and never a crash.
        return Result(
            verdict="BLOCKED",
            validation_errors=["Invalid JSON: nesting is too deep to parse."],
        )

    outcome = validate(parsed)
    if outcome.report is None:
        # Invalid data is always BLOCKED. Warnings are suppressed: we will not
        # derive advice from data we have just declared untrustworthy.
        return Result(verdict="BLOCKED", validation_errors=outcome.errors)

    return evaluate(outcome.report)
