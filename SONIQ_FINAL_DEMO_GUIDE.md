# SONIQ Final Demo Guide

## Demonstration scope

The currently supportable demonstration is a **local software demonstration**: start the backend, check health, submit one existing project WAV to the existing classifier API, and view the static dashboard shell/health status. It does not demonstrate live ESP32 audio, warning actuation, database persistence, or a real event history. The WAV and model are experimental/unreviewed; disclose that before presenting the prediction.

## Start the backend

From the repository root, open PowerShell. The approved root Python environment works, but it does not contain ML dependencies. Reuse the existing ML environment’s installed packages for this process and disable Numba JIT (this is a runtime setting, not a security-policy change):

```powershell
$env:PYTHONPATH = (Resolve-Path 'ml\.venv\Lib\site-packages').Path
$env:NUMBA_DISABLE_JIT = '1'
$env:SONIQ_AUDIO_MODEL_PATH = (Resolve-Path 'ml\artifacts\expanded-local-demo-20261020\experimental_model.joblib').Path
$env:BACKEND_HOST = '127.0.0.1'
$env:BACKEND_PORT = '8000'
& .\.venv\Scripts\python.exe -B -m backend.app
```

The existing Python packages are reused without copying or installing them. If import/model loading fails on another machine, stop and provision the declared requirements through the project's approved environment process; do not assume the current `.venv` has them. Without a PostgreSQL URL/driver, backend startup is degraded and event endpoints report storage unavailable. Health is expected at `http://127.0.0.1:8000/health`.

The batch launcher may be used for normal startup when its configured environment is prepared: `start_soniq.bat` (run as `.\start_soniq.bat` from PowerShell). For the verified experimental classifier run above, launch with the explicit environment shown here so the correct artifact and inference dependencies are selected.

## Run the existing WAV classifier

In a second PowerShell terminal at the repo root:

```powershell
$wav = (Resolve-Path 'ml\data\expanded_local_demo_20261020\audio\recordings\01_StudentConversation.wav').Path
Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8000/api/v1/classify' -Method Post -ContentType 'audio/wav' -InFile $wav
```

Observed response: HTTP 200; label `Student Conversation`; `model_confidence.value=0.9401317274506633`, `calibrated=false`; inference marked `experimental_model` and `not_evaluated`; warning status `not_performed`; hardware `not_tested`. The sample is a local, unreviewed demo audio asset and likely part of model fitting; the output must not be described as validated accuracy or ground truth. This route does not insert an event.

## Open the static dashboard

Serve the static dashboard from a second PowerShell terminal at the repository root:

```powershell
& .\.venv\Scripts\python.exe -m http.server 8001 --bind 127.0.0.1 --directory dashboard
```

Then open `http://127.0.0.1:8001/` in the browser. Serving it over loopback HTTP is required for the dashboard's loopback-only CORS policy; opening the HTML as a `file:` URL is unsupported. The dashboard is static HTML/CSS/JavaScript and has no frontend build step. Its default backend address is loopback. The browser health view can report the backend, but event history will be unavailable while PostgreSQL is not configured. Browser rendering was not tested in this environment; do not present it as tested. Stop the static server with `Ctrl+C` in its terminal.

## LAN and ESP32 status

The backend was verified listening on `0.0.0.0:18128` and reachable through localhost. Access from a second LAN device was **NOT TESTED**. To try a controlled private-LAN session, set `BACKEND_HOST=0.0.0.0`, keep the configured port, determine the active adapter IPv4 with `ipconfig`, and use `http://<that-private-IPv4>:8000` from a device on the same trusted network. Do not configure router port forwarding or expose this unauthenticated service to the internet. Windows Firewall may require an inbound TCP rule for the selected port restricted to the Private profile and LocalSubnet; confirm local policy/admin requirements before adding one.

The firmware currently sends event JSON, not audio accepted by `/api/v1/classify`. No ESP32/COM port was detected. Therefore an ESP32 cannot be assumed to generate the result shown above. Verify board identity, microphone wiring/sample alignment, format, transport, and a compatible firmware protocol before making changes or claiming a live demonstration.

## Stop

Press `Ctrl+C` in the backend terminal. Do not create an event merely to populate the dashboard. For repeatable tests, use the existing unit suites with the exact commands in `SONIQ_MASTER_TEST_RESULTS.md`.
