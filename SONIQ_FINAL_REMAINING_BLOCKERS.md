# SONIQ Final Blockers

| Blocker | Status | Required action |
|---|---|---|
| No physical ESP32 or COM port detected | BLOCKED | Connect the actual board using a data-capable USB cable; inspect Device Manager/PnP and identify the board and USB-UART device before firmware or serial integration. |
| Firmware does not transmit classifier-compatible audio | BLOCKED | Establish hardware/sample format and approve an audio transport/protocol. Existing firmware sends event JSON only; preserve current behavior until compatibility is established. |
| Existing model is experimental and not evaluated | BLOCKED | Obtain data/model-owner review and a valid evaluation plan. Do not claim the demo label is accurate; do not retrain or replace the artifact. |
| Root `.venv` lacks model dependencies | PARTIALLY COMPLETE | Current software inference works by process-scoped reuse of `ml/.venv/Lib/site-packages` plus `NUMBA_DISABLE_JIT=1`. For a durable install, obtain approval to install only declared requirements into the root environment and validate in that environment. Legacy `ml/.venv` remains broken. |
| PostgreSQL unavailable/unconfigured | BLOCKED | Privately configure the intended existing `soniq_db` URL and credentials, make its PostgreSQL service reachable, provide the declared driver, inspect existing tables, then test insertion/retrieval without migrations unless separately reviewed. |
| No persisted event for dashboard | BLOCKED | Resolve PostgreSQL and send a genuine compatible event through the existing contract; verify retrieval and dashboard display. Do not seed synthetic events. |
| Warning chain lacks verified inputs | BLOCKED | Establish the approved mapping for model output to event confidence and provide fresh calibrated SPL. Classifier endpoint explicitly does not run the warning policy; existing event policy must remain fail-closed until requirements are met. |
| SPL calibration | BLOCKED | Calibrate the actual microphone/system against an appropriate reference over the intended frequency/level range, document method/uncertainty, and only then mark measurements calibrated. Current firmware RMS is not dB SPL. |
| Browser and peer-device verification | NOT TESTED | Open the dashboard in the target browser and test a private-LAN client from another device after confirming firewall/profile rules. Current tests are Node and loopback software checks. |
| External network exposure | NOT TESTED | Keep router forwarding disabled. Backend LAN mode is intended only for trusted local subnet; authentication/external exposure is not established. |

## Practical ESP32 detection steps

1. Connect a data-capable cable directly to the Windows PC and check Device Manager, including “Other devices.”
2. Run `Get-PnpDevice -PresentOnly`, `Get-CimInstance Win32_SerialPort`, and `Get-CimInstance Win32_PnPEntity`; capture observed hardware IDs/COM name without guessing the board or USB-UART driver.
3. Install only the driver identified by the hardware ID, if Windows reports it missing; then record the actual COM port.
4. Verify board revision, microphone model/wiring, actual I2S word alignment, sample rate, free memory, transport throughput, and packet protocol before implementing a receiver.

## Database prerequisites

Use the existing database and schema. A database owner must provide the connection URL through an ignored/private environment file or environment variable; never place it in source or reports. Confirm the `soniq_db` host/port/database/role privately. Then inspect the existing `events` and migration ledger before deciding whether any migration is appropriate. No credentials, schema, or database records were inspected or changed in this run.
