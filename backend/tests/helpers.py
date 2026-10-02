"""Builders that keep test inputs readable and intent-revealing."""

from __future__ import annotations

import json
from typing import Any


def check(
    check_id: str = "c1",
    name: str = "A check",
    *,
    required: bool = True,
    status: str = "passed",
    evidence: str | None = "run-1",
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "id": check_id,
        "name": name,
        "required": required,
        "status": status,
    }
    if evidence is not None:
        body["evidence"] = evidence
    return body


def report(*checks: dict[str, Any], release: str = "demo-v1") -> str:
    return json.dumps({"release": release, "checks": list(checks)})
