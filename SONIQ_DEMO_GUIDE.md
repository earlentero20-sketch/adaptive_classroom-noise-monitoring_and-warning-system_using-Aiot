# SONIQ Demonstration Guide

**Current capability:** The repository contains a static dashboard, a backend, a PostgreSQL adapter, an experimental WAV classifier, and ESP32 event-posting firmware. The complete live microphone → classification → warning → database → dashboard demonstration is **not ready**: the firmware sends no audio or calibrated SPL, and this environment cannot start the project runtime. Use the sections below to demonstrate only the features that are actually available, and label each limitation clearly.

## 1. Prepare the Windows computer

Install a supported Python version, then run from the repository root:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r ml\requirements.txt -r backend\requirements.txt
```

No dashboard build or frontend package install is needed. Node.js is needed only to run the existing JavaScript test suite.

## 2. Start PostgreSQL and prepare its existing schema

Start the installed PostgreSQL service from Windows Services (`services.msc`). Confirm the database owner has identified the correct database and role before proceeding. Project history used `soniq_db`, but the backend uses whichever database is specified in `SONIQ_DATABASE_URL`.

Create a private `.env` in the repository root with the approved values. Do not paste or print the database password. Use `SONIQ_DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DATABASE`; URL-encode reserved credential characters. Set `BACKEND_HOST=0.0.0.0` only for the trusted private-LAN ESP32 demonstration; use `127.0.0.1` for a software-only demo. Choose `BACKEND_PORT=8000`. Set warning settings only as approved. `start_soniq.bat` loads these variables into the backend child process without displaying them.

For a first install only, load `.env` into a PowerShell process without echoing values and run the existing migration against the verified target:

```powershell
Get-Content .env | ForEach-Object {
    $line = $_.Trim()
    if ($line -match '^([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
        [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2], 'Process')
    }
}
.\.venv\Scripts\python.exe -m backend.migrate
```

The migration runner is checksum-tracked and does not drop data, but migration `001_create_events.sql` uses `CREATE TABLE events` without `IF NOT EXISTS`. Before applying it, confirm that `schema_migrations` records this migration or that the target has no existing `events` table. If an events table already exists without a matching migration record, stop and ask the database owner to inspect/plan a compatible migration; do not run it blindly. Never drop, reset, or recreate the database. Do not use a production database as the PostgreSQL test database.

## 3. Start and check the backend

Run:

```powershell
.\start_soniq.bat
```

The batch file opens the dashboard server in a separate window and keeps the backend in the current window. Open `http://127.0.0.1:8001/`. Verify backend process health at `http://127.0.0.1:8000/health`. Health reports process/warning-configuration status, not database readiness. Confirm event history separately in the dashboard or at `http://127.0.0.1:8000/api/v1/events`.

If PostgreSQL configuration or connection is unavailable, the backend may still answer health in degraded mode; event requests return `503 storage_unavailable`. An empty event list means the backend returned no stored events; it must not be filled with fabricated examples.

## 4. Optional LAN and ESP32 event-posting check

On the Windows host, run `ipconfig` and identify the active Wi-Fi/Ethernet private IPv4 address. If needed, use the scoped Private-profile firewall command in [`docs/LAN_CONNECTIVITY.md`](docs/LAN_CONNECTIVITY.md); do not enable a Public-profile rule or router port forwarding.

In `firmware/ESP32_SONIQ_Integrated_V2/ESP32_SONIQ_Integrated_V2.ino`, set `SERVER_URL` to `http://<Windows-private-IPv4>:8000/api/v1/events` and configure the same trusted Wi-Fi on the device. Compile/upload with the matching ESP32 toolchain and inspect its Serial Monitor for HTTP status. Keep credentials private.

**Limit:** The current sketch posts events with null classification and null sound level. It does not upload the sampled audio. An event received from this firmware can verify only event transport/storage and reported device status; it cannot demonstrate ML classification or a sound-level warning. This guide does not claim that a physical board is available or verified.

## 5. Optional manual WAV classification

Only after model/data-owner approval, set `SONIQ_AUDIO_MODEL_PATH` to an existing trusted artifact in `.env`, then restart the backend. The repository artifacts are experimental full-fit models with no held-out evaluation and incomplete formal dataset readiness; do not present their results as validated accuracy. No artifact is selected automatically.

Choose an approved, complete PCM WAV and submit it through the dashboard’s WAV control, or from the same Windows computer run:

```powershell
Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/v1/classify' `
    -Method Post -ContentType 'audio/wav' -InFile '<approved-local-wav-path>'
```

The route accepts one complete PCM WAV from a loopback client. It returns classification only. It does not persist an event, evaluate the warning policy, or prove ESP32 audio transport.

## 6. Warning and event-history demonstration status

The existing warning decision is made only by the backend event route. It requires a fresh allowed class marked confident, a fresh calibrated `dB_SPL` value, approved threshold/freshness configuration, and sound strictly above threshold. Current firmware supplies none of the classification/SPL fields; the model probability is explicitly uncalibrated and is not an approved `confident=true` value. No calibration source or confidence rule is currently integrated.

Therefore **do not attempt to trigger a warning by inventing an event, SPL value, or classification**. A permissible current demonstration can show backend warning readiness, an actual non-triggered firmware event if a real board/database are available, and the dashboard’s real history/error state. It cannot claim a positive warning or buzzer demonstration. Keep the physical buzzer disabled.

## 7. What to report during the presentation

- **Can be shown after setup:** backend health; actual PostgreSQL history if genuine events exist; dashboard empty/error/loading states; optionally a manually uploaded WAV classification after artifact approval, clearly labeled experimental.
- **Not currently demonstrable:** ESP32 audio reaching the classifier; calibrated SPL; a valid model-confidence gate; a warning generated from live audio; complete event persistence from a classified sensor window; physical buzzer activation.
- **Do not claim:** evaluated model accuracy, calibrated dB SPL, verified hardware health, end-to-end live classification, or successful persistence unless each is actually tested on the demonstration setup.

For LAN setup, database setup, and dashboard details, see [`docs/LAN_CONNECTIVITY.md`](docs/LAN_CONNECTIVITY.md), [`docs/POSTGRES_LOCAL.md`](docs/POSTGRES_LOCAL.md), and [`dashboard/README.md`](dashboard/README.md).
