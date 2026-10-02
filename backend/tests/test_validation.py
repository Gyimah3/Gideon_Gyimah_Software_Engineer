"""Data-contract validation. Invalid data is always BLOCKED, warnings suppressed."""

from __future__ import annotations

import json

from backend.core.service import check_release
from backend.tests.helpers import check, report


def test_malformed_json_is_blocked_with_a_parse_message() -> None:
    result = check_release('{"release":')

    assert result.verdict == "BLOCKED"
    assert len(result.validation_errors) == 1
    assert "json" in result.validation_errors[0].lower()
    assert result.release is None
    assert result.checks == ()


def test_non_boolean_required_flag_is_invalid_data() -> None:
    raw = json.dumps(
        {
            "release": "demo-v1",
            "checks": [{**json.loads(report(check()))["checks"][0], "required": "true"}],
        }
    )

    result = check_release(raw)

    assert result.verdict == "BLOCKED"
    assert any("required" in e for e in result.validation_errors)


def test_integer_one_is_not_accepted_as_required_true() -> None:
    raw = report(check()).replace('"required": true', '"required": 1')

    result = check_release(raw)

    assert result.verdict == "BLOCKED"
    assert any("required" in e for e in result.validation_errors)


def test_duplicate_check_ids_are_invalid_data() -> None:
    result = check_release(report(check("login"), check("login", "Second login")))

    assert result.verdict == "BLOCKED"
    assert any("duplicate" in e.lower() for e in result.validation_errors)


def test_unknown_status_is_invalid_data() -> None:
    result = check_release(report(check(status="skipped")))

    assert result.verdict == "BLOCKED"
    assert any("status" in e for e in result.validation_errors)


def test_blank_release_name_is_invalid_data() -> None:
    result = check_release(report(check(), release="   "))

    assert result.verdict == "BLOCKED"
    assert any("release" in e for e in result.validation_errors)


def test_invalid_data_in_an_optional_check_blocks_and_suppresses_warnings() -> None:
    result = check_release(report(check("login"), check("copy", required=False, status="nope")))

    assert result.verdict == "BLOCKED"
    assert result.validation_errors != []
    assert result.warnings == []


def test_root_that_is_not_an_object_is_invalid_data() -> None:
    result = check_release("[1, 2, 3]")

    assert result.verdict == "BLOCKED"
    assert result.validation_errors != []


def test_missing_checks_key_is_invalid_data() -> None:
    result = check_release(json.dumps({"release": "demo-v1"}))

    assert result.verdict == "BLOCKED"
    assert any("checks" in e for e in result.validation_errors)


def test_non_string_evidence_is_invalid_data() -> None:
    raw = report(check()).replace('"evidence": "run-1"', '"evidence": 42')

    result = check_release(raw)

    assert result.verdict == "BLOCKED"
    assert any("evidence" in e for e in result.validation_errors)


def test_every_validation_error_is_reported_not_just_the_first() -> None:
    result = check_release(report(check(status="skipped"), check("c2", "", status="nope")))

    assert len(result.validation_errors) >= 3


def test_validation_errors_name_the_path_of_the_offending_field() -> None:
    result = check_release(report(check(status="skipped")))

    assert any("checks[0].status" in e for e in result.validation_errors)


def test_deeply_nested_json_is_blocked_not_a_crash() -> None:
    """json.loads raises RecursionError, not JSONDecodeError, past a nesting depth."""
    result = check_release("[" * 200_000 + "]" * 200_000)

    assert result.verdict == "BLOCKED"
    assert result.validation_errors != []
