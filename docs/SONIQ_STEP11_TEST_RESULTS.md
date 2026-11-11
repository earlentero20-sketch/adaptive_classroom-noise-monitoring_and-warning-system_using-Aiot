# SONIQ Step 11 Test Results

| Check | Result | Evidence |
|---|---|---|
| Dataset archive entries and SHA-256 | PASS | 69/69 entries match source manifest; ZIP opens |
| Dashboard tests | PASS | 
ode --test dashboard/*.test.mjs: 25 passed, 0 failed, 0 skipped |
| Backend tests | BLOCKED | Python executable could not run: configured Python 3.13 path refers to missing C:\Users\admin\...\python.exe; system python.exe was inaccessible |
| Dashboard npm test script | BLOCKED | No dashboard/package.json exists; direct Node test runner succeeded |
| PostgreSQL integration | NOT TESTED | Database service/access unavailable in this audit |
| ESP32/hardware integration | NOT TESTED | Hardware unavailable |
| Model load/inference | NOT TESTED | Artifact presence checked only |
| Dependencies | PARTIAL | backend/ml requirements files present; dashboard has no package manifest |

No hardware/database integration success is claimed.
