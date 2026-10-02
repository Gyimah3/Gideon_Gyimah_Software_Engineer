"""Readiness rules. Each test pins one rule from the brief."""

from __future__ import annotations

import json
from pathlib import Path

from backend.core.service import check_release
from backend.tests.helpers import check, report

SAMPLE = Path(__file__).resolve().parents[2] / "sample-release.json"


def test_supplied_sample_is_blocked_by_two_problems_with_one_warning() -> None:
    result = check_release(SAMPLE.read_text())

    assert result.verdict == "BLOCKED"
    assert result.release == "customer-demo-v1"
    assert len(result.blockers) == 2
    assert any("payments" in b for b in result.blockers)
    assert any("audit" in b for b in result.blockers)
    assert len(result.warnings) == 1
    assert "copy" in result.warnings[0]


def test_all_required_checks_passing_with_evidence_is_ready() -> None:
    result = check_release(report(check("login"), check("payments", "Payments")))

    assert result.verdict == "READY"
    assert result.blockers == []


def test_optional_not_run_check_warns_but_does_not_block() -> None:
    result = check_release(
        report(check("login"), check("copy", required=False, status="not_run", evidence=""))
    )

    assert result.verdict == "READY"
    assert len(result.warnings) == 1


def test_empty_checks_array_is_blocked() -> None:
    result = check_release(json.dumps({"release": "demo-v1", "checks": []}))

    assert result.verdict == "BLOCKED"
    assert any("required check" in b.lower() for b in result.blockers)


def test_report_with_only_optional_checks_is_blocked() -> None:
    result = check_release(report(check("copy", required=False)))

    assert result.verdict == "BLOCKED"
    assert any("required check" in b.lower() for b in result.blockers)


def test_required_check_with_whitespace_only_evidence_is_blocked() -> None:
    result = check_release(report(check("audit", evidence="   ")))

    assert result.verdict == "BLOCKED"
    assert any("audit" in b and "evidence" in b.lower() for b in result.blockers)


def test_required_check_with_absent_evidence_is_blocked() -> None:
    result = check_release(report(check("audit", evidence=None)))

    assert result.verdict == "BLOCKED"
    assert any("evidence" in b.lower() for b in result.blockers)


def test_failed_required_check_with_blank_evidence_reports_both_problems() -> None:
    result = check_release(report(check("payments", status="failed", evidence="")))

    assert len(result.blockers) == 2
