# SONIQ Final Demonstration Guide

## Verified scope

The reproducible demonstration today is **local software-only WAV classification**. A selected existing WAV can pass the backend validator, existing preprocessing, and experimental trained model. The exact result is shown in the backend response. Warning policy stays off because confidence is forced false and no calibrated SPL is supplied. Database history, live ESP32 capture, physical warning output, second-device access, and browser rendering are not verified.

## Start backend with existing local ML packages

In PowerShell, from the repository root:

```powershell
$env:PYTHONPATH = (Resolve-Path 'ml\.venv\Lib\site-packages').Path
$env:NUMBA_DISABLE_JIT = '1'
$env:SONIQ_AUDIO_MODEL_PATH = (Resolve-Path 'ml\artifacts\expanded-local-demo-20261020\experimental_model.joblib').Path
$env:BACKEND_HOST = '127.0.0.1'
$env:BACKEND_PORT = '8000'
& .\.venv\Scripts\python.exe -B -m backend.app
```

Open `http://127.0.0.1:8000/health` to confirm the backend responds. This root venv has no ML dependencies installed; the commands reuse the existing ML site-packages for this process. Do not delete or recreate `ml/.venv`. Numba JIT is disabled only for the current process to work around the blocked compiled extension without weakening Windows security. PostgreSQL remains degraded/unavailable in this environment.

## Submit one existing WAV

In another PowerShell terminal at the repository root:

```powershell
$wav = (Resolve-Path 'ml\data\expanded_local_demo_20261020\audio\recordings\01_StudentConversation.wav').Path
Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8000/api/v1/classify' -Method Post -ContentType 'audio/wav' -InFile $wav
```

Verified result for this file: HTTP 200, `Student Conversation`, model probability `0.9401317274506633` (`calibrated=false`), inference status `not_evaluated`, warning status `not_performed`. Do not describe this as accuracy or ground truth. The manifest says all 12 examples were fitted and evaluation is null.

## Static dashboard

In another terminal:

```powershell
& .\.venv\Scripts\python.exe -m http.server 8001 --bind 127.0.0.1 --directory dashboard
```

Open `http://127.0.0.1:8001/`. The dashboard uses loopback CORS and has actual Node-tested health, event, and WAV classification adapters. Browser rendering could not be verified in this session because installed Chrome/Edge headless processes failed before rendering. Event history is unavailable until the existing PostgreSQL database is configured. Stop both servers with `Ctrl+C` in their terminals.

## Private LAN check

For a controlled same-subnet setup, set `BACKEND_HOST=0.0.0.0`, keep the backend port private, and use `ipconfig` to find the active adapter's IPv4. This PC's checked Ethernet address was `[PRIVATE_LAN_IPV4]`; it may change. On this host, backend health succeeded through both loopback and that address at temporary port `18132`. A second-device connection was **NOT TESTED**. The API has no authentication. Do not configure router port forwarding or expose it publicly. If a firewall exception is required, restrict inbound TCP to the Private profile and LocalSubnet after admin/policy review; this run did not change firewall settings.

## USB receiver (future hardware gate)

The software receiver and parser are in `tools/soniq_serial_audio_companion.py`; protocol layout is documented in `docs/USB_SERIAL_AUDIO_PROTOCOL.md`. Parser-only tests need no hardware. Actual CLI use is blocked until the firmware deliberately emits SQAU/1 and a real board/COM port, microphone conversion, memory, and baud rate pass bench checks. Optional pyserial is declared in `tools/requirements-serial.txt` but not installed. The `--submit-event` option is explicitly opt-in and constructs a fail-closed event (`confident=false`, unknown sensor, null SPL); use it only after the existing PostgreSQL target/schema is verified.

## Do not present as demonstrated

- No ESP32 microphone capture or serial transfer was tested.
- No calibrated dB SPL value exists; RMS remains raw/un-calibrated.
- The experimental model has no valid independent evaluation metrics.
- No event was inserted, retrieved, or persisted.
- No browser-rendered page, second-device LAN connection, or physical warning output was verified.
