"""HTTP contract. One response shape for every input, and no state between calls."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from backend.api.main import app
from backend.tests.helpers import check, report

client = TestClient(app)
SAMPLE = Path(__file__).resolve().parents[2] / "sample-release.json"


def post(raw: str) -> dict[str, Any]:
    response = client.post("/api/evaluate", json={"raw": raw})
    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    return body


def test_sample_report_returns_blocked_with_reasons() -> None:
    body = post(SAMPLE.read_text())

    assert body["verdict"] == "BLOCKED"
    assert body["release"] == "customer-demo-v1"
    assert len(body["blockers"]) == 2
    assert len(body["warnings"]) == 1
    assert len(body["checks"]) == 4


def test_malformed_json_returns_200_with_blocked_not_a_server_error() -> None:
    body = post("{nope")

    assert body["verdict"] == "BLOCKED"
    assert body["validationErrors"] != []
    assert body["release"] is None
    assert body["checks"] == []


def test_a_ready_report_after_a_blocked_one_carries_no_state() -> None:
    post(SAMPLE.read_text())

    body = post(report(check("login")))

    assert body["verdict"] == "READY"
    assert body["blockers"] == []
    assert body["validationErrors"] == []


def test_samples_endpoint_lists_demo_reports_with_their_raw_text() -> None:
    response = client.get("/api/samples")
    assert response.status_code == 200
    samples: list[dict[str, Any]] = response.json()

    assert len(samples) >= 4
    labels = [s["label"] for s in samples]
    assert "Supplied sample" in labels

    supplied = next(s for s in samples if s["label"] == "Supplied sample")
    assert "customer-demo-v1" in supplied["raw"]


def test_every_listed_sample_is_evaluable_and_matches_its_stated_verdict() -> None:
    for sample in client.get("/api/samples").json():
        body = post(sample["raw"])
        assert body["verdict"] == sample["verdict"], sample["label"]
