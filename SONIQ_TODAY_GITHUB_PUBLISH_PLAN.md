# SONIQ Today GitHub Publish Plan

**Prepared:** 2026-11-09 (Asia/Manila)  
**State:** PREPARATION ONLY. No index, branch, commit, remote, or existing working file was changed for this Git review. This report is the requested new untracked file.

## 1. Git snapshot

| Item | Observed state |
|---|---|
| Branch | `main` |
| Current `HEAD` | `7b3e66db39b2d74667da4fcea2f07eeab112731b` |
| Tracking | Local `main` tracks `origin/main`; displayed ahead/behind counts are empty. |
| Remote | `origin` fetch/push: `https://github.com/earlentero20-sketch/adaptive_classroom-noise-monitoring_and_warning-system_using-Aiot.git` |
| Staged | 9,416 staged deletions; `git diff --cached --shortstat` reports 9,416 files and 2,170,919 deletions. These are pre-existing and must remain untouched. |
| Unstaged tracked changes | 0 |
| Untracked files | 107 individual files in the full `git status --porcelain=v1 --untracked-files=all` enumeration before this report was created. The plan itself adds one untracked file. |
| Merge/rebase/cherry-pick | None detected; no unmerged index entries or operation markers. |

Important status detail: `backend/app.py`, `backend/tests/test_app.py`, and `ml/audio_inference.py` each appear as a staged deletion **and** as an untracked working-tree copy. The staged deletion must not be undone. The working copies contain earlier SONIQ edits in addition to today’s edits; do not add these whole copies blindly.

## 2. Changes identified from today’s final integration mission

The following 11 paths are the candidate allowlist. For the three source/test paths that overlap staged deletions, the proposed commit must contain only reviewed today-specific hunks unless the related earlier hunks are explicitly approved as dependencies.

1. `SONIQ_FINAL_INTEGRATION_REPORT.md` — current system result and readiness.
2. `SONIQ_FINAL_ACTUAL_TEST_RESULTS.md` — executed test evidence.
3. `SONIQ_FINAL_DEMONSTRATION_GUIDE.md` — verified software demonstration procedure and limits.
4. `SONIQ_FINAL_REMAINING_BLOCKERS.md` — outstanding readiness conditions.
5. `docs/USB_SERIAL_AUDIO_PROTOCOL.md` — candidate SQAU/1 host protocol, explicitly not firmware-verified.
6. `backend/app.py` — today’s 180-second WAV-duration guard and validated metadata use.
7. `backend/tests/test_app.py` — today’s 180-second boundary and over-limit tests/fixture. This working copy also contains the earlier Step 10 stub-server test repair; isolate today’s hunks unless the earlier repair is separately approved.
8. `ml/audio_inference.py` — today’s `validate_wav_sample` return of verified audio properties.
9. `tools/soniq_serial_audio_companion.py` — host-side receiver/parser and opt-in client.
10. `tools/test_soniq_serial_audio_companion.py` — parser tests using clearly marked protocol-only byte fixtures.
11. `tools/requirements-serial.txt` — optional `pyserial` requirement; it was not installed.

Source delta review against the current commit confirms that the working copies include earlier changes: `backend/app.py` differs by 39 insertions/5 deletions, mostly the prior LAN-bind and degraded-PostgreSQL-start behavior; `backend/tests/test_app.py` differs by 110 insertions/4 deletions, including the earlier Step 10 test repair; `ml/audio_inference.py` differs by 4 insertions/3 deletions. The individual changes from this mission are limited to the duration validation, audio metadata return, and the two boundary tests/helper. A publish commit should not accidentally turn the entire staged deletion into a re-add or silently bundle unrelated prior work.

## 3. Privacy and generated-file checks

- The 11 candidate paths contain no detected credential-like assignments, credential-bearing PostgreSQL URLs, GitHub token patterns, or AWS access-key patterns.
- No real `.env` file is in the candidate list. The repository’s untracked `.env.example` is deliberately excluded; it contains placeholders, not credentials.
- No virtual environment, cache, `node_modules`, temporary file, or candidate file larger than 10 MiB is in the allowlist.
- **Privacy cleanup needed before publication:** `SONIQ_FINAL_INTEGRATION_REPORT.md`, `SONIQ_FINAL_ACTUAL_TEST_RESULTS.md`, and `SONIQ_FINAL_DEMONSTRATION_GUIDE.md` include the workstation’s private IPv4 address observed during the LAN check. Replace that address with a placeholder in the isolated publishing worktree before staging. `backend/app.py` contains private-address range logic, which is code rather than a machine-specific address/configuration.
- The final reports describe the current working copy’s LAN bind and degraded database startup. The committed `HEAD` still has a loopback-only host check and requires PostgreSQL at startup. If only today’s hunks are committed, the reports will describe behavior not present in that commit. Decide whether to include the related earlier LAN/degraded-startup hunks and their tests, or revise the publication copy of the reports. Do not copy the complete current source files without reviewing those earlier changes.

## 4. Deliberately excluded files and state

- All 9,416 staged deletions and all unrelated untracked files.
- Historical Step 1–10 reports, prior master/release/demo reports, the pre-existing `SONIQ_FINAL_BLOCKERS.md`, and older integration guides. They are already untracked working files and are not part of today’s candidate set.
- `README.md`, `.env.example`, `.gitignore`, `.gitattributes`, `start_soniq.bat`, older backend/dashboard/firmware/ML source and tests, datasets, model artifacts, and generated content. These are pre-existing work or outside the requested final-integration delta; do not add them by directory.
- `.venv`, `ml/.venv`, credentials, local database files, test audio, and caches.

The current repository snapshot contains many pre-existing untracked project files, including complete source directories. Selecting only the allowlist is essential. No broad add command is appropriate.

## 5. Proposed isolated publishing strategy

After approval of the file list and the two content questions above:

1. Create a separate worktree and topic branch from the recorded `HEAD`, leaving this `main` worktree and its index untouched. Suggested branch: `codex/soniq-final-integration-2026-11-09`.
2. In that isolated worktree, apply only the approved source/test hunks and copy only the approved new files. Redact the workstation IPv4 from the three report/guide copies. Include prior LAN/degraded-startup changes only if separately approved because the reports depend on them.
3. Review the isolated staged name-status list against the allowlist; require zero deletions, inspect the complete staged diff, run a secret scan, and run `git diff --cached --check` before any commit.
4. Proposed commit message: `feat: complete SONIQ audio integration and verification`.
5. Create the commit only after separate explicit authorization. Do not push until separately authorized.

This method avoids modifying or consuming the existing `main` index, and cannot carry its 9,416 staged deletions into the isolated commit unless someone deliberately adds them. No worktree, topic branch, staging, commit, or push has been created during this preparation.

## 6. Approval questions / unresolved risks

1. Approve the 11-path allowlist, with the three report copies redacted in the isolated worktree?
2. Should the commit include the related earlier LAN-bind/degraded-startup and test-repair hunks needed for consistency, or should those reports be revised so the commit describes only behavior available at `HEAD` plus today’s changes?

No files have been staged or committed. This plan stops here for review.
