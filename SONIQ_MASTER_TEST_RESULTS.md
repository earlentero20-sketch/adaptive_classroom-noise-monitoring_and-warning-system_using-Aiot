# SONIQ Master Test Results

**Date:** 2026-11-09 (Asia/Manila)  
Statuses use the requested vocabulary: PASS, FAIL, BLOCKED, NOT TESTED, PARTIALLY COMPLETE.

## Test matrix

| Check | Status | Result/evidence |
|---|---|---|
| Root Python interpreter | PASS | `.\.venv\Scripts\python.exe --version` returned Python 3.13.17. |
| Legacy ML virtualenv | BLOCKED | `ml\.venv` points to a missing Python executable under another Windows profile. It was not recreated. |
| Backend imports | PASS | `.\.venv\Scripts\python.exe -B -c "import backend.app"` exited successfully. |
| Backend test suite | PASS | `python -B -m unittest discover -s backend/tests`: 67 tests, 1 skipped. The test-only StubServer assertion correction is described in the Step 10 report. |
| ML test suite | PASS | With existing ML site-packages on process-only `PYTHONPATH` and `NUMBA_DISABLE_JIT=1`: 67 tests, 1 skipped. No Windows security policy was bypassed. |
| Dashboard test suite | PASS | Existing Node test command: 25 passed, 0 failed. Node 24.20.0 was invoked by its explicit installation path because shell PATH was stale. |
| Backend default health | PASS | Live `/health` on loopback returned `status=online`; warning setup correctly reported not ready. |
| Backend wide bind and localhost | PASS | `BACKEND_HOST=0.0.0.0`, `BACKEND_PORT=18128`; `/health` via `127.0.0.1` returned online. Temporary server was stopped. |
| Backend access from another LAN device | NOT TESTED | No second device was available. This session could not enumerate a host interface IPv4 due Windows access denial. |
| Real WAV classification | PASS | `01_StudentConversation.wav` POSTed to `/api/v1/classify`; HTTP 200; label `Student Conversation`; experimental, not evaluated; confidence is not calibrated. No event was persisted. |
| Model accuracy/ground truth | NOT TESTED | The selected artifact is marked `experimental_full_fit_no_held_out_evaluation`; dataset manifest is unreviewed and no validated label assessment was performed. |
| Warning on classifier endpoint | PASS | Actual response explicitly reported `warning_evaluation.status=not_performed`; no warning was fabricated. |
| Warning policy with real verified event inputs | BLOCKED | No verified classifier-confidence mapping and no calibrated SPL sample are available. Existing policy remains fail-closed. |
| PostgreSQL connection | BLOCKED | No `SONIQ_DATABASE_URL`, `.env`, local PostgreSQL service, listener on 5432, `psql`, or psycopg driver was available in the new venv. Remote DB status is unknown. |
| Event persistence/retrieval | BLOCKED | No actual DB insertion or retrieval was possible. Prior smoke returned expected HTTP 503 for event history in degraded mode. No fake event used. |
| Dashboard JavaScript/browser-independent checks | PASS | 25 Node tests passed. Static dashboard and adapters are present. |
| Dashboard live health/CORS | PASS | Earlier Step 10 smoke served the static page and received backend health HTTP 200 with expected loopback CORS. Temporary servers stopped. |
| Dashboard browser event/classification display | NOT TESTED | No browser session, persisted events, or live DB data. |
| Windows serial device detection | BLOCKED | `Get-PnpDevice -PresentOnly`, `Get-CimInstance Win32_SerialPort`, and filtered `Win32_PnPEntity` found no matching ESP32/USB-serial device or COM port. |
| Real ESP32 audio transfer and hardware warning | NOT TESTED | No board/COM port was detected. Firmware sends events rather than classifier-compatible audio. |
| Invalid input handling | PASS | Existing backend/ML suites pass their validation tests; no live malformed-audio request was sent in this final run. |
| Public-internet exposure | NOT TESTED | No external exposure test was performed. LAN bind is for a trusted private network only; no router forwarding is documented or authorized. |

## Exact commands

Backend unit tests:

```powershell
& .\.venv\Scripts\python.exe -B -m unittest discover -s backend/tests
```

ML suite and inference environment (uses existing installed ML files, without installing them):

```powershell
$env:PYTHONPATH = (Resolve-Path 'ml\.venv\Lib\site-packages').Path
$env:NUMBA_DISABLE_JIT = '1'
& .\.venv\Scripts\python.exe -B -m unittest discover -s ml/tests
```

Dashboard tests (use the explicit Node path if `node` is not on PATH):

```powershell
& '[LOCAL_PATH]' --test dashboard/backend-adapter.test.mjs dashboard/dashboard.test.mjs
```

Classifier request used the existing WAV and local experimental artifact; service was stopped after the request:

```powershell
$env:PYTHONPATH = (Resolve-Path 'ml\.venv\Lib\site-packages').Path
$env:NUMBA_DISABLE_JIT = '1'
$env:SONIQ_AUDIO_MODEL_PATH = (Resolve-Path 'ml\artifacts\expanded-local-demo-20261020\experimental_model.joblib').Path
& .\.venv\Scripts\python.exe -B -m backend.app
```

In a second terminal, POST the WAV to `http://127.0.0.1:8000/api/v1/classify` as `audio/wav`. The actual response is recorded in `SONIQ_FINAL_DEMO_GUIDE.md`; this is software inference only, not ESP32 input.

## Limitations on results

PASS refers only to the executed software checks above. It does not mean the classifier is validated, the warning chain is complete, PostgreSQL persistence works, or the hardware-to-dashboard workflow has passed. No sensor reading, audio, classification, or event was synthesized for testing.
