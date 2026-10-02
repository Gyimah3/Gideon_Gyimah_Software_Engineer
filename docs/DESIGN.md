# Release Evidence Checker — Design

Date: 2026-10-02
Author: Gideon Gyimah
Context: Zof AI Software Engineer practical exercise. 75 min build + 15 min demo.
Status: written before implementation and reconciled against the code afterwards.
Time-boxed, so this doc stands in for a full spec.

---

## 1. Problem restated

Read a JSON software release report. Validate its shape against a strict data
contract. Apply readiness rules. Report one prominent verdict (READY or BLOCKED),
every blocking reason, and warnings. Never crash. Never leave a stale READY on
screen. Let the user load another report without touching source code.

Evidence is a supplied reference string only. We never fetch it and never claim
we verified its contents.

The supplied sample must return BLOCKED: `payments` failed, `audit` has blank
evidence. `copy` (optional, failed) is a warning, not a third blocker.

---

## 2. Engineering principles

| # | Principle | What it means here |
|---|---|---|
| 1 | Correctness first | The readiness rules are the product. UI and transport are plumbing. |
| 2 | Pure core, thin shell | Validation and evaluation are pure functions with zero I/O. FastAPI and React are adapters around them. The core is testable with no HTTP and no browser. |
| 3 | Test by default | Each rule in the brief maps to a named pytest case. Core tests are written alongside the core, before the UI. |
| 4 | Strict typing, no coercion | `required` must be a real JSON boolean. `"true"` and `1` are invalid data. We validate the raw `json.loads` output by hand so no framework silently coerces a bad type into a good one. mypy strict on the core. |
| 5 | Fail loud, fail clean | Invalid input yields BLOCKED plus every error found. Never a partial render. Never a stale verdict. |
| 6 | Collect, don't fast-fail | One load surfaces every problem, not just the first. Faster for the user than fix-reload-repeat. |
| 7 | Evidence is a string, not a claim | Nonblank check only. No fetching, no verification language anywhere in UI or README. |
| 8 | Efficiency by default | Single pass per phase over the checks array. No dependency we cannot justify. Small files, one purpose each. |
| 9 | Honest README | Limitations, assumptions, AI use, and what was verified by hand are stated plainly. |

---

## 3. Developer quality and experience

| Concern | Choice | Why |
|---|---|---|
| Packaging / env | **uv** | One tool for venv, resolution, lock, and run. `uv sync` is reproducible and cold-starts in seconds, not minutes. Safe to run live in a demo. |
| Lint + format | **ruff** | Lint and format in a single Rust binary. Replaces flake8 + isort + black. Near-zero config, instant feedback. |
| Static types | **mypy --strict** on the core | The rules module is the entire risk surface. Strict mode catches `None` and `Any` leaks in validation before a test has to. |
| Runtime type safety | **hand-rolled validator**, not pydantic coercion | The brief requires *rejecting* wrong field types. Pydantic's default behaviour coerces `"true"` to `True` and `1` to `True`, which would let invalid data pass as valid. Explicit `isinstance` checks are both correct and easy to demonstrate live. |
| Tests | **pytest** | One named test per rule in the brief, so the test names read as the requirements. Plus FastAPI `TestClient` for the endpoint contract. |
| API | **FastAPI** | Typed request and response models, auto `/docs` page useful in the demo, trivially testable. |
| Frontend | **React + TypeScript + Vite** | Types mirror the API contract so a contract drift is a compile error. Vite dev server starts instantly. |
| Frontend state | **plain `useState`**, no state library | One form, one result. A router or Redux would be bloat I could not justify in 60 minutes. |
| Styling | **one plain CSS file** | The brief ranks behaviour over polish. Readable, no build step, no framework. |

---

## 4. Architecture

```
backend/
  core/models.py        frozen dataclasses: Check, Report, Verdict, Result
  core/validation.py    pure: validate(raw: object) -> ValidationOutcome
  core/rules.py         pure: evaluate(report: Report) -> Result
  api/main.py           POST /api/evaluate, GET /api/samples
  tests/test_validation.py
  tests/test_rules.py
  tests/test_api.py
frontend/src/
  App.tsx
  api.ts                fetch wrapper
  types.ts              mirrors the API response
  components/InputPanel.tsx
  components/VerdictBanner.tsx
  components/CheckTable.tsx
README.md
sample-release.json
docs/DESIGN.md
```

**Data flow**

```
textarea / file upload
   -> POST /api/evaluate  { "raw": "<json text>" }
   -> json.loads            (JSONDecodeError -> BLOCKED, parse error)
   -> validate(raw)         (structural errors -> BLOCKED, listed)
   -> evaluate(report)      (readiness rules -> verdict, blockers, warnings)
   -> JSON response
   -> React clears prior result, then renders the new one
```

The frontend sends the *raw text*, not parsed JSON. That keeps a single source of
truth for parse errors: the backend. The browser never decides whether JSON is
well-formed, so the UI and the tests exercise the same code path.

---

## 5. Technical approach

### 5.1 Two phases, strictly ordered

**Phase A — validation (is this data trustworthy?).**
Walks the raw parsed object and answers one question: does it satisfy the data
contract? It knows nothing about readiness.

Checks performed, all errors collected:

- root is an object
- `release` present, is a `str`, and is nonblank after strip
- `checks` present and is a `list`
- each element is an object
- `id` is a nonblank `str`; ids unique across the array
- `name` is a nonblank `str`
- `required` is a real `bool` (`isinstance(v, bool)`, which also rejects `0`/`1`
  because the bool check runs before any int check and we never accept int)
- `status` is a `str` and is exactly one of `passed`, `failed`, `not_run`
- `evidence` is absent, or is a `str`
- no attempt is made to interpret evidence content

Every error carries a path (`checks[2].required`) and a human message, so the UI
can list them without further processing.

**Phase B — readiness evaluation (should this release ship?).**
Runs only if Phase A produced zero errors. Operates on typed `Check` objects, so
it never re-checks types. Rules, in order:

1. If no check has `required is True` -> blocker: no required check exists.
   (This covers both the empty array and the optional-only report. One rule, two
   cases from the brief.)
2. For each required check with `status != "passed"` -> blocker naming the id and
   the actual status.
3. For each required check whose evidence is missing or blank after strip ->
   blocker naming the id. Evaluated independently of rule 2, so a check can
   produce two blockers, which matches the sample's expectation that each
   distinct problem is reported.
4. For each optional check with `status` in `failed` or `not_run` -> warning.
5. Verdict is READY if and only if `blockers` is empty.

### 5.2 Why validation gates evaluation

If the shape is wrong, the readiness output would be guesswork. So a Phase A
failure returns BLOCKED with the validation errors and an **empty warnings list** —
we do not emit warnings derived from data we just declared untrustworthy. This
satisfies "invalid data is always BLOCKED, including invalid data in an optional
check" without needing a special case for optional checks.

### 5.3 Response contract

```json
{
  "verdict": "BLOCKED",
  "release": "customer-demo-v1",
  "checks": [ { "id": "...", "name": "...", "required": true,
                "status": "failed", "evidence": "..." } ],
  "blockers": ["Required check 'payments' has status failed, expected passed."],
  "warnings": ["Optional check 'copy' has status failed."],
  "validationErrors": []
}
```

On invalid input, `release` is `null`, `checks` is `[]`, `warnings` is `[]`, and
`validationErrors` carries the detail. The frontend renders from one shape in all
cases, which is what keeps a stale READY impossible: the whole result object is
replaced on every submit, and set to `null` before the request fires.

---

## 6. Evaluation engine: single-pass deterministic ("System 1")

The engine is deliberately **System 1**: fast, single-pass, deterministic,
no second opinion, no model in the loop.

| Property | Decision |
|---|---|
| Inference | None. No LLM, no heuristics, no scoring, no thresholds. |
| Passes over data | One per phase. Validation walks the checks once; evaluation walks them once. |
| Determinism | Same input always yields the same verdict and the same ordered reason list. |
| Order of reasons | Stable: validation errors in document order; blockers in rule order then document order; warnings in document order. The tests assert which reasons appear rather than their exact order, so the ordering is a property of the output a reader can rely on, not something the suite pins. |
| Ambiguity handling | None permitted. Every rule in the brief is a total function over the typed input. Where the brief is silent (e.g. evidence format), we do nothing rather than infer. |
| Explainability | Each blocker is generated at the site of the rule that produced it, so every line of output traces to one line of code. Required for the live demo. |

**Does this contradict the brief?** No. The brief specifies exact, enumerable
conditions — fixed status values, boolean required flag, nonblank string tests.
There is no fuzzy judgement anywhere in it. A deliberative or probabilistic
second stage would add nondeterminism to a problem that has a single correct
answer, which would make the verdict harder to trust and harder to test. So
System 1 is not a shortcut here; it is the correct engine for the spec.

**Where a System 2 stage would belong, and why it is out of scope.** If the brief
had asked us to judge whether evidence *actually supports* a check — read a test
report, assess coverage, decide if a link is relevant — that is a judgement task
and would need a deliberative stage, plus a human review path. The brief
explicitly forbids it: evidence is a supplied reference string and we must not
claim to have verified it. Noted in the README as a non-goal, not a limitation.

---

## 7. Test matrix

Automated, pytest. Each case is named after the rule it pins.

| # | Input | Expected |
|---|---|---|
| 1 | supplied `sample-release.json` | BLOCKED; exactly 2 blockers (`payments` failed, `audit` blank evidence); exactly 1 warning (`copy`) |
| 2 | all required checks passed with nonblank evidence | READY; 0 blockers |
| 3 | required checks all pass, one optional `not_run` | READY; 1 warning — warnings never block |
| 4 | `checks: []` | BLOCKED; no-required-check blocker |
| 5 | only optional checks, all passing | BLOCKED; no-required-check blocker |
| 6 | malformed JSON (`{"release":`) | BLOCKED; parse error; no crash |
| 7 | `"required": "true"` (string) | BLOCKED; type validation error |
| 8 | duplicate `id` values | BLOCKED; duplicate-id error |
| 9 | required check with `evidence: "   "` | BLOCKED; blank-evidence blocker |
| 10 | `"status": "skipped"` | BLOCKED; unknown-status error |
| 11 | invalid data inside an **optional** check | BLOCKED; validation error; warnings empty |
| 12 | `release: "  "` | BLOCKED; blank release error |
| 13 | API: POST sample then POST valid-ready | second response is READY — no state carried between requests |

---

## 8. Known limitations (carried to README)

- Evidence is never fetched or verified. Only its presence and nonblankness.
- No persistence. Each submit is stateless.
- No authentication, no deployment, no database. Not required by the brief.
- Single report per request. No batch or diff view.
- Frontend is unstyled beyond a single readable CSS file.
- No i18n, no accessibility audit beyond semantic HTML and labelled inputs.

## 9. Non-goals

- Judging whether evidence substantiates a check. Explicitly forbidden.
- Production deployment gating. This is a completeness-checking prototype.
