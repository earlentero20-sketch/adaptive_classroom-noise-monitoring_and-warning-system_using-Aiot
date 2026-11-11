# Classroom Annotation Review Worksheet

**Purpose:** Record the human review of the four existing classroom recordings and any ambiguous intervals. This worksheet is a review record template; it is not evidence of consent, licensing, privacy approval, or technical quality approval.

## Review method and known facts

- Reviewers: Earl Entero (ML/Data Engineer) and Czell Gesite (Project Leader).
- The reviewers listened to the four recordings together and agreed that each intended class label listed below matched the content.
- This was a joint review. Whether either reviewer conducted an independent review has not been established; do not describe this review as independent.
- Review date/time: **not supplied; recover the actual date from the reviewers before marking the record complete**
- Review criteria or annotation guide version used: **[fill in, or state that none was recorded]**
- Opaque review-record reference: **not supplied; assign only after the actual review record is stored in the approved restricted location**

The reviewers' joint listening and label agreement are reported facts. The
date and secure review-record reference are still unknown; this worksheet is
not a substitute for that secured record and must not be used as a fabricated
opaque reference.

Do not put student names, participant identity keys, consent documents, or other identifying information in this worksheet or in the repository. Store the completed record in the approved restricted location. Use only a non-identifying opaque reference in the dataset metadata.

## Per-recording annotation decisions

The intended labels below are confirmed by the reported joint listening review. The target-class presence is therefore recorded as `yes`; other class presence and ambiguous-interval details were not provided and remain `unclear`. Use `yes`, `no`, or `unclear` for presence fields. Do not infer unknown details from filenames. This remains an incomplete review record until the date, secure reference, and unresolved interval fields are completed.

### 1. StudentConversation.wav

- Original recording ID: `StudentConversation.wav`
- Intended/agreed class: `Student Conversation`
- Teacher Discussion present: **unclear (not individually confirmed in the supplied review details)**
- Student Conversation present: **yes (jointly agreed intended label)**
- Ambiguous intervals present: **unclear (not supplied)**
- Ambiguous interval timestamps and decisions: **not supplied; do not assume none**
- Whole recording or particular intervals: **not supplied**
- Per-recording reviewer notes: **joint label agreement reported; review was not stated to be independent**

### 2. StudentConversation2.wav

- Original recording ID: `StudentConversation2.wav`
- Intended/agreed class: `Student Conversation`
- Teacher Discussion present: **unclear (not individually confirmed in the supplied review details)**
- Student Conversation present: **yes (jointly agreed intended label)**
- Ambiguous intervals present: **unclear (not supplied)**
- Ambiguous interval timestamps and decisions: **not supplied; do not assume none**
- Whole recording or particular intervals: **not supplied**
- Per-recording reviewer notes: **joint label agreement reported; review was not stated to be independent**

### 3. Teacher-Discussion.wav

- Original recording ID: `Teacher-Discussion.wav`
- Intended/agreed class: `Teacher Discussion`
- Teacher Discussion present: **yes (jointly agreed intended label)**
- Student Conversation present: **unclear (not individually confirmed in the supplied review details)**
- Ambiguous intervals present: **unclear (not supplied)**
- Ambiguous interval timestamps and decisions: **not supplied; do not assume none**
- Whole recording or particular intervals: **not supplied**
- Per-recording reviewer notes: **joint label agreement reported; review was not stated to be independent**

### 4. Teacher-Discussion2.wav

- Original recording ID: `Teacher-Discussion2.wav`
- Intended/agreed class: `Teacher Discussion`
- Teacher Discussion present: **yes (jointly agreed intended label)**
- Student Conversation present: **unclear (not individually confirmed in the supplied review details)**
- Ambiguous intervals present: **unclear (not supplied)**
- Ambiguous interval timestamps and decisions: **not supplied; do not assume none**
- Whole recording or particular intervals: **not supplied**
- Per-recording reviewer notes: **joint label agreement reported; review was not stated to be independent**

## Separate checks not established by this annotation review

Complete and document these through the appropriate project process. The reported joint label agreement does not establish any of them.

- Technical audio quality review for each recording and its actual review reference: **[complete separately]**
- Source and license evidence, where applicable: **[verify and document separately]**
- School permission: **reported as verbal; no documentary or other non-identifying reference was supplied**
- Participant consent/assent requirements and evidence, as applicable: **[verify separately; do not infer from school permission]**
- Privacy review and approved storage/access/retention arrangements: **[verify separately]**

## Mapping to dataset metadata

After this worksheet is completed and stored securely, the metadata CSV may reference it using the actual assigned opaque reference. Do not enter a placeholder word as a reference ID.

- In `classroom_metadata.csv`, update `annotation_status` and `annotation_review_ref` only according to the review outcome and the validator's accepted values. A review reference must identify the real stored review record.
- In `classroom_recording_log.csv`, update `teacher_discussion_present`, `student_conversation_present`, `ambiguous_intervals_present`, `annotation_status`, and `annotation_review_ref` from the completed per-recording decisions.
- Update `quality_review_status` and `quality_review_ref` only after a separate quality review has actually occurred.
- This worksheet does not change either CSV and does not by itself make the dataset approved or training-ready. Existing source, permission, consent, privacy, quality, and independent-recording split checks remain in force.
