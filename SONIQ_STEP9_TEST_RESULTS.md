# SONIQ Step 9 — Test Results

**Date:** 2026-11-09 (Asia/Manila)  
**Overall:** No full integration test passed in this session. Results below distinguish source review from executable tests. No fake records or test audio were generated.

## Test matrix

| Check | Result | Evidence / limitation |
|---|---|---|
| Review all three Step 8 reports | **PASS (documentation review)** | Read `SONIQ_STEP8_USB_SERIAL_IMPLEMENTATION_PLAN.md`, `SONIQ_STEP8_COMPATIBILITY_REPORT.md`, and `SONIQ_STEP8_BLOCKER_REPORT.md`; serial work is design-only and requires approval. This is not a hardware test. |
| Backend unit tests: `python -B -m unittest discover -s backend/tests -v` | **BLOCKED** | Windows `python.exe` alias failed with “The file cannot be accessed by the system.” No tests executed. |
| ML unit tests: `python -B -m unittest discover -s ml/tests -v` | **BLOCKED** | Same Windows Python alias launch failure. No tests executed. |
| Dashboard tests: `node --test dashboard/backend-adapter.test.mjs dashboard/dashboard.test.mjs` | **BLOCKED** | `node` command is unavailable. No tests executed. |
| Root Python environment | **BLOCKED** | `.venv/Scripts/python.exe` absent. |
| Existing `ml/.venv` | **BLOCKED** | Launcher reports its base interpreter path `[LOCAL_PATH]` does not exist. |
| PostgreSQL process environment | **BLOCKED** | `SONIQ_DATABASE_URL` and `SONIQ_TEST_DATABASE_URL` unset; root `.env` absent. No credential was printed or requested. |
| PostgreSQL local service/listener | **BLOCKED** | No matching PostgreSQL Windows service found; TCP `127.0.0.1:5432` did not connect. This does not establish that no remote/nonstandard DB exists. |
| Backend startup / `/health` | **BLOCKED** | `http://127.0.0.1:8000/health` unreachable; no process answered. |
| Model load and actual audio inference | **NOT TESTED / BLOCKED** | No runnable Python environment, model path, or actual ESP32 capture. No label was generated. |
| Firmware compile and serial protocol | **BLOCKED** | No Arduino CLI/PlatformIO reported by Step 8; no approved protocol implementation. |
| Serial port/device detection | **BLOCKED** | This Step 9 session enumerated no `Win32_SerialPort` devices. No actual ESP32/COM connection verified. |
| Audio capture/transfer/WAV validation | **NOT TESTED** | Current firmware transmits event JSON only and discards I2S samples after RMS. No real audio captured or fabricated. |
| Event insertion/retrieval/PostgreSQL persistence | **BLOCKED** | No DB connection or backend. No event generated. Existing schema and data untouched. |
| Dashboard health/history/classification display | **NOT TESTED / BLOCKED** | Static source remains present; Node/browser/live backend unavailable. No dashboard runtime response observed. |
| Warning policy runtime | **NOT TESTED** | No actual model output plus fresh confident classification and calibrated SPL available. Existing source requires those inputs and fails closed. |
| Physical warning output | **NOT TESTED** | Firmware sets buzzer enable false; no board or safety verification. |
| Git preservation | **PASS** | Final status retained 9,416 staged deletions, has 29 untracked paths including these reports, and zero other status entries. No Git index operation was run. |

## Source facts (not runtime passes)

- Existing firmware uses I2S at 16 kHz, one left channel, 32-bit words, and 512-word RMS blocks; it does not transmit PCM audio.
- Existing `/api/v1/classify` requires one complete PCM WAV request from a loopback client, returns inference metadata, and does not save an event or evaluate warning policy.
- Existing `/api/v1/events` is the event persistence/warning boundary. Database-unavailable behavior is degraded startup and `storage_unavailable` event operations, according to source; no live response was observed here.
- Dashboard calls backend health and event/classification paths; source has unavailable/error states. No live browser check was performed.
- Warning policy cannot safely trigger from classifier probability alone: probability is uncalibrated, confidence approval is absent, and calibrated dB SPL is unavailable. No warning was requested or produced.

## Reproduction when blockers are cleared

1. Configure a working Python virtualenv from the project requirements; configure Node.js for dashboard tests.
2. Privately configure `SONIQ_DATABASE_URL`, verify the existing database and schema/ledger, then start the backend. Do not run migrations until the live schema owner approves.
3. Verify `/health`, event history, and a genuine API event from an actual source; confirm PostgreSQL retrieval and dashboard rendering.
4. Approve the serial protocol and identify board/microphone/COM hardware. Compile firmware and measure real capture conversion, packet integrity, throughput, memory, and reconnection behavior.
5. Use one actual microphone capture through the existing model, check classifier response, persist one actual event, and verify dashboard history.
6. Keep event confidence false and SPL null until approved confidence semantics and reference-meter calibration exist; assert the warning stays off. Physical buzzer remains disabled until separately safety-tested.
