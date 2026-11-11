# Two-Class ML and Warning Policy (Provisional)

## Confirmed model outputs

The classifier has exactly two output classes:

- `Teacher Discussion`
- `Student Conversation`

Unclear or mixed audio may be held for annotation review. It is not a third
model class, and it should not be forced into training labels until the team
agrees on a consistent labeling rule. The model must not identify individual
students.

## Warning rule

The buzzer must not trigger merely because students are speaking. The
provisional software rule in `ml/warning_policy.py` returns a warning decision
only when all of these are true for an input window:

1. The model classification is `Student Conversation` and the caller explicitly
   marks that classification as confident under a team-approved confidence
   rule.
2. A sound-level reading is present and declared calibrated.
3. The team has explicitly configured a finite sound-level threshold.
4. The reading strictly exceeds that threshold.

Teacher Discussion, unknown classifications, unavailable or uncalibrated sound
levels, and missing or invalid thresholds fail closed and do not request a
warning. Non-numeric values and non-boolean confidence/calibration flags also
fail closed. This is a software policy helper only; it does not read a
microphone, calibrate hardware, set confidence or sound thresholds, or drive a
buzzer.

The confidence rule, sound threshold, and calibration procedure remain team
decisions. Values in the unit tests are controlled software fixtures only,
not recommended or validated classroom limits. This first helper evaluates
one window; duration, hysteresis, cooldown, and reset behavior remain to be
agreed before physical warning integration.

## Data suitability and labeling

The existing `DATASET_SOURCES.md` is a broader research draft and contains
older multi-class assessments. For this two-class task, the source must provide
usable evidence of teacher-led classroom discussion or student-to-student
conversation; generic speech labels do not identify those roles.

### Smallest source shortlist after source and terms review

No source in the current research is both a strong match for both target
classes and fully cleared for this project's intended use. The smallest
conditional shortlist is:

| Source | Class fit | Terms/access review | Decision |
|---|---|---|---|
| [TalkBank ClassBank](https://talkbank.org/class/) | Best setting match: it contains filmed classroom interactions. A specific corpus must include usable audio and examples of both teacher-led and student-to-student interaction. | TalkBank's [default rules](https://talkbank.org/0share/rules.html) say CC BY-NC-SA 3.0 unless otherwise indicated, require following its ethics rules, and restrict web processing without non-retention assurance. The existing research notes a different license badge on the ClassBank page and corpus-specific media/download restrictions. | **Conditional candidate only.** Resolve the selected corpus's actual license, access, audio availability, model-training use, and local-handling requirements with TalkBank/course staff before use. The previously reviewed APT corpus says not to download its videos, so exclude APT. |
| [AMI Meeting Corpus](https://groups.inf.ed.ac.uk/ami/corpus/license.shtml) | Adult multi-party meetings can provide a conversation-acoustics proxy, but do not label teacher versus student and are not classroom interaction. | The official AMI license page states CC BY 4.0 for the corpus and annotations. Attribution is required when material is shared. | **Not suitable as labeled data for either target role.** Do not map adult meeting participants to teacher/student classes. It may be deferred as a non-classroom acoustic experiment only if that experiment is useful and separately documented. |
| [FSD50K](https://zenodo.org/records/4060432) | General sound-event labels include speech/conversation-related classes, but do not establish teacher-led discussion or student-to-student conversation. | Zenodo says each clip has its own uploader-selected CC license; metadata maps clip IDs to licenses. The collection also has a CC BY dataset-level license, while its record cautions that a single global license is not straightforward. | **Not suitable as core supervised data for these role classes.** Do not infer student/teacher roles from child/adult voice or generic speech labels. Reconsider only a manually reviewed subset with per-clip rights cleared for the intended use. |

TalkBank describes ClassBank as filmed classroom interactions spanning several
education levels ([ClassBank overview](https://talkbank.org/class/)). Its
default terms and processing restrictions are directly relevant; the specific
corpus terms still govern the decision. AMI's license is clearer, but its
adult meeting content does not support the target role labels. FSD50K's
per-clip licensing is explicit, but its sound-event labels do not provide the
required roles. These sources are therefore not interchangeable.

The practical minimum for a defensible two-class model is likely to include
approved, purpose-recorded classroom examples for both labels. Recording stays
blocked until permissions and participant consent are addressed. Without such
data, a pipeline can be prepared and exercised with software fixtures, but no
classroom classifier should be claimed ready.

Proposed annotation handling for team review:

- Label a clear teacher-led instructional exchange as `Teacher Discussion`.
- Label clear student-to-student conversation as `Student Conversation`.
- Mark overlapping, mixed, or unclear windows for review rather than forcing a
  label. The team must decide how to handle them consistently.
- Do not infer a warning from the class label alone; warning also requires a
  valid calibrated level and an agreed threshold.

Any classroom recording remains blocked until permission, participant
consent, storage/access, retention, and deletion requirements are addressed.
Do not put private audio or restricted datasets in Git or upload them to
third-party AI services without explicit authorization.

## Evaluation when authorized data is available

Use recording/session-grouped splits to reduce leakage. Report class counts,
per-class precision, recall, and F1-score, a confusion matrix, and macro-F1.
Record false predictions and source limitations. Public or proxy-data results
must not be described as validated classroom performance.

The dependency-free metrics helper is in `ml/evaluation.py`. It accepts actual
and predicted labels, rejects labels outside the exact two-class scope, and
returns per-class precision, recall, F1, support, a confusion matrix, accuracy,
and macro-F1. It does not train a model or read audio.

The preparation-only dataset validator, explicit WAV preprocessing settings,
reproducible source-recording-group split helper, architecture-neutral
training/evaluation interface, and provisional inference adapter are documented
in [`ML_PIPELINE.md`](ML_PIPELINE.md). They do not select or train a model and
do not authorize data use. The trainer is a plug-in interface; the inference
adapter leaves `confident=false` unless a team-approved confidence rule is
supplied by its caller.

## Current software check

Run the standard-library tests from the repository root with:

```powershell
python -m unittest discover -s ml/tests -v
```

These tests exercise only software rules and metrics with controlled fixtures.
They do not validate a trained model, a sound-level sensor, a calibrated
threshold, or physical buzzer behavior.
