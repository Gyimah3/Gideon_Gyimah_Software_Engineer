# Tests

Two layers: an automated suite (25 pytest cases) and a manual HTTP log over the
running API. Both were run on 2026-10-02 and the actual output below is copied from
the terminal, not retyped from memory.

## A. Automated suite

```
$ uv run pytest -q
.......................                                                  [100%]
25 passed, 1 warning in 0.17s
```

(The one warning is a Starlette deprecation notice about `httpx` in its test client.
It comes from a dependency, not from this code.)

```
$ uv run mypy
Success: no issues found in 13 source files

$ uv run ruff check backend
All checks passed!

$ cd frontend && npm run build
tsc --noEmit && vite build  -- clean, built in 291ms
```

### Case map

Every rule in the brief is pinned by a named test. `backend/tests/test_rules.py`:

| Test | Input | Expected | Actual |
|---|---|---|---|
| `test_supplied_sample_is_blocked_by_two_problems_with_one_warning` | `sample-release.json` | BLOCKED, 2 blockers (`payments`, `audit`), 1 warning (`copy`) | pass |
| `test_all_required_checks_passing_with_evidence_is_ready` | 2 required checks, passed, with evidence | READY, 0 blockers | pass |
| `test_optional_not_run_check_warns_but_does_not_block` | 1 required passed + 1 optional `not_run` | READY, 1 warning | pass |
| `test_empty_checks_array_is_blocked` | `{"release":"demo-v1","checks":[]}` | BLOCKED, no-required-check | pass |
| `test_report_with_only_optional_checks_is_blocked` | 1 optional check only | BLOCKED, no-required-check | pass |
| `test_required_check_with_whitespace_only_evidence_is_blocked` | required check, `evidence: "   "` | BLOCKED, missing-evidence | pass |
| `test_required_check_with_absent_evidence_is_blocked` | required check, `evidence` key absent | BLOCKED, missing-evidence | pass |
| `test_failed_required_check_with_blank_evidence_reports_both_problems` | required check, failed + blank evidence | exactly 2 blockers | pass |

`backend/tests/test_validation.py`:

| Test | Input | Expected | Actual |
|---|---|---|---|
| `test_malformed_json_is_blocked_with_a_parse_message` | `{"release":` | BLOCKED, 1 parse error, `release` null, `checks` empty | pass |
| `test_non_boolean_required_flag_is_invalid_data` | `"required": "true"` | BLOCKED, error naming `required` | pass |
| `test_integer_one_is_not_accepted_as_required_true` | `"required": 1` | BLOCKED (Python's `True == 1` must not leak) | pass |
| `test_duplicate_check_ids_are_invalid_data` | two checks with `id: "login"` | BLOCKED, duplicate error | pass |
| `test_unknown_status_is_invalid_data` | `"status": "skipped"` | BLOCKED, status error | pass |
| `test_blank_release_name_is_invalid_data` | `"release": "   "` | BLOCKED, release error | pass |
| `test_invalid_data_in_an_optional_check_blocks_and_suppresses_warnings` | valid required check + optional check with bad status | BLOCKED, `warnings == []` | pass |
| `test_root_that_is_not_an_object_is_invalid_data` | `[1, 2, 3]` | BLOCKED | pass |
| `test_missing_checks_key_is_invalid_data` | `{"release": "demo-v1"}` | BLOCKED, error naming `checks` | pass |
| `test_non_string_evidence_is_invalid_data` | `"evidence": 42` | BLOCKED, evidence error | pass |
| `test_every_validation_error_is_reported_not_just_the_first` | two checks, three defects | at least 3 errors | pass |
| `test_validation_errors_name_the_path_of_the_offending_field` | bad status on check 0 | message contains `checks[0].status` | pass |

`backend/tests/test_api.py`:

| Test | Input | Expected | Actual |
|---|---|---|---|
| `test_sample_report_returns_blocked_with_reasons` | POST sample | 200, BLOCKED, 2 blockers, 1 warning, 4 checks | pass |
| `test_malformed_json_returns_200_with_blocked_not_a_server_error` | POST `{nope` | HTTP 200 (not 500), BLOCKED | pass |
| `test_a_ready_report_after_a_blocked_one_carries_no_state` | POST sample, then POST a READY report | second is READY with no leftover reasons | pass |

| `test_samples_endpoint_lists_demo_reports_with_their_raw_text` | GET `/api/samples` | at least 4 samples, one labelled "Supplied sample", carrying its raw text | pass |
| `test_every_listed_sample_is_evaluable_and_matches_its_stated_verdict` | every sample the endpoint offers, POSTed back to `/api/evaluate` | each one's actual verdict equals the verdict advertised on its button | pass |

The last of those is worth noting: the UI's one-click buttons advertise a verdict,
and this test re-evaluates every one of them to prove the label is not a lie. If a
fixture file changed, it would fail.

`test_a_ready_report_after_a_blocked_one_carries_no_state` is the automated guard
against a stale verdict on the server side; the browser-side guard was verified by
hand (section C).

## B. Manual HTTP log

Server: `uv run uvicorn backend.api.main:app --port 8010`. Each fixture was POSTed to
`/api/evaluate`. Output copied verbatim.

```
=== sample-release.json  -> HTTP 200  BLOCKED
   [blockers] Required check 'payments' (Payment workflow) has status failed, expected passed.
   [blockers] Required check 'audit' (Audit trail) is missing evidence.
   [warnings] Optional check 'copy' (UI text check) has status failed.

=== fixtures/ready-release.json  -> HTTP 200  READY
   [warnings] Optional check 'copy' (UI text check) has status not_run.

=== fixtures/optional-only.json  -> HTTP 200  BLOCKED
   [blockers] No required check exists. A release needs at least one required check to be READY.

=== fixtures/empty-checks.json  -> HTTP 200  BLOCKED
   [blockers] No required check exists. A release needs at least one required check to be READY.

=== fixtures/malformed.json  -> HTTP 200  BLOCKED
   [validationErrors] Invalid JSON: Expecting value (line 1, column 37).

=== fixtures/invalid-required-type.json  -> HTTP 200  BLOCKED
   [validationErrors] checks[0].required must be a JSON boolean, got string.

=== fixtures/invalid-duplicate-ids.json  -> HTTP 200  BLOCKED
   [validationErrors] checks[1].id has a duplicate value 'login'; ids must be unique.

=== fixtures/invalid-optional-check.json  -> HTTP 200  BLOCKED
   [validationErrors] checks[1].status must be one of passed, failed, not_run; got 'skipped'.
```

Every line matches the expectation stated in `docs/DESIGN.md` §7. Note `HTTP 200`
throughout: invalid input is a BLOCKED verdict, never an HTTP error, so the UI has
one response shape to render in all cases.

### Reproducing section B

```bash
uv run uvicorn backend.api.main:app --port 8010 &
python3 - <<'PY'
import json, urllib.request
files = ["sample-release.json", "fixtures/ready-release.json",
         "fixtures/optional-only.json", "fixtures/empty-checks.json",
         "fixtures/malformed.json", "fixtures/invalid-required-type.json",
         "fixtures/invalid-duplicate-ids.json", "fixtures/invalid-optional-check.json"]
for f in files:
    body = json.dumps({"raw": open(f).read()}).encode()
    req = urllib.request.Request("http://127.0.0.1:8010/api/evaluate", body,
                                {"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        d = json.load(r)
    print(f"\n=== {f}  -> HTTP {r.status}  {d['verdict']}")
    for k in ("blockers", "warnings", "validationErrors"):
        for m in d[k]:
            print(f"   [{k}] {m}")
PY
```

## C. Browser checks

Run against the built UI at `http://127.0.0.1:8010/`. Each step was driven in a real
Chrome tab and the resulting DOM was read back; the quoted "actual" values are the
text the page rendered. Method noted per step, because two of them set the textarea
through the React value setter rather than by typing character by character -- the
submit path and the rendering are identical either way.

| # | Step | Expected | Actual |
|---|---|---|---|
| 1 | Paste `sample-release.json`, press **Check release** | red BLOCKED banner; 2 blocking reasons; 1 warning; table of 4 checks; `audit` and `copy` evidence shown as *missing* | confirmed by screenshot: `BLOCKED`, `Blocking reasons (2)` listing `payments` status failed and `audit` missing evidence, `Warnings (1)` listing `copy`, 4-row table, caption reading "Evidence values are supplied reference strings. They are not fetched or verified." |
| 2 | Replace with the all-required-passing report, press again | green READY banner; no blocking reasons; 1 warning | `READY \| blockers:none \| warn: Warnings (1) Optional check 'copy' (UI text check) has status not_run.` |
| 3 | Replace with `{"release": "broken-v1", "checks": [`, press again | BLOCKED with the parse message; **the earlier READY banner gone**; no warnings section; no check table | `{"verdict":"BLOCKED","readyBannerStillPresent":false,"invalid":"Invalid data (1) Invalid JSON: Expecting value (line 1, column 37).","warningsSection":"none","checkTablePresent":false}` |
| 4 | Load a file through the **Load JSON file** input (`invalid-duplicate-ids.json`) | textarea fills from the file; BLOCKED with the duplicate-id message | `{"textareaFilledFromFile":true,"verdict":"BLOCKED","invalid":"checks[1].id has a duplicate value 'login'; ids must be unique."}` |
| 5 | Click the **Supplied sample** button | one click loads and checks; BLOCKED, 2 blockers, 1 warning, 4 table rows, summary line | `{"verdict":"BLOCKED","release":"Release customer-demo-v1","summary":"3 required \u00b7 1 optional \u00b7 2 blocking \u00b7 1 warning","tableRows":4}` |
| 6 | Click **All required passing**, then **Malformed JSON** | green READY replaced by BLOCKED; no stale banner; no table | ready: `{"verdict":"READY","summary":"3 required \u00b7 1 optional \u00b7 0 blocking \u00b7 1 warning"}` then broken: `{"verdict":"BLOCKED","readyStillThere":false,"table":false}` |
| 7 | Click **Invalid optional check** | BLOCKED; the broken check is the optional one; warnings suppressed | `{"verdict":"BLOCKED","invalid":"checks[1].status must be one of passed, failed, not_run; got 'skipped'.","warnings":"none"}` |
| 8 | Press `Cmd`+`Enter` inside the text box | checks without touching the button | verdict rendered: `BLOCKED` |
| 9 | Empty text box | **Check release** is disabled | button `disabled` true, confirmed by screenshot |

Step 3 is the one that matters most: `readyBannerStillPresent: false` is direct
evidence that invalid input does not leave an earlier READY result on screen.

Steps 5 to 8 were driven by clicking the real buttons and reading the DOM back.

Step 4 drove the hidden file input by assigning a `File` through a `DataTransfer`
and dispatching `change`, which runs the real `handleFile` callback. The native
file-picker dialog itself cannot be scripted, so that one dialog interaction is the
only part of the UI not covered here; it is a one-click browser affordance in front
of the handler that was exercised.
