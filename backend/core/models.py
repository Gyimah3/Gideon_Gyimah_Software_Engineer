"""Immutable value types shared by validation, rules, and the API layer.

Nothing here performs I/O or validation. A `Check` only exists once the raw
input has already satisfied the data contract, so the rules layer never has to
re-check a type.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Status = Literal["passed", "failed", "not_run"]
Verdict = Literal["READY", "BLOCKED"]

VALID_STATUSES: frozenset[str] = frozenset({"passed", "failed", "not_run"})


@dataclass(frozen=True, slots=True)
class Check:
    id: str
    name: str
    required: bool
    status: Status
    evidence: str | None

    @property
    def has_evidence(self) -> bool:
        """Evidence is a supplied reference string; we only test for presence.

        Whitespace-only evidence counts as missing, per the brief. We never
        fetch the reference and never assert anything about its contents.
        """
        return self.evidence is not None and self.evidence.strip() != ""


@dataclass(frozen=True, slots=True)
class Report:
    release: str
    checks: tuple[Check, ...]


@dataclass(frozen=True, slots=True)
class Result:
    """The single shape returned for every input, valid or not.

    On invalid input `release` is None and `checks` is empty, so the UI renders
    from one shape in all cases and can never show a stale verdict.
    """

    verdict: Verdict
    release: str | None = None
    checks: tuple[Check, ...] = ()
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    validation_errors: list[str] = field(default_factory=list)
