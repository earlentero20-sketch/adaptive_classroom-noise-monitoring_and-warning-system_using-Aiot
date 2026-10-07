# Public Dataset Sources: Research and Shortlist

**Owner:** Earl Entero (ML / Data Engineer)
**Phase:** 2 — Dataset Collection and Labeling (research and planning only)
**Status:** Draft for review. **No dataset, audio, or metadata file has been downloaded.**

## How to read this document

Every statement is tagged by type so facts are not confused with plans or assumptions:

- **DIRECT** = the page or document was opened and read during this research pass (section 2 lists them).
- **NOT DIRECTLY VERIFIED** = seen only as a search-result excerpt, or described by a mirror, catalog, paper, or message instead of a page that was opened. This is reference information. It must be confirmed at the source before it is relied on.
- **ASSESSMENT** = the ML role's judgment (for example the "Fit" and "Limitations" lines). Not a verified fact.
- **INFERENCE** = reasoning that no source confirms.
- **UNRESOLVED** = a license, access, or factual question that is still open.
- **RECOMMENDATION** = a proposal by the ML role. Not a decision.
- **TBD (team)** = belongs to other team members. The ML role does not decide it.
- **TBD (Earl)** = an ML-role decision or fact not yet known.

Research dates from October 2026. Licenses and terms can change, so re-check each source before any download. Nothing here is legal advice.

---

## 1. Summary

### Five-class assessment (ASSESSMENT)

| Class | Assessment |
|---|---|
| Teacher Speech | Possible public sources, but weak classroom/domain match |
| Student Conversation | **Insufficient public data** |
| Group Discussion | Partially covered |
| Excessive Noise | **Insufficient public data** |
| Background Noise | Best covered |

No dataset is forced into a class it does not fit. Where a dataset only loosely matches, this document says so.

### Cross-cutting limitations

1. No candidate is real classroom audio recorded with the project's final microphone (ASSESSMENT). Microphone specification: **TBD (team)**. Results on public data may not transfer cleanly to a classroom.
2. Public clips are not level-calibrated (ASSESSMENT), so the "clearly elevated level" part of the Excessive Noise definition may not be learnable from them. The dB threshold is **TBD (team)**.
3. Several datasets carry non-commercial or ShareAlike terms (section 5). **The project is intended for academic use. Whether a given license applies to this project's use should still be confirmed against course and institution requirements.**
4. Clip lengths differ widely (see profiles), which will need decisions in Phase 3.

---

## 2. Verification basis for this research pass

**Opened and read directly (DIRECT):**
- ESC-50 README (raw text from the dataset's GitHub repository)
- FSD50K Zenodo record (https://zenodo.org/records/4060432)
- FSD50K paper (https://arxiv.org/abs/2010.00475, PDF opened)
- Salamon, Jacoby, Bello, "A Dataset and Taxonomy for Urban Sound Research" (ACM MM 2014, PDF opened)
- DEMAND Zenodo record (https://zenodo.org/records/1227121). The attached `DEMAND.pdf` could not be read (binary).
- TalkBank ClassBank pages: main page, data access levels page, corpora index, Curtis corpus page, APT corpus page, and the TalkBank Ground Rules page

**Not opened. Information below about these comes from search-result excerpts or secondary sources and is NOT DIRECTLY VERIFIED:**
- UrbanSound8K's official dataset page, and its mirrors and catalogs (Kaggle, Hugging Face, DagsHub, audEERING, soundata)
- Google's AudioSet pages
- OpenSLR pages for LibriSpeech and MUSAN
- The Mozilla Common Voice datasheet
- The AMI corpus homepage, rooms page, and papers that use AMI
- The MyST LDC catalog page and papers that use MyST
- The DEMAND author's 2013 mailing-list message and papers about DEMAND
- Papers describing SimClass, RealClass, and NCTE
- A paper describing a filtered ClassBank subset
- The ClassBank corpus pages other than Curtis and APT

The FSD50K companion site was opened but is dynamic and gave no vocabulary list.

---

## 3. Dataset profiles

### ESC-50
- **DIRECT (README):** 2,000 recordings, 5 s each, 50 classes with 40 per class, WAV 44.1 kHz mono, manually extracted from Freesound field recordings. License CC BY-NC (version 3.0 link); the ESC-10 subset is CC BY. Predefined 5 folds keep fragments of one Freesound clip together. Download is a single zip of about 600 MB. The README warns of possible leakage because some source recordings were already processed (mostly band-limited) in a class-dependent way.
- **DIRECT (FSD50K paper, comparison table):** about 2.8 h in total.
- **ASSESSMENT, fit:** Background Noise only (selected indoor non-speech classes such as vacuum cleaner, keyboard typing, clock tick, washing machine). No speech or shouting classes.
- **ASSESSMENT, limitations:** many clips are single events (for example a door knock), not steady ambience. 40 clips per class is small.

### UrbanSound8K — **secondary / unresolved** (official page not opened)
- **DIRECT (original paper):** 8,732 slices (8.75 h) in 10 urban classes, capped at 1,000 slices per class. Slices of up to 4 s are cut from 1,302 Freesound recordings (about 27 h) with a 2 s hop, so neighboring slices overlap. Folds were built so slices from one recording stay in the same fold. Each occurrence has a foreground/background salience label. In the authors' baseline, air conditioners were mostly confused with idling engines, and children playing with street music.
- **NOT DIRECTLY VERIFIED (license):** the dataset README text, as reproduced by a mirror, says non-commercial CC BY-NC 3.0. The Kaggle copy and a Hugging Face mirror list CC BY-NC 4.0. **UNRESOLVED:** the version must be confirmed from the dataset's own page or README.
- **NOT DIRECTLY VERIFIED (sample rate):** mirrors say files keep the original Freesound format and may vary. One catalog lists 8 kHz to 192 kHz and 1–2 channels; one paper reports 16–48 kHz. **UNRESOLVED:** must be measured in Phase 3.
- **UNRESOLVED (per-class counts):** exact counts for air_conditioner and children_playing are only in a figure and in `UrbanSound8K.csv`, which is inside the archive (about 6 GB, size not directly verified).
- **ASSESSMENT, fit:** Background Noise (air_conditioner); only weakly Excessive Noise (children_playing, outdoor).
- **ASSESSMENT, limitations:** urban outdoor audio, variable sample rate, overlapping slices.

### FSD50K
- **DIRECT:** 51,197 Freesound clips, 108.3 h, 200 classes drawn from the AudioSet Ontology. 16-bit 44.1 kHz mono WAV, 0.3–30 s, clip-level (weak) labels. Dev and eval sets share no uploaders.
- **DIRECT (licenses):** each clip has its own license: CC0 19,873, CC-BY 23,506, CC-BY-NC 6,041, CC Sampling+ 1,777 (summed from the dev and eval counts). The dataset as a whole is CC-BY, but the authors note a single license for the whole is not straightforward. Commercial use requires contacting the authors. Per-clip licenses are in the metadata files.
- **DIRECT (vocabulary, paper Figure 7):** relevant classes present include Speech, Male speech, Female speech, Child speech, Conversation, Chatter, Whispering, Shout, Yell, Screaming, Crowd, Cheering, Applause, Clapping, Laughter, Human group actions, Mechanical fan, Hiss. No class for silence, air conditioning, or children shouting appears in the list.
- **DIRECT (quality):** the authors estimate FSD50K is cleaner than AudioSet (mean SNR about 26 dB versus 14 dB, measured with a speech-oriented tool, so only a rough indication). Some Freesound clips are studio or foley recordings or staged sounds. Human sounds are often unlabeled in dev clips when they are not the dominant event, so labels may be incomplete.
- **DIRECT (size):** audio is distributed only as split zip files (about 18 GB dev plus 6 GB eval, 24.7 GB in total). A subset of clips cannot be fetched separately. The ground-truth and metadata zips are small (0.33 MB and 6.7 MB).
- **UNRESOLVED:** per-class clip counts and per-clip licenses for the relevant classes (in the small ground-truth and metadata files, not downloaded).
- **ASSESSMENT, fit:** Excessive Noise (Shout, Yell, Screaming, Cheering, Crowd); Group Discussion weakly (Chatter and Crowd are babble, not discussion); Teacher Speech (adult speech clips); Background Noise (Mechanical fan, Hiss); Student Conversation only through Conversation and Child speech clips (counts unknown).
- **ASSESSMENT, limitations:** weak labels, cleaner than classrooms, all-or-nothing download.

### AudioSet — not used for audio
- **DIRECT (FSD50K paper):** about 2.1 million clips, about 5,731 h, 527 classes. The official release provides precomputed audio features, not waveforms, under CC-BY-4.0. The audio comes from YouTube videos that are not freely distributable, and videos gradually disappear.
- **NOT DIRECTLY VERIFIED (search excerpts of Google's pages):** the ontology license (CC BY-SA 4.0), and label counts for Children shouting (673), Chatter (1,952), and Child speech (11,816).
- **RECOMMENDATION:** do not scrape YouTube audio. The label license does not clearly cover the underlying audio, and the FSD50K paper itself describes usage-rights problems. Use AudioSet only as a reference vocabulary.

### LibriSpeech — **NOT DIRECTLY VERIFIED** (OpenSLR page not opened)
- **From search excerpt:** about 1,000 h of 16 kHz read English audiobook speech, CC BY 4.0; dev-clean subset about 337 MB. **UNRESOLVED:** confirm at OpenSLR.
- **ASSESSMENT, fit:** Teacher Speech as a "single adult voice" proxy only.
- **ASSESSMENT, limitations:** studio-clean read speech, no classroom acoustics, cannot tell teacher from non-teacher.

### MUSAN — **NOT DIRECTLY VERIFIED** (OpenSLR page not opened)
- **From search excerpts:** about 109 h, 16 kHz WAV, license listed as CC BY 4.0, content described as public domain or Creative Commons. Noise part 929 files (about 6 h), speech part about 60 h (LibriVox and US government recordings), archive about 11 GB. **UNRESOLVED:** confirm at OpenSLR.
- **ASSESSMENT, fit:** weak Background Noise only. The speech part likely duplicates LibriSpeech.
- **ASSESSMENT, limitations:** an assorted, non-classroom noise set.

### Common Voice — **NOT DIRECTLY VERIFIED** (datasheet not opened)
- **From search excerpt:** CC0, read sentences from single speakers, with rules against identifying speakers and against re-hosting. **UNRESOLVED:** confirm in the current datasheet; clip durations not checked.
- **ASSESSMENT, fit:** weak. Not instructional or conversational speech. At best adds speaker variety to synthetic mixes.

### AMI Meeting Corpus — **NOT DIRECTLY VERIFIED** (AMI pages not opened)
- **From search excerpts:** 100 h of meetings, signals and transcripts under CC BY 4.0, recorded in three rooms with close-talking and far-field microphones. Most meetings have four participants, some three or five. About 20% of speech overlaps (from papers using AMI). The Edinburgh room is described as capturing at 48 kHz, 16-bit; commonly used prepared versions are 16 kHz. **UNRESOLVED:** license, sample rate, and participant counts to be confirmed on the AMI site.
- **ASSESSMENT, fit:** Group Discussion, the strongest public acoustic match found (multi-party turn-taking and overlap).
- **ASSESSMENT, limitations:** adults in meeting rooms, reportedly mostly non-native English, long recordings to cut and hand-label. Headset mix versus far-field microphone is a Phase 3 choice.

### MyST Children's Conversational Speech — **NOT DIRECTLY VERIFIED** (LDC page and paper not opened)
- **From search excerpts:** children in grades 3–5 (1,371 students) talking with a virtual science tutor, single channel 16 kHz. About 470 h per the LDC excerpt and about 400 h per a paper excerpt (the figure differs by source). Free non-commercial version under CC BY-NC-SA 4.0; commercial licensing separate. **UNRESOLVED:** confirm license and access at the source.
- **ASSESSMENT, fit:** child voices only. **Not Student Conversation:** each session is one child and a software tutor, not students talking to each other. Possible ingredient for synthetic mixes.
- **ASSESSMENT, limitations:** NC-SA terms, minors' voice data.

### ClassBank / TalkBank
- **DIRECT (access):** open to all with free registration (email and password), for transcripts and media.
- **DIRECT (media):** the two corpora checked are video only. Curtis is a second-grade geometry classroom (a 1992–1995 project); much of its untranscribed material is children's small-group work. APT's page states its videos should not be downloaded or reposted, which rules it out. APT file names tag whole-class versus small-group sessions. The corpora index lists about 23 corpora; only these two were opened.
- **DIRECT (rules):** the Ground Rules say CC BY-NC-SA 3.0 unless otherwise indicated, no commercial use, no uploading TalkBank data to web-based systems unless they guarantee they will not keep it (ChatGPT and OpenAI are named), and that commercial enterprises cannot include the data in models.
- **UNRESOLVED:** the ClassBank page shows a CC BY-NC-SA 4.0 badge while the Ground Rules text says 3.0. Whether a student-trained classifier counts as "including the data" is unclear; confirm with TalkBank or your instructor. Each other corpus page must be read for media type and download restrictions. Audio quality of older video is unknown.
- **NOT DIRECTLY VERIFIED:** one research team's filtered ClassBank subset of 44 h (322 files), seen only as a paper excerpt. That is their subset, not the whole corpus.
- **ASSESSMENT, fit:** the only real-classroom source found. Could give Teacher Speech, Student Conversation, Group Discussion, and some Excessive Noise segments, if a corpus passes the checks.
- **ASSESSMENT, limitations:** no sound-class labels (hand labeling by listening), video-to-audio extraction needed, mixed settings (the index also lists museum lessons, tutoring, and medical-school sessions).

### DEMAND
- **DIRECT (Zenodo record):** 16-channel noise recordings. The file list shows 18 environments: DKITCHEN, DLIVING, DWASHING, NFIELD, NPARK, NRIVER, OHALLWAY, OMEETING, OOFFICE, PCAFETER, PRESTO, PSTATION, SCAFE, SPSQUARE, STRAFFIC, TBUS, TCAR, TMETRO. Each environment is 16 single-channel WAVs at 16 kHz and 48 kHz (SCAFE only at 48 kHz). 16 kHz zips are about 78–130 MB each.
- **DIRECT (license conflict):** the record's description says CC BY-SA 3.0, while its rights field says CC BY 4.0. The description's "15 recordings" is out of date (18 environments are listed). Per-recording duration is not stated on the page.
- **NOT DIRECTLY VERIFIED:** an author's 2013 mailing-list message (seen as an excerpt) says 18 environments under Attribution-ShareAlike. **UNRESOLVED:** which license applies. Working assumption (RECOMMENDATION): treat as CC BY-SA until clarified.
- **ASSESSMENT, fit (based on environment names only, contents not listened to):** Background Noise from quieter indoor environments such as office, hallway, meeting room, living room, kitchen.
- **INFERENCE:** café and restaurant recordings likely contain speech, so they would need listening and probably exclusion.
- **ASSESSMENT, limitations:** only 18 environments, so it cannot reach 20 independent sources alone. The 16 channels of one recording are not independent, so each environment would be one `original_recording_id`. Mono handling is a Phase 3 choice.

### Considered, not shortlisted — **NOT DIRECTLY VERIFIED**
- **SimClass / RealClass:** described in paper excerpts as synthetic classroom sets built from a children's speech corpus plus lecture speech and synthesized babble. License not verified. **INFERENCE:** it likely inherits restrictions from its source corpora.
- **NCTE:** described in a paper excerpt as 2,128 elementary math classroom recordings (12.8 h of speech). Access terms not verified.

---

## 4. Verification log

| Item | Result | Basis | Status |
|---|---|---|---|
| FSD50K vocabulary | Full 200-class list read; relevant classes in section 3 | DIRECT (paper) | Resolved |
| FSD50K counts and licenses per class | In small metadata files, not downloaded | — | Open |
| UrbanSound8K license | Non-commercial; 3.0 versus 4.0 wording conflict | Mirrors and catalogs | Unresolved |
| UrbanSound8K sample rate | Varies per file per mirrors; documented ranges disagree | Mirrors and papers | Unresolved |
| UrbanSound8K class counts | Capped at 1,000 per class; exact counts need the CSV | DIRECT (paper) for the cap | Open |
| DEMAND license / version | 18 environments listed; BY-SA versus BY 4.0 conflict in the record | DIRECT (Zenodo) | Conflict unresolved |
| AMI sample rate | Edinburgh room 48 kHz; common versions 16 kHz | Search excerpts only | Not directly verified |
| ClassBank access | Free registration | DIRECT | Resolved |
| ClassBank audio availability | Two corpora checked, both video; APT forbids download | DIRECT (two pages) | Partly resolved |

---

## 5. Unresolved license and access issues

1. UrbanSound8K license version (3.0 versus 4.0) and sample rate.
2. DEMAND license (BY-SA 3.0 versus BY 4.0 in the same Zenodo record).
3. ClassBank license version (3.0 versus 4.0) and whether a trained model counts as including the data.
4. ClassBank per-corpus media type and download restrictions, for the corpora not yet opened.
5. Licenses and terms for LibriSpeech, MUSAN, Common Voice, AMI, MyST, and AudioSet come from search excerpts and must be confirmed at the source before any download.
6. FSD50K per-clip licenses: clips under non-commercial terms need a decision on whether they may be used.
7. ShareAlike datasets (DEMAND, MyST, ClassBank) may require sharing derived datasets under the same terms.
8. **License applicability:** the project is intended for academic use, but whether each license applies to this project's use should be confirmed against course and institution requirements.

---

## 6. Recommended dataset strategy (RECOMMENDATION, not a decision)

**Teacher Speech.** Use LibriSpeech and FSD50K adult speech clips for training and validation, labeled as a voice-type proxy. Add ClassBank segments only if a corpus passes the media, license, and handling checks. Real teacher speech, with consent, is needed for testing. Risk: the model learns clean read speech instead of classroom speech.

**Student Conversation.** No strong public source. Options, in order: (1) team or approved recordings, the most credible but consent-dependent; (2) FSD50K Conversation and Child speech clips after checking counts and speaker mix; (3) clearly labeled synthetic mixes of one or two child voices. Treat this class as needing team-collected data. Do not claim it is covered.

**Group Discussion.** AMI for training and validation, if its terms are confirmed (headset mix versus far-field is a Phase 3 choice). FSD50K Chatter and Crowd may supplement it, with the babble-versus-discussion caveat. Student groups are not covered, so real recordings are needed.

**Excessive Noise.** FSD50K Shout, Yell, Screaming, Cheering, and Crowd, with UrbanSound8K children_playing as a weak supplement. Labels follow the character of the sound because public clips are not level-calibrated. Real classroom recordings are needed.

**Background Noise.** DEMAND quieter indoor environments (after listening), selected ESC-50 and UrbanSound8K clips, and FSD50K Mechanical fan and Hiss. Listen to every clip to confirm it is speech-free. Keep keyboard typing as an edge case. Record real quiet-classroom room tone for testing.

---

## 7. Training/validation versus real-classroom testing

- Public datasets are for **training, validation, and development comparison.** They do not automatically become the final real-classroom test set.
- A held-out public split measures performance on public data, mixed with the effect of our own mapping of public classes onto the five classes. That mapping is an assumption.
- The **final test set should be real or approved classroom audio** (Phase 11), collected under the consent rules and never used for tuning.
- Splits stay grouped by `original_recording_id`. ESC-50 and UrbanSound8K folds group by source recording (ESC-50 DIRECT from the README, UrbanSound8K DIRECT from the paper); FSD50K's provided split is by uploader.
- If classroom consent is not obtained, public-only results must be reported as development results with the domain gap stated. They must not be presented as classroom performance.

---

## 8. Data directory convention

| Folder | Purpose | In Git? |
|---|---|---|
| `ml/data/external/` | Downloaded third-party datasets **and third-party metadata** (for example a dataset's own CSV or ground-truth files) | **No.** Must stay out of Git. |
| `ml/data/metadata/` | **Our own** project metadata CSV files (clip IDs, class, source type, `original_recording_id`, `consent_ref`, and so on) | Yes, only when the file contains no private audio and no personal information. |
| `ml/data/<class>/` | Local audio organized by class | No (audio is ignored). Only `.gitkeep` placeholders. |

Notes:
- `ml/.gitignore` ignores everything under `ml/data/` except `.gitkeep` files and `ml/data/metadata/*.csv`.
- The ignore rule cannot inspect a CSV's contents. Checking that a metadata CSV has no personal information (no names, no consent documents, only a consent reference) is a manual step before committing.
- `ml/.gitignore` is scoped to `ml/` only. Audio committed outside `ml/` is not covered. Whether a root-level `.gitignore` is also needed is **TBD (team)**.

---

## 9. Guardrails

- **ClassBank:** its Ground Rules prohibit uploading the data to web-based systems unless they guarantee non-retention. That guarantee cannot be given for AI chat tools, so ClassBank audio must **not** be uploaded to Claude, ChatGPT, or any other AI tool. Labeling must be done by listening locally.
- **Synthetic data:** an option only, not a decision. Every synthetic clip would be labeled `synthetic`. It must not be presented as real classroom data, and it may introduce mixing artifacts that the model learns instead of real classroom sound.
- **Privacy and consent:** school or consent approval for classroom recordings remains **TBD (Earl)**. No private audio in Git.

---

## 10. TBD decisions

| Decision | Owner |
|---|---|
| Where ML inference runs | **TBD (team)** |
| What the device sends (raw audio, clips, or features) | **TBD (team)** |
| Microphone model, sample rate, gain | **TBD (team)** |
| dB threshold for Excessive Noise and the baseline | **TBD (team)** |
| Final output format and field names | **TBD (team)** |
| Whether the repository also needs a root-level `.gitignore` (affects other members' folders) | **TBD (team)** |
| School/consent approval for classroom recordings | **TBD (Earl)** |
| License applicability to this academic project, confirmed against course and institution requirements | **TBD (Earl)** |
| Whether to seek ClassBank access, and which corpora | **TBD (Earl)** |
| Whether and how to use synthetic mixing | **TBD (Earl)** |
| Final dataset size | Depends on available, approved data |

---

## 11. Next steps (each needs separate approval; none started)

1. Confirm licenses and terms at the source pages for the datasets listed as not directly verified.
2. Metadata-only downloads to close open items: FSD50K ground-truth and metadata zips (about 7 MB) and UrbanSound8K's CSV.
3. Read the remaining ClassBank corpus pages for media type and restrictions.
4. Decide on classroom consent and which sources to download, with exact subsets and sizes.
