# SONIQ Step 7 — Test Results

**Date:** 2026-11-09 (Asia/Manila)  
**Summary:** No database, backend, model, audio, browser, or hardware integration test could be completed in the current environment. The supplied prompt reports prior passing suites and WAV inference; those results are recorded as user-reported, not independently reproduced here.

## User-reported prior results

The Step 7 prompt states:

- Backend tests: 72 passed, 1 skipped.
- ML tests: 66 passed, 1 skipped.
- Dashboard tests: 25 passed.
- Backend health: passed.
- Actual WAV classification through a running backend: passed.
- Event history: HTTP 503 `storage_unavailable`.

No test logs, environment details, or execution output accompanied those claims. Current local attempts below could not reproduce them; they may refer to a different machine/session.

## Tests attempted in this environment

| Test/check | Status | Actual result |
|---|---|---|
| `python -B -m unittest discover -s backend/tests -v` | **BLOCKED** | Windows Store `python.exe` alias failed to launch (`file cannot be accessed by the system`). |
| `python -B -m unittest discover -s ml/tests -v` | **BLOCKED** | Same Python launch failure. |
| `node --test dashboard/backend-adapter.test.mjs dashboard/dashboard.test.mjs` | **BLOCKED** | `node` command is not available. |
| `.\ml\.venv\Scripts\python.exe` | **BLOCKED** | Virtualenv points to missing base interpreter `[LOCAL_PATH]`. |
| PostgreSQL service query (`Get-Service -Name '*postgres*'`) | **BLOCKED / NO SERVICE FOUND** | No matching Windows service was returned. This does not rule out a nonstandard/remote installation. |
| PostgreSQL default install root | **NO INSTALL FOUND THERE** | `C:\Program Files\PostgreSQL` does not exist; other install locations were not exhaustively searched. |
| PostgreSQL TCP connect `127.0.0.1:5432` | **FAILED / UNAVAILABLE** | TCP connect did not complete; no local listener accepted it. |
| `SONIQ_DATABASE_URL` / `.env` | **BLOCKED** | Environment variable absent and `.env` absent. No credentials were printed or supplied. |
| `psql` / `pg_isready` | **BLOCKED** | Commands unavailable. |
| `GET http://127.0.0.1:8000/health` | **FAILED / NOT RUN** | Request raised `WebException`; no backend process was listening. |
| Database connection to `soniq_db` | **BLOCKED** | No URL/service/client; authentication and database existence were not tested. |
| Event insertion/retrieval/history API/dashboard | **NOT TESTED** | No DB or live backend; no records were generated. User reports a prior 503, not independently reproduced. |
| Model deserialization and actual WAV classification | **BLOCKED** | Python unavailable. Three experimental artifacts and WAV files are present, but no prediction was made here. |
| Warning policy runtime/integration | **NOT TESTED** | No actual classifier output plus calibrated SPL reached the event API. |
| ESP32 audio transmission / LAN test | **FAILED by implementation inspection** | Current source sends event JSON only; no audio payload path exists. No physical board test. |
| Serial/board availability | **NOT TESTED** | Only COM1 was enumerated; board model/connection was not confirmed. |
| Firmware compilation | **BLOCKED** | Arduino CLI/PlatformIO unavailable. |

## Code/interface findings (not test passes)

- Current firmware reads 16 kHz I2S as 32-bit left-channel words in 512-sample blocks, computes local normalized RMS, and posts null classification/SPL fields.
- Classifier requires a complete PCM WAV and remains loopback-only. Existing artifact metadata targets 16 kHz mono and 1-second windows; the model is experimental/no-held-out-evaluation.
- Event API applies warning policy and persists via PostgreSQL. Missing repository returns `storage_unavailable`; health only reports process/configuration and is not proof of DB readiness.
- Current firmware sets `ENABLE_PHYSICAL_BUZZER=false`; no live warning/output verification occurred.

## Reproduction requirements

1. Install/use a working Python environment and declared requirements; rerun backend and ML suites.
2. Start/provision PostgreSQL and privately set `SONIQ_DATABASE_URL`; inspect the target schema/ledger before any migration. Use a dedicated test DB for destructive-test-schema routines.
3. Start backend and verify health, event list, a genuine event insert/retrieval, then dashboard display.
4. Use approved WAV/model artifacts for actual inference; preserve the no-accuracy-claim status of the experimental artifacts.
5. Obtain approval and hardware identification before implementing the documented serial audio path; then test real audio, throughput, backend inference, event persistence, warning inputs, and physical output separately.
