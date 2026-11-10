# SONIQ Step 12 Test Results

| Check | Status | Result |
|---|---|---|
| Dataset ZIP readability and file checksums | PASSED | 69/69 source files verified |
| Model artifact presence/hash | PASSED | 7/7 files match manifest |
| Dashboard tests | PASSED | 
ode --test dashboard/*.test.mjs: 25 passed, 0 failed, 0 skipped |
| Backend unit tests | BLOCKED | Python executable missing/inaccessible (C:\Users\admin\...\python.exe) |
| Backend/PostgreSQL integration | NOT TESTED | No database connection attempted |
| ML loading/inference | BLOCKED | Python runtime unavailable; no model loaded |
| Firmware compilation | BLOCKED | rduino-cli unavailable |
| ESP32 behavior and end-to-end integration | NOT TESTED | Hardware unavailable |
| Remote branch freshness | BLOCKED | GitHub connection failed on port 443 |
| Handoff manifest vs tree | FAILED | 117/120 unique entries match; 3 differences recorded in manifest comparison |

Do not treat blocked or untested items as passes.

