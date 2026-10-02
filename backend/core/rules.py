"""Phase B: should this release ship?

Runs only on a validated Report, so it never inspects a type. Deterministic and
single-pass: the same input always produces the same verdict and the same
ordered reason list.
"""

from __future__ import annotations

from backend.core.models import Report, Result

WARNING_STATUSES = frozenset({"failed", "not_run"})


def evaluate(report: Report) -> Result:
    blockers: list[str] = []
    warnings: list[str] = []

    required = [c for c in report.checks if c.required]

    # Rule 1: covers both the empty checks array and the optional-only report.
    if not required:
        blockers.append(
            "No required check exists. A release needs at least one required check to be READY."
        )

    for check in required:
        # Rules 2 and 3 are independent, so one check can raise both: a failed
        # check with blank evidence has two distinct problems to fix.
        if check.status != "passed":
            blockers.append(
                f"Required check {check.id!r} ({check.name}) has status "
                f"{check.status}, expected passed."
            )
        if not check.has_evidence:
            blockers.append(f"Required check {check.id!r} ({check.name}) is missing evidence.")

    # Rule 4: optional problems inform, they never block.
    for check in report.checks:
        if not check.required and check.status in WARNING_STATUSES:
            warnings.append(
                f"Optional check {check.id!r} ({check.name}) has status {check.status}."
            )

    return Result(
        verdict="READY" if not blockers else "BLOCKED",
        release=report.release,
        checks=report.checks,
        blockers=blockers,
        warnings=warnings,
    )
