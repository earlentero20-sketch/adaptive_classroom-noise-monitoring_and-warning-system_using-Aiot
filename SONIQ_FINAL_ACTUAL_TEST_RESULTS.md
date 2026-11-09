# SONIQ Final Actual Test Results

**Date:** 2026-11-09 (Asia/Manila)  
Status terms: PASS, FAIL, BLOCKED, NOT TESTED, PARTIALLY COMPLETE.

## Executed tests

| Test | Status | Actual procedure/result |
|---|---|---|
| Python runtime | PASS | `& .\.venv\Scripts\python.exe --version` → Python 3.13.17. |
| Backend suite | PASS | With existing ML `site-packages` on process-only `PYTHONPATH` and `NUMBA_DISABLE_JIT=1`, `& .\.venv\Scripts\python.exe -B -m unittest discover -s backend/tests` → 69 run, 1 skipped, all others passed. Includes 180-second boundary acceptance and 181-second WAV rejection. |
| ML suite | PASS | Same process-only package path/JIT setting, `& .\.venv\Scripts\python.exe -B -m unittest discover -s ml/tests` → 67 run, 1 skipped, all others passed. Numba's compiled JIT extension was not loaded. |
| SQAU parser suite | PASS | `& .\.venv\Scripts\python.exe -B -m unittest tools.test_soniq_serial_audio_companion -v` → 9 passed. Test-only byte fixtures exercise COBS, ordering, CRC, timeout, metadata, resynchronization, and WAV wrapping; no test fixture was classified or represented as microphone audio. |
| Dashboard suite | PASS | Installed Node 24.20.0 executable ran `node --test dashboard/backend-adapter.test.mjs dashboard/dashboard.test.mjs` → 25 passed, 0 failed. A first invocation from the default sandbox could not access the executable; approved invocation completed the suite. |
| Backend health | PASS | Live local backend `/health` returned `status=online`. Warning configuration correctly stayed `not_ready`. |
| LAN bind on host | PASS | `BACKEND_HOST=0.0.0.0`, port `18132`; health was `online` from `127.0.0.1` and host Ethernet IPv4 `[PRIVATE_LAN_IPV4]`. Temporary process stopped. This is a host-interface test, not another-device proof. |
| Second-device LAN request | NOT TESTED | No peer device was available. No firewall rule was changed. |
| Real WAV metadata | PASS | `01_StudentConversation.wav`: PCM WAV, 44,100 Hz, mono, 16-bit, 2,906,187 frames, 65.900 seconds. These are file properties, not an ESP32 capture. |
| Actual model load/inference | PASS | Existing `experimental_model.joblib` via real backend `/api/v1/classify` and companion client. HTTP 200; `Student Conversation`; `predict_proba=0.9401317274506633`, `calibrated=false`; model marked not evaluated. No model weights or preprocessing changed. |
| Model evaluation metrics | BLOCKED | The active manifest is `local_only_expanded_school_demo_unreviewed`, has 12 fitted recordings and `evaluation=null`; weak labels and formal reviews remain pending. No valid held-out metrics computed. |
| Actual classification → warning policy | PASS | Actual returned class/time passed in memory through `process_event` with `confident=false`, `sound_level=null`. Response: `warning.triggered=false`, reason `sound_level_unavailable`; sound-level status `unavailable`. No warning or event was persisted. |
| Invalid audio | PASS | Existing backend HTTP tests reject malformed/truncated WAV and wrong content type. New test submits a clearly labeled synthetic 181-second zero-PCM fixture and confirms HTTP 400 `invalid_audio` before inference. It is a boundary test fixture only. |
| Inference failure handling | PASS | Existing regression test verifies hidden internal details and HTTP 503 `inference_unavailable`. |
| PostgreSQL installation/configuration | BLOCKED | No `SONIQ_DATABASE_URL`/`.env`, service, listener, `psql`, Docker, or configured driver. Admin-role check false; WinGet executable access denied. No installation attempt, database replacement, or migration. |
| Event insertion/retrieval/restart persistence | BLOCKED | No PostgreSQL target. No event was posted, inserted, or fabricated. Existing route tests cover storage-unavailable and duplicate mappings with test doubles, not a live database. |
| Serial hardware | BLOCKED | `Get-CimInstance Win32_SerialPort` returned `NO_ROWS`; filtered `Win32_PnPEntity` returned `NO_ROWS`; `Get-PnpDevice -PresentOnly` had no ESP32/USB-serial device. |
| Host serial receiver against hardware | NOT TESTED | Parser tests pass, but current firmware emits no SQAU/1, no COM port is present, and pyserial was not installed. |
| Browser rendering | BLOCKED | Chrome and Edge headless attempted with local static server/backend. Both exited `-2147483645` without DOM; stderr reported “GPU process isn't usable.” Dashboard Node tests and previous static/CORS smoke passed, but visual rendering did not. |
| Event endpoint with actual model-derived event | BLOCKED | No POST was sent. Automatic review rejected a host-generated event request because an available database could make it durable. API event submission and persistence therefore remain unverified beyond existing tests. |

## Commands and configuration for Python suites

```powershell
$env:PYTHONPATH = (Resolve-Path 'ml\.venv\Lib\site-packages').Path
$env:NUMBA_DISABLE_JIT = '1'
& .\.venv\Scripts\python.exe -B -m unittest discover -s backend/tests
& .\.venv\Scripts\python.exe -B -m unittest discover -s ml/tests
Remove-Item Env:PYTHONPATH,Env:NUMBA_DISABLE_JIT
```

The classifier artifact was selected only in the test process using `SONIQ_AUDIO_MODEL_PATH` pointing to `ml\artifacts\expanded-local-demo-20261020\experimental_model.joblib`. Existing package files were reused; no requirements were installed in the root venv. Numba was disabled using its process environment variable, not by changing a security setting.

## Test interpretation

The successful classification is real model execution on an existing local WAV, but it is not model validation or an ESP32 capture. Protocol frames were generated only for parser tests. The warning test used the actual model label with safe missing inputs. PostgreSQL and browser UI results are not inferred from unit tests.
