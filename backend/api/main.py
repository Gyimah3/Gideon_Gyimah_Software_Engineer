"""HTTP adapter. Holds no logic beyond shaping the core Result for the browser."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.core.models import Result
from backend.core.service import check_release

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"

app = FastAPI(title="Release Evidence Checker", version="0.1.0")

# The Vite dev server runs on a different port during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["POST"],
    allow_headers=["*"],
)


class EvaluateRequest(BaseModel):
    """Raw document text. The browser never decides whether JSON is well-formed."""

    raw: str


def _serialise(result: Result) -> dict[str, Any]:
    return {
        "verdict": result.verdict,
        "release": result.release,
        "checks": [asdict(c) for c in result.checks],
        "blockers": result.blockers,
        "warnings": result.warnings,
        "validationErrors": result.validation_errors,
    }


# Demo reports offered as one-click buttons in the UI. Each is read from the
# fixtures on disk, so the page and the test suite use the same files and cannot
# drift apart.
SAMPLES: tuple[tuple[str, str], ...] = (
    ("Supplied sample", "sample-release.json"),
    ("All required passing", "fixtures/ready-release.json"),
    ("Malformed JSON", "fixtures/malformed.json"),
    ("Invalid optional check", "fixtures/invalid-optional-check.json"),
    ("Only optional checks", "fixtures/optional-only.json"),
)


@app.get("/api/samples")
def list_samples() -> list[dict[str, Any]]:
    """Label, raw text, and expected verdict for each demo report."""
    listed: list[dict[str, Any]] = []
    for label, relative in SAMPLES:
        path = PROJECT_ROOT / relative
        if not path.is_file():
            continue
        raw = path.read_text()
        listed.append({"label": label, "raw": raw, "verdict": check_release(raw).verdict})
    return listed


@app.post("/api/evaluate")
def evaluate_report(request: EvaluateRequest) -> dict[str, Any]:
    """Always 200. Invalid input is a BLOCKED verdict, not an HTTP error."""
    return _serialise(check_release(request.raw))


# Optional single-process mode: serves the built frontend when `npm run build`
# has been run. Absent in development, where Vite serves the UI itself.
if FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(FRONTEND_DIST / "index.html")
