# Classroom Audio Collection Protocol

Per the team's update, school permission to conduct classroom recording has
been received. This protocol does not independently verify its scope or
conditions. Before collection, document the permission and confirm it covers
the specific class, purpose, recording setup, and storage plan. Separately
complete the required participant consent/assent, privacy, storage, and
retention checks. The applicable school and local privacy rules must be
checked by the responsible people; this document is not a legal determination.

The current classifier labels only **Teacher Discussion** and **Student
Conversation**. A label describes the audible speech activity, not loudness.
The buzzer decision remains a separate conjunction: the classifier reports
Student Conversation and an independently measured, valid, calibrated sound
level is above the threshold agreed by the team. A class label or recording
gain alone must never imply excessive noise.

## Proposed workspace layout

```text
ml/data/
  classroom_collection/                 # local ignored collection workspace
    metadata.csv                        # copy the template; fill after review
    recording_log.csv                   # one non-identifying row per original
    audio/
      recordings/                       # candidate PCM WAV clips, each in metadata.csv
  metadata/
    classroom_metadata.example.csv      # header-only schema template
    classroom_recording_log.example.csv # header-only collection-log template
```

The planned storage is a restricted Google Drive folder. Before collection,
confirm the account and folder are school-approved, access is limited to named
authorized people, sharing settings prevent public access, and the retention,
backup, and deletion arrangements meet the school's requirements. A restricted
folder is not, by itself, proof of approval or a secure-storage review. Copy data
into this ignored workspace only if the school also approves this device and
storage location. Raw audio and generated artifacts are ignored by `ml/.gitignore`;
still verify Git status and never force-add audio, consent documents, or
identifying metadata. Ignore rules are a guardrail, not secure storage: they do
not protect files outside `ml/`, and force-adding or already tracked files can
bypass them. Keep identity keys and signed consent records outside the
repository in approved restricted storage; verify both `git status` and the
tracked-file list before any handoff. The example CSV has only the pipeline's
column header and contains no consent or approval claims.

The two header-only CSV examples are the only data-folder exceptions in the
ML ignore rules. Copy each into `classroom_collection/` before filling it in;
keep completed metadata, recording logs, raw audio, and all private records in
approved restricted storage. The collection log is not the ML metadata CSV:
it has one row per original recording, while `metadata.csv` has one row per
reviewed clip. Do not fill in or commit either example template.

Copy `ml/data/metadata/classroom_metadata.example.csv` to
`ml/data/classroom_collection/metadata.csv`. Put WAV files under
`ml/data/classroom_collection/audio/recordings/`. In the run configuration,
set `dataset_root` to `../data/classroom_collection` and keep
`metadata_csv` as `metadata.csv` (relative to the dataset root).
Copy `ml/data/metadata/classroom_recording_log.example.csv` to
`ml/data/classroom_collection/recording_log.csv` and add one row per original
recording. Use only opaque source, recording, session, room, and review codes.
Its secure-record reference must point to a restricted record without
including a participant name or identity key. The log records class coverage,
conditions, observed device format/settings, quality review, and annotation
status; it does not replace clip-level labels in `metadata.csv`.
In the recording-log template, `teacher_discussion_present` and
`student_conversation_present` describe original-level class coverage using
`yes`, `no`, or `unclear`; `ambiguous_intervals_present` uses the same values.
Use `pending`, `pass`, or `fail` for `quality_review_status`, and
`pending`, `reviewed`, or `ambiguous` for `annotation_status`. The device
columns record the observed export, not a desired setting. Keep notes
non-identifying and put detailed interval/reviewer records in approved secure
storage, referenced only by opaque codes.

## Approvals and participant protections

Document the school permission already received and verify its scope and any
conditions for the purpose, class, location, recording period, access list,
storage, review, sharing, and deletion plan. Confirm the responsible school
contact for questions about those conditions. Use the school's approved
consent process for the teacher and every
recorded participant; obtain guardian permission and student assent where
school policy or applicable rules require them. Participation must be
voluntary, and the class must have a practical non-recorded alternative.
Explain the recording purpose, what is captured, who can listen, how clips are
used, retention/deletion dates, and how a participant can raise a concern.
Do not record until approvals and consent are complete and the responsible
person has checked them. The metadata references are evidence pointers for
human review, not proof of approval.

Do not capture video, names, student numbers, private conversations outside
the approved lesson activity, or unrelated classes. Use opaque IDs in filenames
and metadata. Keep the identity/consent key separate from audio and ML
metadata, encrypted and accessible only to the designated custodian. Do not
put consent forms, participant lists, or identifying notes in the repository.

Restrict raw audio to the approved custodian and label reviewers. Use an
institution-approved encrypted device/storage location, access controls, and
secure transfer. Keep an access log if required by the school. Set a specific
retention/deletion date before collection; delete raw audio, working copies,
exports, and backups at that date or sooner if approval is withdrawn or the
school requires it. Record deletion completion without retaining audio or
identifying details. The teacher/team lead must approve the final access and
retention plan before collection.

## Recording procedure

1. The selected setup is a Vivo Y22s using PCM Recorder, configured for WAV,
   signed 16-bit PCM, 44,100 Hz, mono. Confirm the exported WAV header reports
   uncompressed PCM (`comptype` `NONE`), 2-byte samples, 44,100 Hz, and one
   channel; the pipeline accepts PCM WAV with 1-4 byte samples and positive
   rates/channels. Actual device output has not been inspected yet. The example
   preprocessing target of 16 kHz is a later processing setting, not a capture
   rate. Preserve originals; do not normalize or resample recordings by hand.
2. Use a fixed, documented microphone position for each session. Place it so
   the approved teacher and student speech is intelligible, away from direct
   contact, handling noise, loudspeakers, and obstructions. Do not move it or
   change gain mid-session. Log anonymous `source_id`, room/session conditions,
   microphone model, placement, and recorder settings in a restricted,
   non-identifying collection log. These fields are not part of the current
   metadata schema.
3. Before and after the lesson, record a short non-speech setup check only if
   the school-approved protocol permits it. Listen for clipping, dropouts,
   handling noise, and unintelligibility. This check is not a sound-level
   calibration. A future warning threshold requires a separate calibrated
   measurement path and team approval.
4. Capture natural lesson activity; do not prompt students to perform louder
   speech or stage classroom disruption. Note session boundaries and mark
   intervals to exclude without storing personal notes in the ML workspace.
5. Preserve each master original in approved restricted storage. Candidate
   WAV clips/windows placed under `dataset_root` must each have a metadata row
   and distinct `clip_id`/path, while retaining the exact same `source_id` and
   `original_recording_id` as their master. The validator requires a row for
   every WAV found under `dataset_root`; do not put extra master WAVs there
   unless they too are labeled candidate samples. Never treat crops of one
   master as independent recordings.

## Labeling and ambiguous clips

- **Teacher Discussion:** the teacher is the clearly audible primary speaker
  giving instruction, explanation, or leading a lesson exchange. A student
  acknowledgment does not change the label when the teacher remains clearly
  primary.
- **Student Conversation:** student-to-student conversation is clearly
  audible as the primary speech activity. It remains this class whether quiet
  or loud; loudness is measured separately.
- Label short fixed-duration windows only when the target activity is clear
  throughout the window. Use the duration approved for the baseline config;
  the example's one-second preprocessing window is a starting setting, not a
  final collection requirement.
- If teacher and student speech overlap and neither target activity is
  clearly primary, or the voices/role cannot be determined, do not guess. Mark
  the review as ambiguous, send it for independent human review, and either
  resolve it under the team's written rule or exclude it from the candidate
  training dataset. Keep excluded audio in the approved restricted location,
  outside the directory passed to the readiness command. The current validator
  intentionally blocks the entire dataset when an ambiguous metadata row or
  unlisted audio file is inside that directory.
- Have two reviewers independently label pilot clips, then adjudicate
  disagreements with a named reviewer. Document the written decision rule
  before scaling annotation. Store only a non-identifying review reference in
  `annotation_review_ref`.

## IDs and metadata

Use unique opaque IDs, for example `COLL_A` for a collection and
`COLL_A_REC_001` for one original recording. For every crop from that original,
use a unique `clip_id`, a relative path such as
`audio/recordings/COLL_A_REC_001_CLIP_001.wav`, and keep
`original_recording_id=COLL_A_REC_001` and `source_id=COLL_A`. Never encode a
name, date of birth, student number, or class roster identity in IDs or paths.
`source_id` and `original_recording_id` together are the split key.

Fill one metadata row per clip using the exact header in
`ml/data/metadata/classroom_metadata.example.csv`:

| Field | What the collection team enters |
|---|---|
| `clip_id` | Unique opaque clip/window ID |
| `relative_path` | WAV path relative to `dataset_root` |
| `label` | Exactly `Teacher Discussion` or `Student Conversation` |
| `original_recording_id`, `source_id` | Stable group IDs shared by all derivatives |
| `source_type` | `classroom` |
| `source_reference` | Non-identifying collection/protocol record ID; leave empty if not yet known |
| `license_id`, `license_reference` | Applicable terms and human review record; leave unknown references empty |
| `approval_status`, `approval_reference` | `pending` until documented human approval; then `approved` with a real verified record pointer |
| `consent_ref` | Non-identifying consent/assent record pointer; leave empty until verified; never include the form or participant identity |
| `privacy_review_ref` | Non-identifying privacy review record pointer; leave empty until the review exists |
| `annotation_status`, `annotation_review_ref` | `pending`/`ambiguous` until a human reviews the audio; `reviewed` only with a real review record pointer |

Unknown reference fields may be empty. Do not enter `pending`, `unknown`, `TBD`,
or similar text as a fake reference ID. The validator accepts empty references
as truthful metadata, but reports them as blocking readiness issues when the
corresponding evidence is required. Status columns remain separate from
reference columns. Filenames do not verify a class label: keep
`annotation_status=pending` until a human has reviewed the clip contents.

School permission does not substitute for participant consent/assent. A
classroom row is not eligible for use unless permission/approval, participant
consent, privacy review, quality review, and annotation review have each been
completed and checked by responsible humans. A status value or reference string
alone is not proof. The recording log must have a matching original-recording
row with `quality_review_status=pass` and a real `quality_review_ref`; its
annotation status must be `reviewed` with a real `annotation_review_ref`.
Missing or pending review data blocks the row.

The CSV's `approved` and `reviewed` values are gates, not authorization.
Assign one unique opaque `source_id` for the collection/source and one unique
`original_recording_id` for each original audio file. Every clip derived from
that original keeps the exact same pair. Each clip gets its own unique
`clip_id` and relative path. Never reuse an original ID for a later session,
and never give crops separate group IDs. The recording log has one row per
original, while the metadata CSV has one row per candidate clip. Log whether
each class is present at the original level; label individual windows only
under the class rules above. For overlapping or unclear speech, note the
interval for review, hold it out of the candidate dataset until adjudicated,
and exclude it if it remains ambiguous. The readiness command intentionally
rejects ambiguous rows and unlisted audio inside the dataset directory. The
responsible humans must verify the underlying records. Keep the signed consent
and approval records separately in approved secure storage.

## Provisional collection target

For an initial planning round, aim for **about 30 independent original
recordings that contain clear examples of each class** (roughly 30 source
groups represented per class, not 30 crops). If separate sessions are needed
to capture the two activities, target about 30 recordings per class instead.
This is a planning estimate only, not a statistically proven minimum or a
guarantee of model quality. The team's review of time, permissions, and
available sessions should set the feasible target.

Vary teachers, student groups, lesson sessions, and approved room conditions
where possible. Repeated crops from one original add clips but no independent
source group; they cannot show whether the model generalizes to a new session
or speaker group. A useful evaluation needs distinct source groups in train,
validation, and test, with both labels represented in each. The current
readiness rule requires at least two distinct groups per class per split; this
is only a software gate, not a sufficiency claim. Under 70/15/15 grouped
splitting, collect substantially more than this floor because groups are not
stratified and some partitions can be class-incomplete.

The current pipeline prevents clips from one original recording crossing
splits. It does not know whether the same teacher or students appear in
different recordings, so recurring speakers could occur in both training and
test. Before collection, the team must decide whether the first evaluation
targets new recordings from familiar participants or generalization to unseen
participants. The latter needs an additional privacy-safe participant/session
grouping rule and pipeline support; do not claim a speaker-independent test
from the current recording-only split.

## Transfer and prepare the private dataset

1. Record only after the school-approved scope and the required participant
   consent/assent, privacy, access, storage, and retention checks are complete.
   Save originals directly to the approved encrypted location.
2. Review the original for the approved lesson content and technical quality.
   Keep unclear or excluded intervals in restricted review storage, not in the
   candidate dataset directory.
3. Keep master originals in the approved restricted storage. Copy only selected
   candidate PCM WAV clips/windows to
   `ml/data/classroom_collection/audio/recordings/` if that workspace location
   is approved. The validator requires a metadata row for every discovered WAV,
   so keep uncut master recordings outside `dataset_root` unless each master is
   itself an intentionally labeled candidate sample. Use opaque IDs only; never
   copy consent forms, identity keys, participant lists, or identifying notes.
4. Copy the recording-log example to `recording_log.csv`; create one row for
   each original, using its stable source/recording IDs, observed device
   settings, class coverage, quality result, and annotation status.
5. Copy the metadata example to `metadata.csv`; create one row per reviewed
   clip/window. Use exact two-class labels, unique clip IDs and paths, and the
   original's unchanged source/recording group IDs. Leave unknown references
   empty; keep the status pending until responsible humans have checked the
   underlying records.
6. Confirm the collection folder and private files are ignored and untracked.
   Keep the completed copies local; do not force-add them. If school policy
   does not approve this workspace as storage, keep the data outside it and
   configure the runner only through an approved location.
7. Copy the run configuration with
   `Copy-Item ml/config/first-baseline.example.json ml/config/first-baseline.json`,
   then edit only the local copy's dataset path as described below. Run the
   data check and inspect all issues and group/class counts before any training.

## Before the readiness command

The collection owner and label reviewers should confirm all of these:

- [ ] School approval and required participant/guardian consent and assent are
  complete for the approved purpose, storage, access, and retention period.
- [ ] Vivo Y22s and PCM Recorder export is confirmed from an actual WAV file:
  uncompressed signed 16-bit PCM, 44,100 Hz, mono; microphone placement and
  gain settings are documented.
- [ ] Every selected file is intelligible, unclipped, complete PCM WAV with no
  unintended content; excluded/ambiguous files are outside `dataset_root`.
- [ ] Labels follow the written two-class rule; overlap/uncertainty was
  independently reviewed and adjudicated or excluded.
- [ ] Each clip has a unique ID/path, exact class label, stable source group,
  source/license/protocol references where known, verified approval, consent,
  privacy, quality, and annotation reviews. Leave unknown reference cells empty
  and keep statuses pending; do not use placeholder words as references.
- [ ] All derivatives of an original share its source group IDs, and no group
  is being counted as independent merely because it produced many clips.
- [ ] The metadata CSV contains at least one row and every WAV in
  `dataset_root` is listed. Unresolved or unapproved rows are not marked ready.
- [ ] Git status confirms raw audio and sensitive records are not staged or
  tracked; the school's storage and deletion plan is still in force.

Then copy the example run config, set its dataset root to the approved
collection directory, and run:

```powershell
python -m ml.run_baseline --check-data ml/config/first-baseline.json
```
The checked-in `first-baseline.example.json` deliberately has a placeholder
`dataset_root`. In the local config copy for the folder layout above, set it to
`../data/classroom_collection`; leave `metadata_csv` as `metadata.csv`. The
runner resolves `dataset_root` relative to the config file and the metadata
CSV relative to that dataset root. This aligns with the command above and does
not imply that recordings or approvals exist.

Review `grouped_split_ready_for_baseline`, every split's per-class clip count,
and independent group count. Resolve all validation issues and ensure both
classes have adequate independent groups in every split before approving a
real training run. Empty/placeholder references, pending reviews, or missing
classroom recording-log quality/annotation review block readiness. The check
does not prove permissions or consent; responsible humans must verify each
underlying record. Four original recordings cannot satisfy the current rule
of at least two independent original groups per class in each of train,
validation, and test. Never duplicate recordings or invent group IDs to pass
that check.

## Decisions required before recording

The teacher/team lead and school contact must confirm the scope and conditions
of the permission already received. They must decide: which participants are
in scope and the consent/assent process; the approved rooms/times; the
microphone/recorder and
placement/settings; the retention period, access list, storage device/location,
and deletion owner; the written labeling and overlap rule; and who adjudicates
labels. Confirm the initial collection target and whether the candidate source
data may be used in the academic project. No recording begins until these are
approved and the required consent is complete.

They must also decide whether evaluation should generalize to unseen
participants. Current metadata and split logic enforce only original-recording
separation.

The sound-level calibration method and numerical warning threshold are separate
team decisions. They are required before buzzer behavior is enabled or
validated, but they do not change the two audio labels and need not be
estimated from the training recordings.
