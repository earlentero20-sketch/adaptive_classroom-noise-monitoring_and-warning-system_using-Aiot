# SONIQ Complete Handoff Publish Plan

## Proposed snapshot

- Branch: `handoff/soniq-complete-project-2026-11-09`
- Base: `7b3e66db39b2d74667da4fcea2f07eeab112731b` (`main` at preparation time)
- Remote: `origin` — `https://github.com/earlentero20-sketch/adaptive_classroom-noise-monitoring_and_warning-system_using-Aiot.git`
- Worktree: `C:\Users\PC-21\Documents\soniq-handoff-2026-11-09`
- Proposed commit message after explicit approval: `Prepare SONIQ complete second-PC handoff`

The handoff branch is staged for review only. No commit or push has been made. The original `main` worktree/index is separate and must retain its 9,416 staged deletions and existing untracked files.

## Included content

The snapshot carries current untracked source/documentation deliverables and restores the current working copies of project files that were deleted in the original index. It removes the tracked virtual environment and audio/data material from the handoff branch, retaining only safe manifests and examples, and adds the setup guide, exclusions, manifest, and this plan. `SONIQ_COMPLETE_HANDOFF_MANIFEST.md` is the exact staged file inventory and SHA-256 record. Review `git diff --cached --name-status` in this worktree for the full list; it is intentionally not reproduced here because it contains thousands of environment/data deletions.

The original tracked project plus current additions are preserved in the proposed snapshot except explicitly excluded virtual environment, audio recordings, and pending-review metadata detailed in `SONIQ_HANDOFF_EXCLUSIONS.md`. Model files are included and checksummed; no model retraining/replacement was performed.

## Validation and risks

The recorded backend, ML, serial parser, and dashboard test results are summarized in `SONIQ_STEP10_TEST_RESULTS.md`. PostgreSQL and physical ESP32 testing were unavailable; no live hardware-to-dashboard result is claimed. All dataset audio was withheld pending rights/privacy review. Transfer uses ordinary Git model files; no dataset audio LFS transfer is proposed. Verify the GitHub remote's access and branch policy before publication.

Credential and private-address scans must be rechecked against this snapshot before approving publication. `.env` is excluded; `.env.example` is safe placeholder configuration. The firmware requires a second-PC LAN endpoint to be set locally.

## Exact publication sequence after approval

1. Review this plan, exclusions, manifest, and staged change list in the handoff worktree.
2. On approval of this exact snapshot and strategy, commit only the staged changes on the handoff branch.
3. Push only `handoff/soniq-complete-project-2026-11-09` to `origin` if separately authorized. Do not push `main` or publish excluded content.

No commit, push, or original-index modification is authorized by this plan.

## Snapshot review details

- Proposed included tree: the 121 paths listed in `SONIQ_COMPLETE_HANDOFF_MANIFEST.md` (120 checksummed files plus the self-referential manifest entry). This is the exact included-file list.
- Staged change summary: 41 additions, 9 modifications, and 9,336 deletions. All deletions are isolated to `ml/.venv` (9,270 paths) and `ml/data` (66 paths). The six retained data paths are the manifests, schema examples, and empty placeholders listed in the manifest.
- LFS inventory resolves only to paths under the excluded virtual environment and dataset; no LFS download/upload is needed for the included snapshot.
- Preservation recheck: original `main` remains at the base hash with 9,416 staged deletions, 0 unstaged tracked changes, and 108 untracked files. No merge/rebase is in progress.
- `git diff --cached --check` reports existing trailing spaces in copied Markdown reports, used as Markdown hard line breaks. No source changes were made to remove them.
- Credential-address scan found no `.env` or local database files and no hardcoded private HTTP URL in the handoff. `.env.example` contains generic `USER`/`PASSWORD` placeholders only. The copied firmware endpoint is a `YOUR_COMPUTER_LAN_IPV4` placeholder.
