"""Phase A: is this data trustworthy?

Answers one question only -- does the parsed input satisfy the data contract?
It knows nothing about readiness. Every error is collected rather than raised on
the first problem, so one load surfaces every issue.

Types are checked by hand rather than through a coercing validation library.
The brief requires *rejecting* a wrong field type, and `"true"` or `1` for
`required` must be invalid data, not silently coerced to True.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from backend.core.models import VALID_STATUSES, Check, Report, Status


@dataclass(frozen=True, slots=True)
class ValidationOutcome:
    report: Report | None
    errors: list[str]


def _is_nonblank_str(value: object) -> bool:
    return isinstance(value, str) and value.strip() != ""


def validate(raw: object) -> ValidationOutcome:
    """Validate already-parsed JSON against the data contract."""
    errors: list[str] = []

    if not isinstance(raw, dict):
        return ValidationOutcome(None, [f"Root must be a JSON object, got {_type_name(raw)}."])

    release = raw.get("release")
    if "release" not in raw:
        errors.append("release is missing.")
    elif not isinstance(release, str):
        errors.append(f"release must be a string, got {_type_name(release)}.")
    elif release.strip() == "":
        errors.append("release must not be blank.")

    if "checks" not in raw:
        errors.append("checks is missing.")
        return ValidationOutcome(None, errors)

    raw_checks = raw["checks"]
    if not isinstance(raw_checks, list):
        errors.append(f"checks must be an array, got {_type_name(raw_checks)}.")
        return ValidationOutcome(None, errors)

    checks: list[Check] = []
    seen_ids: set[str] = set()

    for index, item in enumerate(raw_checks):
        path = f"checks[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{path} must be an object, got {_type_name(item)}.")
            continue
        checks.extend(_validate_check(item, path, seen_ids, errors))

    if errors:
        return ValidationOutcome(None, errors)

    return ValidationOutcome(Report(release=cast(str, release), checks=tuple(checks)), [])


def _validate_check(
    item: dict[str, Any], path: str, seen_ids: set[str], errors: list[str]
) -> list[Check]:
    """Validate one check. Returns it in a list, or an empty list if unusable."""
    before = len(errors)

    check_id = item.get("id")
    if not _is_nonblank_str(check_id):
        errors.append(f"{path}.id must be a nonblank string.")
    elif check_id in seen_ids:
        errors.append(f"{path}.id has a duplicate value {check_id!r}; ids must be unique.")
    else:
        seen_ids.add(cast(str, check_id))

    if not _is_nonblank_str(item.get("name")):
        errors.append(f"{path}.name must be a nonblank string.")

    required = item.get("required")
    # bool before int: in Python True == 1, so an explicit isinstance bool test
    # is the only way to reject 0/1 while accepting true/false.
    if not isinstance(required, bool):
        errors.append(f"{path}.required must be a JSON boolean, got {_type_name(required)}.")

    status = item.get("status")
    if not isinstance(status, str):
        errors.append(f"{path}.status must be a string, got {_type_name(status)}.")
    elif status not in VALID_STATUSES:
        errors.append(f"{path}.status must be one of passed, failed, not_run; got {status!r}.")

    evidence = item.get("evidence")
    if "evidence" in item and not isinstance(evidence, str):
        errors.append(f"{path}.evidence must be a string when present, got {_type_name(evidence)}.")

    if len(errors) > before:
        return []

    return [
        Check(
            id=cast(str, check_id),
            name=cast(str, item["name"]),
            required=cast(bool, required),
            status=cast(Status, status),
            evidence=cast("str | None", evidence),
        )
    ]


def _type_name(value: object) -> str:
    if value is None:
        return "null"
    return {
        bool: "boolean",
        int: "number",
        float: "number",
        str: "string",
        list: "array",
        dict: "object",
    }.get(type(value), type(value).__name__)
