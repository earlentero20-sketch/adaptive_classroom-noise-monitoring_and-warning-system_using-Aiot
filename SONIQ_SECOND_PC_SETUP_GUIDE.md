# SONIQ Setup Guide for a Second Windows PC

This handoff is a source snapshot on branch `handoff/soniq-complete-project-2026-11-09`, based on `7b3e66db39b2d74667da4fcea2f07eeab112731b`. It does not include the original computer's virtual environments, local database, recordings, or credentials.

## Prerequisites

- Windows 10/11, Git, Python 3.13.x, and (for dashboard automated tests) Node.js 24.x.
- PostgreSQL installed or a reachable PostgreSQL server, with an existing `soniq_db` database and schema provisioned separately. Do not reset or recreate an existing database.
- The trained model artifact(s) are included under `ml/artifacts/`; the manifest records their checksums.

## Python environment and configuration

From the repository root in PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe -m pip install -r ml\requirements.txt
Copy-Item .env.example .env
notepad .env
```

Fill `.env` locally with settings appropriate to this PC. Set `SONIQ_DATABASE_URL` only if PostgreSQL is configured, using the existing database name and a locally managed password; never commit `.env`. Set model path using the existing configuration documented in `.env.example` and backend documentation. Do not change database schema as part of setup.

## Start backend and dashboard

```powershell
.\start_soniq.bat
```

The launcher starts the backend. Open `dashboard\index.html` in a browser. If browser CORS or file-origin rules prevent requests, serve the static dashboard from the repository root with Python in a separate terminal:

```powershell
.\.venv\Scripts\python.exe -m http.server 8080 --directory dashboard
```

Then open `http://127.0.0.1:8080`. Backend startup and test commands are documented in `README.md`, `backend/README.md` if present, and `SONIQ_STEP10_TEST_RESULTS.md`.

## Run checks

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests ml\tests
node --test dashboard\tests\*.test.js
```

Install Node only if you intend to run dashboard tests; the static dashboard itself has no build step. The handoff manifest and test report record what was verified on the original PC. Passing local tests does not establish hardware or database availability on this PC.

## ESP32 and serial bridge

Review `docs/USB_SERIAL_AUDIO_PROTOCOL.md`, `SONIQ_STEP8_COMPATIBILITY_REPORT.md`, and `SONIQ_STEP10_REMAINING_BLOCKERS.md` before connecting hardware. Board identity, microphone pins, sample format, and COM port must be confirmed on this PC. The current firmware endpoint may contain a LAN address from the original setup; replace it with this PC's reachable LAN IPv4 address and the documented backend port only after confirming the API endpoint and firmware protocol compatibility. Do not assume the serial companion is compatible with firmware without matching protocol evidence. Raw microphone values are not calibrated dB SPL unless separately calibrated.

## PostgreSQL

Use only the intended existing PostgreSQL server/database. Confirm host, port, database, and username locally; supply credentials through an untracked `.env`. The snapshot does not carry database data or credentials. PostgreSQL was unavailable during the recorded verification, so persistence must be retested against the configured server.
