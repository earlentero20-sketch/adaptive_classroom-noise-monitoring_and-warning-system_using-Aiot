# SONIQ Step 13 Test Results

| Check | Status | Evidence / next command |
|---|---|---|
| Dataset archive | PASSED | ZIP readable; 69/69 file hashes match sidecar |
| Model artifact inventory | PASSED | 7/7 local files match manifest size/hash |
| Dashboard tests | PASSED | `node --test dashboard/*.test.mjs`: 25 passed, 0 failed, 0 skipped |
| Backend unit tests | BLOCKED | Python runtime unavailable; later run `python -m pytest backend/tests` |
| ML tests/model inference | BLOCKED | Python runtime unavailable; later run `python -m pytest ml/tests` and the project inference script |
| Firmware compile | BLOCKED | `arduino-cli` unavailable; later compile `firmware/ESP32_SONIQ_Integrated_V2/ESP32_SONIQ_Integrated_V2.ino` with configured ESP32 board/core and required libraries |
| Database connectivity | NOT TESTED | Requires configured PostgreSQL service and safe local credentials |
| ESP32/hardware/end-to-end | NOT TESTED | No hardware available |
| Manifest file hashes | FAILED | 117/120 unique entries verify; three discrepancies listed in conflict report |
| PC-21/GitHub remote availability | BLOCKED | PC-21 paths absent; GitHub HTTPS connection failed on port 443 |

No tools or system configuration were installed or changed. Python/Arduino tooling installation requires separate approval.
