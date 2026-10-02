# Release Evidence Checker

Reads a JSON software release report, displays its checks, and explains whether the
release is **READY** or **BLOCKED**.

Prototype with fictional data. Not production deployment software.

## At a glance

```bash
uv sync && (cd frontend && npm install && npm run build)
uv run uvicorn backend.api.main:app --port 8010      # open http://127.0.0.1:8010/
uv run pytest -q                                      # 25 tests
```

- **Deliverables:** the app is `backend/` and `frontend/`; tests are `TESTS.md` and
  `backend/tests/`; this file is the README.
- **Readiness in one line:** a release is READY only if the data is valid, at least
  one required check exists, and every required check passed with nonblank evidence.
- **Evidence is never fetched.** Only presence and nonblankness are checked. This
  tool verifies the paperwork is complete, not that the work was done.
- **Decision logic:** 178 lines in `backend/core/validation.py` and
  `backend/core/rules.py`. Neither performs I/O.

Everything below is detail: the rules in full, design decisions, assumptions,
limitations, and what I verified by hand.

---

## Launch instructions

Prerequisites: [uv](https://docs.astral.sh/uv/) and Node.js 18+. Both are already
installed on this machine (`uv 0.12.1`, `node v24.5.0`).

### Option A — single process (recommended for the demo)

```bash
cd Zof_AI_Software_Engineer_Challenge
uv sync                                # install Python dependencies
cd frontend && npm install && npm run build && cd ..
uv run uvicorn backend.api.main:app --port 8010
```

Open **http://127.0.0.1:8010/**

> Port 8010, not 8000: port 8000 was already occupied by an unrelated application
> on this machine. Any free port works — pass a different `--port` and, for
> Option B, update the proxy target in `frontend/vite.config.ts`.

### Option B — two processes (hot reload, for development)

```bash
# terminal 1
uv run uvicorn backend.api.main:app --port 8010 --reload
# terminal 2
cd frontend && npm run dev
```

Open **http://localhost:5173/**. Vite proxies `/api` to port 8010.

### Run the tests

```bash
uv run pytest -q          # 25 tests
uv run mypy               # strict type check
uv run ruff check backend # lint
cd frontend && npm run typecheck
```

### Using the app

Three ways in, all feeding the same submit path:

- **Try buttons** at the top load a demo report and check it in one click. The
  backend reads them from the fixture files on disk (`GET /api/samples`), so the
  page and the test suite can never drift apart. Each button shows the verdict it
  expects.
- **Load JSON file** opens a file picker for any report on disk.
- **Paste** into the text box and press **Check release**, or `⌘`+`Enter` from
  inside the box.

Load a different report and check again to recalculate — no source changes needed.
A summary line under the verdict counts required, optional, blocking and warning
items. The check button is disabled while the box is empty.

---

## Readiness logic

Two phases, strictly ordered.

**Phase A — validation** (`backend/core/validation.py`) asks only: does this data
satisfy the contract? It collects *every* error rather than stopping at the first,
so one load shows all problems. It checks: root is an object; `release` is a
nonblank string; `checks` is an array; each check has a nonblank string `id`
(unique across the array), a nonblank string `name`, a `required` that is a real
JSON boolean, a `status` that is exactly `passed`/`failed`/`not_run`, and an
`evidence` that is absent or a string.

If Phase A finds anything, the verdict is **BLOCKED** with the validation errors,
and **warnings are suppressed** — we will not derive advice from data we have just
declared untrustworthy. That single decision satisfies "invalid data in an optional
check must BLOCK" without any special case for optional checks.

**Phase B — readiness** (`backend/core/rules.py`) runs only on validated data, so it
never inspects a type:

1. No check has `required: true` → blocker. One rule covers both the empty `checks`
   array and the optional-only report.
2. Each required check with `status != passed` → blocker.
3. Each required check whose evidence is absent or blank after `strip()` → blocker.
   Evaluated independently of rule 2, so a failed check with blank evidence reports
   two distinct problems to fix.
4. Each optional check with status `failed` or `not_run` → warning. Never a blocker.
5. Verdict is READY if and only if there are no blockers.

Deterministic and single-pass. Same input always yields the same verdict and the
same ordered reason list — no inference, no heuristics, no thresholds, no model in
the loop. The brief's conditions are all exactly enumerable, so there is nothing to
judge.

### The supplied sample

`sample-release.json` returns **BLOCKED** with exactly two blockers and one warning:

- blocker: `payments` has status `failed`
- blocker: `audit` is missing evidence
- warning: `copy` is optional and failed — a warning, not a third blocker

---

## Design notes worth knowing

**Why a hand-written validator instead of Pydantic for the report shape.** The brief
requires *rejecting* wrong field types. Pydantic's default behaviour coerces
`"true"` into `True`, which would let invalid data pass as valid. Explicit
`isinstance` checks are correct here, and they are easy to point at and explain.
Pydantic is still used for the HTTP request envelope, where coercion is harmless.

**Why `isinstance(x, bool)` rather than a truthiness test.** In Python `True == 1`,
so only an explicit `bool` check rejects `"required": 1` while accepting
`true`/`false`.

**Why the browser posts raw text, not parsed JSON.** Malformed input is then handled
by exactly one code path, exercised identically by the tests, the API, and the
browser. The UI never decides whether JSON is well-formed.

**Why a stale READY is structurally impossible.** `backend/core/models.Result` is a
single shape returned for every input (on invalid data, `release` is `null` and
`checks` is empty). The frontend sets `result` to `null` *before* each request
fires, then replaces it wholesale. There is no partial update path that could leave
an old verdict on screen.

**Pure core, thin shell.** `backend/core/` performs no I/O and imports nothing from
FastAPI. 20 of the 25 tests exercise it with no HTTP involved.

---

## Assumptions

- A report with a valid shape but zero checks is BLOCKED via the "no required check"
  rule. The brief lists the empty array and the optional-only case separately; they
  reduce to the same condition.
- A required check that both failed *and* has blank evidence produces two blockers,
  not one. Each distinct problem a user must fix gets its own line.
- Unknown extra fields on a check or on the root are ignored, not rejected. The
  brief enumerates required fields and does not forbid additions.
- Evidence format is unconstrained. The brief states no particular URL format is
  required, so only presence and nonblankness are checked.
- Validation errors and blockers appear in document order within rule order. Stable
  ordering lets tests assert exact output rather than set membership.

## Known limitations

- **Evidence is never fetched or verified.** Only its presence and nonblankness are
  checked. Nothing in the UI or the output claims otherwise.
- No persistence. Every submit is stateless; nothing is stored between requests.
- One report per request. No batch mode, no diff between two reports.
- No authentication, database, or deployment. None are required by the brief.
- The frontend has no automated tests. Its behaviour was verified by hand in a
  browser (see below) and its types are checked by `tsc --strict`. With more time,
  the next thing I would add is a Vitest + Testing Library test asserting that a
  BLOCKED result replaces a prior READY result in the DOM.
- CORS allows `localhost:5173` only, which is correct for local development and
  would need revisiting for any other origin.
- Very large reports are evaluated in one synchronous pass. Fine at the scale the
  brief implies; not streamed.

## Non-goal (deliberately not built)

Judging whether evidence *substantiates* a check — reading a linked test report,
assessing coverage, deciding if a reference is relevant — is a judgement task, not a
completeness check. The brief explicitly forbids it. It would also be the one place
in this problem where a deliberative, human-reviewed stage would be warranted. It is
out of scope by instruction, not an oversight.

## Tools and AI used

- **Claude Code (Opus 5)** — used throughout: to draft the design document, scaffold
  the project, write the test suite and implementation, and draft this README. Every
  design decision recorded in `docs/DESIGN.md` was my call; I directed the stack,
  the two-phase architecture, the hand-written-validator decision, and the test
  matrix, and I reviewed all generated code.
- **uv** (packaging), **ruff** (lint + format), **mypy --strict** (types), **pytest**
  (tests), **FastAPI** + **uvicorn** (API), **React** + **TypeScript** + **Vite**
  (frontend).
- No paid service, cloud deployment, database, external API, or production
  credentials. All data is fictional.

## What I verified myself

- Ran `uv run pytest -q` → **25 passed**. I watched the core suite fail first
  (`ModuleNotFoundError: No module named 'backend.core.service'`) before any
  implementation existed.
- Ran `uv run mypy` → **Success: no issues found in 13 source files**.
- Ran `uv run ruff check backend` → **All checks passed**.
- Ran `cd frontend && npm run build` → `tsc --noEmit` clean, Vite build succeeded.
- Posted all 8 fixtures to the running API and read each verdict and reason by hand;
  transcript in `TESTS.md`.
- Drove the built UI in a real Chrome tab through nine cases and read the rendered
  DOM back each time: the sample report, an all-required-passing report, malformed
  JSON, a file loaded through the file input, each of the one-click Try buttons, the
  keyboard shortcut, and the disabled-while-empty state. The malformed case reported
  `readyBannerStillPresent: false`, which is direct evidence that invalid input does
  not leave an earlier READY result on screen. Full transcript in `TESTS.md` §C.

**One honesty note on process:** three of the five tests in
`backend/tests/test_api.py` were written before their implementation but in the same
step, so I did not watch those three fail in isolation. The 20 core tests in
`test_rules.py` and `test_validation.py`, and the two later `/api/samples` tests,
were properly observed failing first.

## Layout

```
backend/core/models.py       immutable value types; Check.has_evidence
backend/core/validation.py   Phase A -- data contract, collects all errors
backend/core/rules.py        Phase B -- readiness rules
backend/core/service.py      parse -> validate -> evaluate
backend/api/main.py          POST /api/evaluate, GET /api/samples; serves the built UI
backend/tests/               25 tests (8 rules, 12 validation, 5 api)
frontend/src/App.tsx         state, submit, clears prior result first
frontend/src/components/     VerdictBanner, ReasonList, CheckTable, InputPanel,
                             SampleBar, ResultSummary
fixtures/                    reports used in the manual test log and the Try buttons
docs/DESIGN.md               design, principles, tooling rationale
TESTS.md                     reproducible test cases with expected vs actual
```
