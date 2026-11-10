# SONIQ Step 13 Proposed Package Inventory

Approved source: recovered Git snapshot origin/handoff/soniq-complete-project-2026-11-09 (a7e7a240dddfe8a256ed401822e7ee1dc25508c8), plus verified dataset ZIP and Step 12/13 audit reports. Final package assembled and verified; package inventory and verification are included.

| Package section | Recovered snapshot count / planned contents | Status |
|---|---|---|
| Project root and handoff docs | 39 root files, including README, setup/readiness docs, manifest and publish docs | Snapshot present; three manifest conflicts included from recovered ref, labeled with approval exception |
| VS Code | 1 launch configuration | Present |
| Backend | 12 files, API/repository/migration/tests/dependencies | Present in snapshot; backend tests blocked |
| Dashboard | 9 files, HTML/CSS/ES modules/tests/README | Present in snapshot; tests passed 25/25 |
| Firmware | 3 files, ESP32 sketch and placeholder/docs | Present; compile/hardware not tested |
| ML code and data structure | 48 files in handoff tree, including placeholders/config/tests | Present; training recordings supplied separately |
| Model artifacts | 7 files (3 joblib, 3 metadata JSON, 1 model dataset manifest) | Local hashes verified |
| Dataset archive/checksums | 69-file ZIP and CSV sidecar | Copied to approved durable path; both archive SHA and 69 inner hashes verified |
| Setup instructions | README, environment templates, DB docs, second-PC guide | Second-PC guide is one unresolved manifest conflict |
| Test/handoff reports | Existing manifest reports plus Step 12/13 audit reports | Included: eight Step 12 and eight Step 13 markdown reports plus the Step 13 path CSV |
| External dependencies | Python/NumPy/SciPy/librosa/scikit-learn/joblib/psycopg, Node, PostgreSQL, Arduino ESP32 core/tooling, hardware | Not bundled; versions/setup recorded in source docs/requirements |

Secrets policy: include .env.example only; exclude actual .env, tokens, passwords, and local virtual environments. Secret marker scan found no private-key, AWS access-key, or GitHub token patterns; no actual `.env` files are included. Approved: use recovered snapshot versions for the three conflicted docs and nine PC-49 variants; preserve local counterparts. The 40 absent PC-49 paths are present in the selected recovered snapshot. Excluded by approval: .git, local virtual environments, actual .env files, credentials, and PC-49-only files outside the approved inventory.




