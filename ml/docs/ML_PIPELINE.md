# Reusable ML Pipeline (Preparation Only)

This is a reusable software foundation, not a trained classifier. No real
classroom recordings or third-party datasets are included. Dataset rights,
intended-use approval, classroom permissions, participant consent, and privacy
review remain prerequisites; a metadata value of `approved` is a human
attestation and is not produced by this code.

For classroom recording, consent, labeling, storage, and deletion procedures,
see [CLASSROOM_AUDIO_COLLECTION.md](CLASSROOM_AUDIO_COLLECTION.md).

## Development environment

The inspected repository has no active virtual environment or Python
dependency manifest. The active interpreter is global Python 3.13.15. The
recommended isolated location is `ml/.venv`; `ml/.gitignore` already excludes
that path. It has not been created. After package-install approval, it can be
created with `python -m venv ml/.venv` and activated for the current shell.
NumPy, SciPy, librosa, scikit-learn, soundfile, PyTorch, and ONNX Runtime were
not available in the active interpreter during this check.

The extractor uses librosa MFCCs, and the classifier uses scikit-learn. The
current proposed direct pins for the active Python 3.13 environment are:

```text
numpy==2.4.4
scipy==1.17.0
librosa==1.0.0
scikit-learn==1.9.1
```

Python's standard-library `wave` module handles the validated PCM WAV input;
librosa's remaining requirements and scikit-learn's joblib dependency are
transitive. These versions are a proposal for later approval, not installed
packages or a lock file. The official librosa 1.0 requirements specify Python
3.12+, NumPy 2.1+, and SciPy 1.15+; its development instructions use Python
3.13. NumPy 2.4.4 and SciPy 1.17.0 document Python 3.13 support. Check the
selected Windows wheels and resolve/pin all transitive packages when install is
approved ([librosa requirements](https://librosa.org/blog/posts/1.0/),
[NumPy release notes](https://numpy.org/doc/stable/release/2.4.4-notes.html),
[SciPy release notes](https://docs.scipy.org/doc/scipy/release/1.17.0-notes.html),
[scikit-learn install guide](https://scikit-learn.org/stable/install)).

## Metadata and audio validation

`ml/data_pipeline.py` accepts a CSV with these required columns:

`clip_id,relative_path,label,original_recording_id,source_id,source_type,source_reference,license_id,license_reference,approval_status,approval_reference,consent_ref,privacy_review_ref,annotation_status,annotation_review_ref`

Labels must exactly match `Teacher Discussion` or `Student Conversation`.
`source_id` plus `original_recording_id` forms the split group identity, so
derived windows from one source recording remain together. IDs must be stable
and assigned by the dataset curator; every crop/augmentation from an original
must retain the same pair. `consent_ref` is a non-identifying internal
reference and is deliberately omitted from manifests. Never put participant
names or other identifying details in IDs or paths.

`source_reference` identifies the dataset/source record; `license_id` and
`license_reference` identify the applicable terms and human review record.
Unknown reference cells may be empty; do not enter `pending`, `unknown`, `TBD`,
or other placeholders as fake reference IDs. Empty values are accepted as
truthful intake metadata but produce blocking readiness issues when required.
`approval_status` is `approved`, `pending`, or `rejected`; approved records
require a real non-identifying `approval_reference`. Classroom records require
real `consent_ref` and `privacy_review_ref` values. School permission does not
replace participant consent/assent. `annotation_status` is `reviewed`,
`ambiguous`, `pending`, or `rejected`; only `reviewed` rows with a real
`annotation_review_ref` can be considered for training. Do not infer labels
from filenames. Keep annotation pending until a human reviews the audio.

For classroom sources, `recording_log.csv` must use the existing recording-log
template and have one matching `(source_id, original_recording_id)` row. The
original-level quality status must be `pass` with a real `quality_review_ref`,
and original-level annotation status must be `reviewed` with a real
`annotation_review_ref`. Clip and original-level reviews are both required.
These status/reference checks do not prove that licensing, permission,
consent, privacy, quality, or annotation review actually occurred. A
responsible human must verify the underlying records. Missing or pending
review information prevents the dataset check from passing.

Prepare `metadata.csv` inside the dataset root with these columns (in any
order):

```csv
clip_id,relative_path,label,original_recording_id,source_id,source_type,source_reference,license_id,license_reference,approval_status,approval_reference,consent_ref,privacy_review_ref,annotation_status,annotation_review_ref
<CLIP_ID>,<RELATIVE_PCM_WAV_PATH>,Teacher Discussion,<STABLE_RECORDING_ID>,<STABLE_SOURCE_ID>,classroom,,,,pending,,,,pending,
```

This is a format example only; replace every angle-bracket token with actual
metadata and keep unknown reference cells empty. Its blank references and
pending statuses are intentionally not ready for training. Set
`approval_status=approved` and `annotation_status=reviewed` only after humans
check the underlying permission, terms, consent, privacy review, and label.
Never mark status complete merely because a reference cell is populated. Assign
the same `source_id` and `original_recording_id` to every clip or derivative
from one original recording.

After replacing the placeholders in the JSON template and preparing reviewed
metadata, inspect split coverage before training:

```powershell
python -m ml.run_baseline --check-data ml/config/first-baseline.json
```

This check requires the data review gates to pass and reports each split's
clip count, per-class counts, distinct source-recording groups, and groups per
class. It does not import ML packages, train, or write artifacts. Proceed only
when `grouped_split_ready_for_baseline` is true; inspect class counts for
imbalance because the deterministic split is not stratified. Never change
source-group IDs to force a desired split.

Only rows with approved source review and completed annotation review are
opened and hashed. The report identifies missing metadata/audio, duplicate or
ambiguous IDs/paths, corrupt files, unsupported formats, unlisted audio,
missing references, incomplete classroom recording-log reviews, and sources
still awaiting review.
At present only uncompressed PCM WAV is decoded. Other common audio suffixes
are discovered and reported, not converted. WAV sample rate, duration, channel
count, and supported PCM width are read per file; uniform source properties are
not assumed.

Construct `PreprocessingConfig` explicitly for each run. It records target
sample rate and duration, channel mix (`mean` or `first`), resampling method
(currently linear), crop position (`start` or `center`), and normalization
(`none` or `peak`). Short windows are zero-padded; long windows are cropped.
These are software controls, not acoustically validated choices. In
particular, linear resampling is a simple dependency-free preparation method;
the eventual model owner should choose and document an appropriate
anti-aliasing resampler after the target environment is known.

`build_manifest` is stable and timestamp-free. It records file SHA-256,
metadata, audio properties, preprocessing, issues, and optional split
assignments without copying audio or consent references. Its
`ready_for_training` value remains false until valid assignments exist and
every split passes class and independent-group coverage checks. A successful
intake check alone is not a training-ready grouped evaluation. `write_manifest`
only writes when called explicitly by a user workflow.

## Grouped split policy

`split_by_source_group` deterministically hashes the seed and the canonical
`(source_id, original_recording_id)` pair into train, validation, and test
partitions. It never splits clips from one group. It requires at least three
independent groups and repairs an empty partition by moving a whole deterministic
group. `assert_no_group_leakage` checks complete assignments and catches any
group assigned to multiple partitions. `ml/training.py` repeats group checks
between train/validation and held-out test data.

`summarize_split_readiness` reports per-class clip counts and distinct groups
for each partition and flags partitions missing a class or having fewer than
two groups for a class. This is a minimum diagnostic only, not a sample-size
or statistical-power guarantee.

The hash split is reproducible but not stratified and can produce imbalanced
partitions, particularly with few groups. Before training, inspect class and
group counts for all partitions and revise the split design under review if a
partition lacks either class. Do not tune decisions against the held-out test
set.

## Training and inference boundaries

`Trainer` and `FittedClassifier` in `ml/training.py` define a small
architecture-neutral interface. `fit_model` validates labels, feature shapes,
finite values, and split separation, and passes a seed to the implementation.
`evaluate_held_out` calls the existing `ml/evaluation.py` helper and returns
per-class precision, recall, F1, confusion matrix, accuracy, and macro-F1.
No trainer, feature extractor, weights, or measured model result is included.

`ml/inference.py` adapts a future classifier to the provisional event
contract's exact `classification` fields: `label`, `confident`, and
timezone-aware `observed_at`. The prediction must be one of the two classes.
`confident` defaults to `false`; no numerical confidence or confidence cutoff
is invented. The team must approve the confidence rule before any integration
can set it true. Sound level, units, calibration, connection status, and warning
decisions remain separate fields owned by sensor/backend integration.

`ml/audio_inference.py` adds a transport-neutral host inference runtime for a
complete in-memory PCM WAV byte sample. It uses the preprocessing settings and
MFCC configuration serialized with a locally trained baseline artifact. The
runtime returns the two-class label and, when available, the predicted class
probability from `predict_proba`; that value is explicitly uncalibrated and is
not converted into the event contract's `confident` flag. The backend's
loopback-only `POST /api/v1/classify` route is a temporary local adapter for
this byte interface. It does not select a warning, process sound-level
readings, or establish an ESP32 audio transport.

`ml/features.py` implements a fixed-configuration librosa MFCC extractor. It
requires mono preprocessed input at the configured sample rate and returns
mean and standard deviation for each MFCC coefficient. Window length, hop,
FFT size, window function, mel count, frequency range, power, and aggregation
are recorded in `MFCCConfig`; channel mixing is recorded separately in
`PreprocessingConfig`. `ml/experiment.py` builds canonical JSON run metadata containing the
split method, seed and proportions, preprocessing configuration, extractor
name/version/configuration, dataset-manifest SHA-256, and code revision when
available. The caller supplies the revision (for example, from a read-only Git
query); `run_metadata_sha256` provides a stable hash of the run configuration.
This does not create model artifacts or train a model.

## Baseline recommendation and unresolved target

The host baseline is librosa MFCC mean/std features with a training-only
`StandardScaler` and regularized L2 logistic regression. It is compared with a
majority-class predictor derived from the training split only. A linear SVM is
not currently implemented. This is a fixed first experiment, not a production
architecture or performance claim. The active interpreter has none of the
required ML packages, and this phase does not install them.

The final inference target is unresolved. ESP32 inference may require a small
quantized model and a different frontend; a backend-hosted model has different
latency, network, and privacy constraints. The team must identify the ESP32
variant, RAM/flash budget, microphone and sample format, window/latency target,
and whether inference runs on-device or on the backend before selecting an
architecture or claiming deployability.

## Reproducible workflow after approvals

Create and activate the ignored project-local environment from the repository
root after installation approval:

```powershell
python -m venv ml/.venv
.\ml\.venv\Scripts\Activate.ps1
python -m pip install "numpy==2.4.4" "scipy==1.17.0" "librosa==1.0.0" "scikit-learn==1.9.1"
python -m pip check
python -m pip freeze | Set-Content -Encoding ascii ml/requirements-lock.txt
```

Do not run these commands until the team approves package installation and
reviews the resolved lock. The four pins constrain direct dependencies;
`pip freeze` records the resolved transitive versions for this environment.
Recreate an approved environment later with
`python -m pip install -r ml/requirements-lock.txt`. The file
`ml/config/first-baseline.example.json` is a template only. Copy it to
`ml/config/first-baseline.json`, replace all dataset and run-name placeholders,
and use human-verified references in the metadata CSV. The template does not
point to approved data.

The template includes all required fields and optional logistic-regression
settings. `metadata_csv` is relative to `dataset_root`; the dataset and
artifact paths are relative to the config file. Its MFCC and preprocessing
values are starting settings, not validated hardware or acoustic requirements.

With the template location, approved audio belongs under `ml/data/` and output
belongs under the ignored `ml/artifacts/`. Use a new artifact
directory for each run. Start only after all source and annotation reviews
pass:

```powershell
python -m ml.run_baseline ml/config/first-baseline.json
```

The runner refuses invalid, unapproved, ambiguous, synthetic, class-incomplete,
or group-incomplete datasets. It rechecks file hashes, verifies the grouped
split against the recorded seed/proportions, and writes the model, run
metadata, dataset manifest, and evaluation only after successful training on
approved non-synthetic audio. The evaluation JSON compares the logistic model
and majority reference. Its metrics are real only when generated by an
authorized run; never interpret software fixture results as model performance.

At present the four classroom recordings are not eligible for this run:
annotation and quality reviews are pending, required consent/review references
are not complete, and two original recordings per class cannot provide the
current independent train/validation/test group coverage. Do not change these
gates or use filename-derived labels. No model artifact or real evaluation is
currently available.

For a classroom presentation after every ordinary source, consent, privacy,
quality, and annotation gate passes, `ml.run_experimental` offers an explicitly
separate full-fit demonstration path. It reuses `validate_dataset()` and the
same approved-real-data checks, requires at least two independent reviewed
recordings for each class, and requires an explicit no-held-out-evaluation
acknowledgement. It fits every available reviewed clip and produces no
validation/test set, evaluation JSON, or performance metrics. Its model and
metadata are marked `experimental_full_fit_no_held_out_evaluation` and must
not be described as a reliable or evaluated classifier. It does not alter
the normal runner or its grouped split requirements. With the current pending
reviews it will refuse to run.

After the review gates pass and the local ML packages are approved and
available, an example command is:

```powershell
python -m ml.run_experimental ml/config/first-baseline.json `
  --artifact-directory ml/artifacts/experimental-four-recording-demo `
  --acknowledge-no-held-out-evaluation
```

The output directory must be new or empty. The command records `metrics: null`
and does not calculate or imply validation performance. The four recordings
must still receive human-reviewed class labels, quality review, and complete
source/consent/privacy documentation before the command can fit anything.

After an approved real run creates its artifact, a local backend can load it
without coupling the model to firmware details:

```powershell
$env:SONIQ_AUDIO_MODEL_PATH = "ml/artifacts/first-local-check/baseline.joblib"
python -m backend.app
```

For an approved experimental full-fit artifact, point at
`ml/artifacts/experimental-four-recording-demo/experimental_model.joblib`
instead. With the backend running, a complete local WAV file can be sent with:

```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/v1/classify" `
  -Method Post -ContentType "audio/wav" -InFile "<approved-short-wav-path>"
```

The placeholder must be replaced with a local WAV sample. The request remains
loopback-only and does not establish firmware compatibility. The endpoint
returns a class only from a loaded artifact; it returns `503 model_unavailable`
when no artifact can be loaded.

The local-only development adapter accepts one complete PCM WAV request at
`POST http://127.0.0.1:8000/api/v1/classify` with `Content-Type: audio/wav`.
It returns HTTP 503 with `model_unavailable` when no trusted artifact is
configured or available. A successful classification response does not run
warning policy and reports hardware as `not_tested`. The `predict_proba` value,
when present, is not a calibrated confidence and cannot itself activate the
buzzer. Raw microphone amplitude is not a calibrated dB SPL measurement.
If the artifact came from the experimental full-fit path, the response source
is `experimental_model` and its evaluation status is `not_evaluated`.

Run the software suites from the repository root with:

```powershell
python -B -m unittest discover -s ml/tests -v
python -B -m unittest discover -s backend/tests -v
node --test dashboard/backend-adapter.test.mjs
```

Temporary PCM WAV fixtures are created only inside test temporary directories;
feature tests use a generated in-memory tone. A small scikit-learn unit test,
when dependencies are installed, fits only controlled feature vectors to
check the scaler boundary. None of these are project audio, authorized data,
or model results.
