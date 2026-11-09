# SONIQ Today — Demonstration Guide

**Current-session status:** A full live ESP32 → ML → PostgreSQL → dashboard → warning demonstration is **NOT READY**. No ESP32/serial device, usable Python runtime, Node runtime, backend process, or PostgreSQL listener was available in this session. No audio bridge exists, and Step 8 approval remains outstanding. This guide gives the exact existing local startup path and states what it can and cannot demonstrate; it does not claim that startup succeeded here.

## 1. Before starting: supply existing dependencies

Use the existing Python project environment if repaired. Current observations: root `.venv` is absent; `ml/.venv` points to a missing Python 3.13 install; the Windows Store `python` alias fails. Install a supported Python distribution if needed, then from the repository root run:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r ml\requirements.txt -r backend\requirements.txt
```

These are setup instructions, not commands verified in this session. Node.js is needed to run dashboard tests, but not to serve the static dashboard. Do not install `pyserial` yet: no receiver is implemented or approved.

## 2. Configure the existing database and model privately

Use the already approved PostgreSQL server/database and role. Do not create a replacement database or reset data. The database owner must first verify the target `soniq_db` (or the approved existing DB), `events` table, and `schema_migrations` ledger. Do not run migration 001 blindly; it creates `events` without `IF NOT EXISTS`.

Create a root `.env` using privately supplied actual values; do not paste credentials into chat or reports. Example keys only:

```dotenv
SONIQ_DATABASE_URL=postgresql://<approved-role>:<url-encoded-password>@<approved-host>:5432/soniq_db
SONIQ_AUDIO_MODEL_PATH=<absolute-path-to-approved-existing-model-artifact>
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
WARNING_THRESHOLD_DB_SPL=75
MAX_INPUT_AGE_SECONDS=30
```

Replace placeholders locally. The values must refer to the existing approved server, role, and model artifact; no credentials or model selection are supplied here. `backend/start_backend.py`, called by the launcher, reads root `.env` as UTF-8 for its allowlisted keys and does not print values. Directly running `backend.app` will not load `.env` itself. If database settings are absent, health can still be available in degraded mode while event endpoints return `storage_unavailable`.

## 3. Start the existing backend and dashboard

From the repository root, use the existing launcher:

```powershell
.\start_soniq.bat
```

It starts the static dashboard at `http://127.0.0.1:8001/` and the backend on the configured host/port (default `127.0.0.1:8000`). It uses the root `.venv` if usable, then `ml/.venv`; currently neither is usable in this environment. If the dashboard server starts, open `http://127.0.0.1:8001/`. Check backend process health at:

```text
http://127.0.0.1:8000/health
```

Health confirms the HTTP process and warning configuration only; it does not prove PostgreSQL is ready. Check actual stored history in the dashboard or at `http://127.0.0.1:8000/api/v1/events?limit=10&offset=0`. Database failure must remain visibly an API error, not an empty/synthetic history.

The dashboard API base defaults to `http://127.0.0.1:8000`. For a local static page, it also supports an explicit URL query override, for example `http://127.0.0.1:8001/?api=http://127.0.0.1:8000`. No LAN/firewall exposure is needed for this local USB-serial design. Keep classifier loopback-only.

## 4. COM port and audio transfer status

**There is no current receiver command or supported COM configuration.** No `tools/soniq_serial_audio_companion.py`, framing implementation, or optional serial requirements file exists. This session detected no serial port; do not guess `COM3` or another port. Firmware still emits text at 115,200 baud and sends event JSON over Wi-Fi; it does not send PCM audio.

After hardware is physically connected and implementation is approved, Windows port discovery can use:

```powershell
Get-CimInstance Win32_SerialPort | Select-Object DeviceID,Name
```

or, after an approved `pyserial` install:

```powershell
.\.venv\Scripts\python.exe -m serial.tools.list_ports
```

At that future point, the receiver must be given the observed port explicitly (`COMx`) and a bench-verified baud. Close Arduino Serial Monitor before the receiver opens the port. Those commands only list ports; they cannot receive audio or call the classifier today. Existing 115,200 baud is too slow for real-time PCM16 (minimum estimate 2.78 seconds for a one-second, 32,000-byte buffered transfer, before framing overhead). Board/RAM/baud suitability is unknown.

## 5. Actual demo sequence and truthful scope

### Sequence verified in this session

**None of the live workflow was verified.** This session verified only repository/source state and attempted the existing test commands; Python and Node test runs were blocked, and no live services or hardware were reachable. Do not demonstrate or describe an actual ESP32 capture, model prediction, saved event, dashboard event update, or positive warning as having occurred.

### Sequence to execute only after prerequisites are restored

1. Start the real PostgreSQL service and confirm the approved existing database, schema, and migration ledger. Do not migrate without owner review.
2. Configure the private `.env` values above, prepare a usable Python environment, and run `start_soniq.bat`.
3. Confirm `/health`, then verify the actual event-history response/database readiness. Do not infer DB readiness from health.
4. An existing manual WAV upload in the static dashboard can exercise `/api/v1/classify` when the model path is approved and a real approved PCM WAV is supplied. Label the current artifact experimental if its metadata says full-fit/no-held-out-evaluation. This does not demonstrate ESP32 audio or persistence.
5. To complete ESP32-to-model-to-event, first obtain approval for the Step 8 serial protocol and implement/bench-test the firmware and separate host receiver. Then capture from the actual microphone, verify packet CRC/frame count, assemble WAV, confirm classifier response, submit a real event, read it back from PostgreSQL, and observe it in dashboard history. This complete sequence has **not** been implemented or tested.
6. Keep event `confident=false` and sound level null/uncalibrated until approved confidence semantics and reference-meter SPL calibration are available. Verify warning remains off. Keep physical buzzer disabled absent separate safety approval and hardware tests.

## 6. Existing test commands

Run these after installing/repairing the tools:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s backend\tests -v
.\.venv\Scripts\python.exe -B -m unittest discover -s ml\tests -v
node --test dashboard/backend-adapter.test.mjs dashboard/dashboard.test.mjs
```

This session attempted the equivalent commands with `python` and `node`: both Python suites failed before test collection because the Windows alias could not launch; Node was not found. See `SONIQ_STEP9_TEST_RESULTS.md` for all status details.

## 7. Current demonstrated capabilities and limitations

- Source has a static dashboard, HTTP health/events/classification interfaces, a PostgreSQL repository, and I2S RMS/LED firmware.
- Runtime startup, database persistence, model inference, dashboard rendering, USB serial, physical audio, SPL, and hardware warning output were **not tested** here.
- Firmware does not currently transmit audio. No serial port was found in this session.
- Classifier inference does not itself store events or evaluate warning policy. Event persistence requires a working existing PostgreSQL connection.
- Model confidence is not calibrated; RMS is not dB SPL. No real classification can authorize a warning on its own.

Do not call today’s full end-to-end demonstration ready unless the actual setup passes each hardware, inference, persistence, dashboard, and safety gate above.
