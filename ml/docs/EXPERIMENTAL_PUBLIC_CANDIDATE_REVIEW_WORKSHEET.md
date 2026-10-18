# Experimental Public Recording Review Worksheet

Purpose: triage public recordings for the exact classes `Teacher Discussion` and `Student Conversation`. This is a blank working worksheet, not a review record, approval, or evidence. Keep detailed reviewer records in a project-approved restricted location; do not place private participant details here. Add only genuine non-identifying references to the candidate mapping after the underlying record exists.

## Review protocol

- Content decision: `Teacher Discussion` only when the teacher is clearly the primary speaker giving instruction, explanation, or leading a lesson exchange; `Student Conversation` only when student-to-student conversation is the clear primary speech activity. Loudness is not a class.
- If speech cannot be verified, both classes are materially present without a clear dominant class, or the activity is only ambiguous murmur, choose `Mixed/ambiguous` or `Exclude`; record non-identifying notes and time intervals. Do not force a label.
- For every selected asset, verify the exact source asset and its current license/conditions, then have the project lead decide and record project-use approval. A public license or source-page observation is not project approval.
- Separately complete a human review of participant-rights/consent applicability, privacy, and audio quality. The inventory’s structural WAV scan does not replace listening quality review.
- Current pipeline intake accepts readable uncompressed PCM WAV only. Do not convert unsupported formats until source and rights reviews clear the asset. Never count byte-identical copies as separate recordings.

## Current selected shortlist (unique assets)

`Source/license evidence observed` below is copied from the project preparation notes and selected-file mapping; team verification and applicability review are still required. All listed candidates still lack completed project approval, formal annotation review references, privacy review, participant-rights/consent applicability decisions, and audio-quality review.

| Candidate path under `ml/data/classroom_collection/` | Proposed class (unverified unless reviewer confirms) | Existing source/license observation | Reviewer decision / notes / intervals | Outstanding candidate-specific work |
|---|---|---|---|---|
| `audio/recordings/115386__adamlhumphreys__groupofcollegestudentsinclassroom.wav` | Student Conversation | Freesound 115386; CC BY-NC 4.0 observed. Attribution and noncommercial conditions noted. | ____________________ | Verify exact asset, license conditions and compatibility with project use; confirm class by listening. |
| `audio/recordings/155599__claudiooliveira2__students-talking.wav` | Student Conversation; user-reported listening decision, formal record pending | Freesound 155599; CC0 observed. | ____________________ | Verify exact asset and CC0 applicability; formalize the reported label decision. |
| `audio/recordings/188214__splicesound__science-teacher-lecturing.wav` | Teacher Discussion; user-reported listening decision, formal record pending | Freesound 188214; CC0 observed. | ____________________ | Verify exact asset and CC0 applicability; formalize the reported label decision. |
| `audio/recordings/23202__lg__lecture09.wav` | Teacher Discussion (unverified; conflicts with available source description) | Legacy Freesound ID linked by a forum post; current exact source/license not verified. | ____________________ | Find exact current source and license; listen to resolve class conflict. Current validator rejects IMA ADPCM encoding. Keep excluded unless source and terms are established. |
| `audio/recordings/233453__dmadridp__teacher-speech.wav` | Teacher Discussion | Freesound 233453; CC BY 3.0 observed; source description places speech in a corridor during class. | ____________________ | Verify exact asset and attribution conditions; listen to confirm target activity and class fit. |
| `audio/recordings/256189__cyweb__students-lunchtime.wav` | Student Conversation (unverified) | Contributor profile has a general no-restrictions statement; asset-specific source/license not verified. | ____________________ | Obtain exact sound record and asset-specific terms; otherwise keep excluded. Listen to confirm class. |
| `audio/recordings/335031__heraclitopd__students-chatting-amb.wav` | Student Conversation (unverified) | No matching exact source page/license located in project notes. | ____________________ | Establish exact source/license; otherwise keep excluded. Do not use the byte-identical `(1)` copy. |
| `audio/recordings/352096__deleted_user_3667256__students-in-university-by-sielxm3d.mp3` | Student Conversation | Freesound 352096; CC0 observed; uploader account deleted/anonymized. | ____________________ | Review provenance; confirm class and quality, including noted MPEG decoder warnings. Unsupported MP3; no conversion before clearance. |
| `audio/recordings/425671__bparker4336__lecture.mp3` | Teacher Discussion | Freesound 425671; CC0 observed. | ____________________ | Verify exact asset and CC0 applicability; confirm label and investigate noted MPEG warnings. Unsupported MP3. |
| `audio/recordings/449511__12572598__theatre-class-lecture.mp3` | Teacher Discussion (unverified; mixed speech risk) | Freesound 449511; CC0 observed; source description includes teacher speaking to students. | ____________________ | Determine whether teacher speech is clearly primary or clip is mixed/ambiguous; investigate MPEG warnings. Unsupported MP3. Exclude duplicate `(1)` copy. |
| `audio/recordings/455052__maqsood5mail2worldcom__a-languge-teacher-can-make-a-lot-for-the-human.mp3` | Teacher Discussion (unverified) | No matching exact source page/license located in project notes. | ____________________ | Establish exact source/license; otherwise keep excluded. Confirm class and investigate MPEG warnings. Unsupported MP3. |
| `audio/recordings/504669__bpayri__group-of-students-talking-loud-in-classroom-valencian-and-spanish.aiff` | Student Conversation (unverified) | Freesound 504669; CC BY 4.0 observed; source notes indistinct chatter/laughter and some saturation. | ____________________ | Verify exact asset and attribution conditions; confirm class/ambiguity and assess saturation. Unsupported AIFF. |
| `audio/recordings/650855__noiseful_joy__the-murmur-of-students-inside-a-lecture-hall-in-aix-en-provence.wav` | Student Conversation proposed; actual outcome unresolved | Freesound 650855; CC BY 4.0 observed; described as student murmur before a lecture. | ____________________ | Decide whether clear student-to-student conversation is primary. If only background murmur or unclear, mark ambiguous/exclude. Verify attribution and project-use applicability. |
| `audio/recordings/696685__sgtdukenberry__calm-teacher.wav` | Teacher Discussion; user-reported listening decision, formal record pending | Freesound 696685; CC0 observed. | ____________________ | Verify exact asset and CC0 applicability; formalize the reported label decision. |

## Additional files requiring content triage before shortlist selection

These entries in `experimental_candidate_mapping.csv` have no reliable two-class label from the filename. The mapping does not supply exact source/license references for them. First establish whether the audio plausibly contains a target class, then complete the same source, license, approval, annotation, privacy/rights, and quality checks above. “Potential label” below is only a listening prompt, not a label assignment.

| Candidate filename | Pipeline intake | Listening prompt / reviewer decision |
|---|---|---|
| `121258__ondrosik__students-beginning-of-lesson.wav` | PCM WAV accepted | Determine whether student-to-student conversation is primary, or whether it is another activity. ____________________ |
| `13226__incarnadine__living-minute-classroom-before-the-teacher-arrives.mp3` | MP3 unsupported | Determine whether target speech exists; investigate decoder warnings. ____________________ |
| `232436__zachrau__school-kids-repeating-words.wav` | PCM WAV accepted | Determine whether this is student conversation or prompted/repeated speech outside the label rule. ____________________ |
| `237525__joangilbardaji__vn-frances-toni.wav` | PCM WAV accepted | Identify audible activity; filename gives no reliable target class. ____________________ |
| `240821__casaasiasons__leer-un-poema-chino_yishizhang.wav` | PCM WAV accepted | Determine whether clear teacher-led instruction or student conversation is primary. ____________________ |
| `274794__klankbeeld__marine-life-education-nl-150524_05.wav` | PCM WAV accepted | Determine whether target speech exists and which role is primary. ____________________ |
| `328622__bpayri__crowd-chattering-students-university-loud.aiff` | AIFF unsupported | Determine whether voices constitute student conversation; do not infer class from title. ____________________ |
| `337237__artesmediales__roldan_rios_voces-y-silencios_paisaje_escolar.wav` | WAV PCM accepted | Determine whether target speech is clear and classifiable. ____________________ |
| `402303__jsoza__loyola-field-recording.wav` | PCM WAV accepted | Identify audible activity; filename gives no reliable target class. ____________________ |
| `439500__belfernando610__armando.mp3` | MP3 unsupported | Identify audible activity; investigate decoder warnings. ____________________ |
| `450445__kyles__crowd-int-high-school-hallway-light-activity-while-students-in-class-french-and-english-teachers-nice-wood-door-knock-open-close-middle.flac` | FLAC unsupported | Title suggests hallway/mixed events; determine whether target speech is primary. ____________________ |
| `455780__kyles__high-school-hallway-lockers-students-movement-between-periods-gets-busier-and-loud-montreal-canada.flac` | FLAC unsupported | Determine whether target conversation is present rather than movement/ambience. ____________________ |
| `464326__deleted_user_9772077__are615_7_1_chaiken_suzanne.mp3` | MP3 unsupported | Establish provenance and audible activity; investigate decoder warnings. ____________________ |
| `520478__saaxeemq__danzon_class.flac` | FLAC unsupported | Determine whether target speech exists. ____________________ |
| `593015__2100385_joshua_blignaut__soft-room-tone-of-a-student-library-some-people-moving.wav` | PCM WAV accepted | Determine whether target speech exists; room tone/movement alone is not a target class. ____________________ |
| `648664__elenalostale__school-classroom-ambience.wav` | PCM WAV accepted | Determine whether classifiable teacher or student speech is present. ____________________ |
| `65536__sonsdebarcelona__sonsericlaia2.mp3` | MP3 unsupported | Identify audible activity; investigate decoder warnings. ____________________ |
| `679130__qleq__school-class-sounds.m4a` | M4A unsupported; stream details unavailable | Establish source and format, then determine whether target speech exists. ____________________ |
| `736924__robo9418__100-students-cheering.wav` | PCM WAV accepted | Determine whether there is student conversation; cheering alone does not establish that label. ____________________ |
| `766495__thikhomunyai__ambience-school-_students-in-a-workspace_thikho_owsfx.wav` | PCM WAV accepted | Determine whether intelligible target speech is present. ____________________ |
| `847680__finnaem__faculdade-de-architecture.m4a` | M4A unsupported; stream details unavailable | Establish source and format, then determine whether target speech exists. ____________________ |
| `869642__paisagemsonoraunila__student-strike.wav` | PCM WAV accepted | Determine whether target conversation is primary; filename alone is insufficient. ____________________ |
| `869656__hawa9874__classroom-ambience-environment-in-nepal-school-environment.wav` | PCM WAV accepted | Determine whether classifiable target speech is present. ____________________ |

## Record only after actual review

For each selected file, complete the following in its approved record, then transfer only truthful statuses and non-identifying references to the metadata:

- Reviewer identity and actual review date/time.
- Criteria/version used; use the project class definitions above and note whether the whole asset or specific intervals were reviewed.
- Exactly one content outcome: `Teacher Discussion`, `Student Conversation`, `Mixed/ambiguous`, or `Exclude`; non-identifying notes and time intervals where needed.
- Source identity and exact license evidence; project lead’s use decision and attribution/condition requirements.
- Privacy review and participant-rights/consent applicability decision, with evidence references where applicable.
- Separate technical audio-quality outcome and real review reference.

For eligible metadata, use the exact clip schema in `ml/data_pipeline.py`: `clip_id`, `relative_path`, `label`, `original_recording_id`, `source_id`, `source_type`, `source_reference`, `license_id`, `license_reference`, `approval_status`, `approval_reference`, `consent_ref`, `privacy_review_ref`, `annotation_status`, `annotation_review_ref`. The validator requires `approval_status=approved`, `annotation_status=reviewed`, real source/license/approval/annotation references, and `privacy_review_ref` for training. For `source_type=public`, the validator does not conditionally require `consent_ref`; the human review must still decide whether participant rights or consent obligations apply. The baseline training guard requires privacy reference. The experimental fitter requires both exact classes and at least two distinct reviewed `(source_id, original_recording_id)` groups per class.

## Restricted storage and approvals

The collection documentation describes a planned restricted Google Drive folder but explicitly requires the team to confirm the account, folder approval, access controls, sharing settings, retention, backup, and deletion arrangements. The repository does not establish an approved location or give a record-creation procedure for these public-candidate reviews. The project lead must confirm the approved location and record format before reviewers store completed records. Do not use this worksheet, a filename, or a guessed opaque string as a review reference.

## Current disposition

- No candidate is fully cleared by repository evidence alone.
- Candidate mapping entries for 188214, 155599, and 696685 contain user-reported listening decisions; formal annotation records/references remain pending.
- 650855 remains unresolved; do not assign `Student Conversation` unless listening confirms clear student-to-student conversation is primary.
- The duplicate files `335031__heraclitopd__students-chatting-amb (1).wav` and `449511__12572598__theatre-class-lecture (1).mp3` are excluded from selection.
- Source/license, project approval, privacy, participant-rights/consent applicability, and quality reviews remain outstanding for all selected assets.
