"""Train a separate local-only demo from existing mapped classroom audio.

This path is deliberately isolated from the approved-data readiness runner.
It writes PCM WAV working copies and an explicit source/label-status manifest,
does not edit source metadata or approvals, and produces no evaluation metrics.
The artifact is for a local school demonstration only, not production use.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import warnings
from typing import Any

import joblib
import soundfile as sf

from ml.baseline import LogisticRegressionConfig, LogisticRegressionTrainer
from ml.data_pipeline import PreprocessingConfig, preprocess_wav, validate_audio_file
from ml.evaluation import CLASSES
from ml.features import MFCCConfig, MFCCFeatureExtractor, extract_feature_vector
from ml.run_baseline import _load_config
from ml.training import FeatureExample


_SCHOOL_LABELS = {
    "StudentConversation.wav": "Student Conversation",
    "StudentConversation2.wav": "Student Conversation",
    "Teacher-Discussion.wav": "Teacher Discussion",
    "Teacher-Discussion2.wav": "Teacher Discussion",
}

# Include the reported listening decisions plus only source-described examples
# that can be represented honestly as provisional. These assignments are not
# formal annotation approvals; pending rights/review state is retained below.
_PUBLIC_CANDIDATES = {
    "115386__adamlhumphreys__groupofcollegestudentsinclassroom.wav": {
        "label": "Student Conversation",
        "label_confidence": "provisional_medium",
        "label_reason": "Source title identifies a group of college students in a classroom; local content was not reported as listened to.",
        "source_reference": "https://freesound.org/people/adamlhumphreys/sounds/115386/",
        "license_id": "CC BY-NC 4.0",
        "license_note": "Attribution and noncommercial use are required; the project applicability review remains pending.",
        "source_id": "filename-asset:115386",
        "review_basis": "source-title-only provisional label",
    },
    "155599__claudiooliveira2__students-talking.wav": {
        "label": "Student Conversation",
        "label_confidence": "user_listening_reported",
        "label_reason": "User reports listening to the recording and verifying Student Conversation; formal review record remains pending.",
        "source_reference": "https://freesound.org/people/claudiooliveira2/sounds/155599/",
        "license_id": "CC0",
        "license_note": "CC0 observed in the project source-page notes; project, participant-rights, and privacy reviews remain pending.",
        "source_id": "filename-asset:155599",
        "review_basis": "user-reported listening decision; no review reference supplied",
    },
    "188214__splicesound__science-teacher-lecturing.wav": {
        "label": "Teacher Discussion",
        "label_confidence": "user_listening_reported",
        "label_reason": "User reports listening to the recording and verifying Teacher Discussion; formal review record remains pending.",
        "source_reference": "https://freesound.org/people/SpliceSound/sounds/188214/",
        "license_id": "CC0",
        "license_note": "CC0 observed in the project source-page notes; project and privacy reviews remain pending.",
        "source_id": "filename-asset:188214",
        "review_basis": "user-reported listening decision; no review reference supplied",
    },
    "352096__deleted_user_3667256__students-in-university-by-sielxm3d.mp3": {
        "label": "Student Conversation",
        "label_confidence": "provisional_medium",
        "label_reason": "The preparation guide says the source page describes university students with speech/conversations; uploader account is deleted and local listening/quality review is pending.",
        "source_reference": "https://freesound.org/people/deleted_user_3667256/sounds/352096/",
        "license_id": "CC0",
        "license_note": "CC0 observed in the project guide; provenance and project-use review remain pending. Inventory notes MPEG decoder warnings.",
        "source_id": "filename-asset:352096",
        "review_basis": "source-description-only provisional label",
    },
    "425671__bparker4336__lecture.mp3": {
        "label": "Teacher Discussion",
        "label_confidence": "provisional_low",
        "label_reason": "The candidate mapping and source-page notes identify a lecture, but the exact classroom activity and label have not been confirmed by listening.",
        "source_reference": "https://freesound.org/people/bparker4336/sounds/425671/",
        "license_id": "CC0",
        "license_note": "CC0 observed in the project source-page notes; project-use, participant-rights, and privacy reviews remain pending. Inventory notes MPEG decoder warnings.",
        "source_id": "filename-asset:425671",
        "review_basis": "source-title-only provisional label",
    },
    "449511__12572598__theatre-class-lecture.mp3": {
        "label": "Teacher Discussion",
        "label_confidence": "provisional_low",
        "label_reason": "The preparation guide says the source describes a theatre teacher speaking to students; mixed teacher/student speech is a documented risk and dominance is unconfirmed.",
        "source_reference": "https://freesound.org/people/12572598/sounds/449511/",
        "license_id": "CC0",
        "license_note": "CC0 observed in project notes; project, participant-rights, and privacy reviews remain pending. Inventory notes MPEG decoder warnings.",
        "source_id": "filename-asset:449511",
        "review_basis": "source-description-only provisional label; mixed-speech risk",
    },
    "504669__bpayri__group-of-students-talking-loud-in-classroom-valencian-and-spanish.aiff": {
        "label": "Student Conversation",
        "label_confidence": "provisional_low",
        "label_reason": "The preparation guide describes student voices, indistinct chatter, and laughter; clear conversation is not confirmed and saturation is noted.",
        "source_reference": "https://freesound.org/people/bpayri/sounds/504669/",
        "license_id": "CC BY 4.0",
        "license_note": "Attribution is required; project applicability and audio-quality reviews remain pending, including the documented saturation concern.",
        "source_id": "filename-asset:504669",
        "review_basis": "source-description-only provisional label; indistinct chatter/saturation",
    },
    "696685__sgtdukenberry__calm-teacher.wav": {
        "label": "Teacher Discussion",
        "label_confidence": "user_listening_reported",
        "label_reason": "User reports listening to the recording and verifying Teacher Discussion; formal review record remains pending.",
        "source_reference": "https://freesound.org/people/Sgt.Dukenberry/sounds/696685/",
        "license_id": "CC0",
        "license_note": "The preparation guide records the source page and CC0 as verified; the selected-file mapping lacks these references and project/privacy reviews remain pending.",
        "source_id": "filename-asset:696685",
        "review_basis": "user-reported listening decision; no review reference supplied",
    },
}

_EXCLUSION_NOTES = {
    "121258__ondrosik__students-beginning-of-lesson.wav": "No reliable target-class label in the supplied mapping; filename alone is insufficient.",
    "13226__incarnadine__living-minute-classroom-before-the-teacher-arrives.mp3": "Class activity is not established by the available metadata; filename alone is insufficient.",
    "23202__lg__lecture09.wav": "Proposed Teacher Discussion conflicts with the source note describing classroom background/student chatter; license unresolved and current WAV validator rejects IMA ADPCM.",
    "232436__zachrau__school-kids-repeating-words.wav": "Repeating words is not established as either target activity; no confirmed label.",
    "233453__dmadridp__teacher-speech.wav": "Source notes place speech in a corridor during class; target classroom discussion is not established and label is unconfirmed.",
    "237525__joangilbardaji__vn-frances-toni.wav": "No reliable target-class label in the supplied mapping.",
    "240821__casaasiasons__leer-un-poema-chino_yishizhang.wav": "Reading a poem is not established as either target activity; no confirmed label.",
    "256189__cyweb__students-lunchtime.wav": "Asset-specific license could not be verified; label remains unconfirmed.",
    "274794__klankbeeld__marine-life-education-nl-150524_05.wav": "Educational audio is not enough to establish a target class.",
    "328622__bpayri__crowd-chattering-students-university-loud.aiff": "No source-reviewed target-class label; filename alone is insufficient.",
    "335031__heraclitopd__students-chatting-amb.wav": "Exact source/license is unresolved and no human label review is recorded.",
    "337237__artesmediales__roldan_rios_voces-y-silencios_paisaje_escolar.wav": "School soundscape is not enough to establish a target class.",
    "402303__jsoza__loyola-field-recording.wav": "No reliable target-class label in the supplied mapping.",
    "439500__belfernando610__armando.mp3": "No reliable target-class label in the supplied mapping.",
    "450445__kyles__crowd-int-high-school-hallway-light-activity-while-students-in-class-french-and-english-teachers-nice-wood-door-knock-open-close-middle.flac": "Hallway recording with multiple events; neither target class is established.",
    "455052__maqsood5mail2worldcom__a-languge-teacher-can-make-a-lot-for-the-human.mp3": "No exact source/license record was located; do not infer from title or similar uploads.",
    "455780__kyles__high-school-hallway-lockers-students-movement-between-periods-gets-busier-and-loud-montreal-canada.flac": "Hallway movement is not one of the target classes.",
    "464326__deleted_user_9772077__are615_7_1_chaiken_suzanne.mp3": "No reliable target-class label or provenance in the supplied mapping.",
    "520478__saaxeemq__danzon_class.flac": "Music/dance-class label does not establish either target class.",
    "593015__2100385_joshua_blignaut__soft-room-tone-of-a-student-library-some-people-moving.wav": "Library room tone is not established as either target class.",
    "648664__elenalostale__school-classroom-ambience.wav": "Classroom ambience alone does not establish teacher discussion or student conversation.",
    "650855__noiseful_joy__the-murmur-of-students-inside-a-lecture-hall-in-aix-en-provence.wav": "Source notes describe background murmur before a lecture; conversation is not established, so the proposed class is not forced.",
    "335031__heraclitopd__students-chatting-amb (1).wav": "Byte-identical duplicate of 335031__heraclitopd__students-chatting-amb.wav; the underlying asset is excluded because exact source/license evidence and human label review are missing.",
    "449511__12572598__theatre-class-lecture (1).mp3": "Byte-identical duplicate of the selected 449511 recording; it is not counted as an independent sample.",
    "65536__sonsdebarcelona__sonsericlaia2.mp3": "No reliable target-class label in the supplied mapping.",
    "679130__qleq__school-class-sounds.m4a": "No target label in the mapping and installed decoder cannot read this M4A.",
    "736924__robo9418__100-students-cheering.wav": "Cheering is not Student Conversation.",
    "766495__thikhomunyai__ambience-school-_students-in-a-workspace_thikho_owsfx.wav": "Workspace ambience alone does not establish either target class.",
    "847680__finnaem__faculdade-de-architecture.m4a": "No target label in the mapping and installed decoder cannot read this M4A.",
    "869642__paisagemsonoraunila__student-strike.wav": "A student strike is not established as either target class.",
    "869656__hawa9874__classroom-ambience-environment-in-nepal-school-environment.wav": "Classroom ambience alone does not establish either target class.",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _classroom_rows(path: Path) -> dict[str, dict[str, str]]:
    import csv

    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return {row["clip_id"]: row for row in csv.DictReader(stream)}


def _to_working_wav(source: Path, destination: Path) -> tuple[dict[str, Any], list[str]]:
    """Decode any installed SoundFile-supported source to a generated PCM16 WAV."""
    import numpy as np

    captured: list[str] = []
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        samples, sample_rate = sf.read(source, dtype="float32", always_2d=True)
        captured.extend(str(item.message) for item in caught)
    if samples.ndim != 2 or samples.shape[0] <= 0 or samples.shape[1] <= 0:
        raise ValueError("decoder returned an empty or malformed waveform")
    if not np.isfinite(samples).all():
        raise ValueError("decoder returned non-finite sample values")
    destination.parent.mkdir(parents=True, exist_ok=True)
    sf.write(destination, samples, sample_rate, format="WAV", subtype="PCM_16")
    info = validate_audio_file(destination)
    return {
        "decoder": "soundfile/libsndfile",
        "decoded_sample_rate_hz": int(sample_rate),
        "decoded_channels": int(samples.shape[1]),
        "decoded_frame_count": int(samples.shape[0]),
        "decoded_subtype": sf.info(source).subtype,
        "working_copy_encoding": "PCM_16 WAV; original rate/channels retained",
        "working_copy_audio": asdict(info),
    }, captured


def run_demo(
    *, config_path: str | Path, dataset_directory: str | Path,
    artifact_directory: str | Path, acknowledge_demo_only_unreviewed_data: bool,
) -> dict[str, Any]:
    if acknowledge_demo_only_unreviewed_data is not True:
        raise ValueError("explicit acknowledgement of demo-only use with pending reviews is required")
    project_root = Path(__file__).resolve().parents[1]
    source_root = (project_root / "ml/data/classroom_collection/audio/recordings").resolve()
    classroom_metadata = project_root / "ml/data/metadata/classroom_metadata.csv"
    dataset_root = Path(dataset_directory).resolve()
    artifact_root = Path(artifact_directory).resolve()
    for target in (dataset_root, artifact_root):
        if target.exists():
            raise FileExistsError(f"refusing to overwrite existing output: {target}")
    if dataset_root == artifact_root or dataset_root in artifact_root.parents or artifact_root in dataset_root.parents:
        raise ValueError("demo dataset and model artifact directories must be separate")
    if not source_root.is_dir() or not classroom_metadata.is_file():
        raise FileNotFoundError("existing classroom recordings and metadata are required")

    config_file, config = _load_config(config_path)
    preprocessing = PreprocessingConfig(**config["preprocessing"])
    feature_config = MFCCConfig(**config["feature_extractor"]["config"])
    if config["feature_extractor"].get("name") != "librosa-mfcc-mean-std":
        raise ValueError("demo config must use the existing librosa-mfcc-mean-std extractor")
    extractor = MFCCFeatureExtractor(feature_config)
    logistic_config = LogisticRegressionConfig(**config.get("logistic_regression", {}))
    school_rows = _classroom_rows(classroom_metadata)

    choices: dict[str, dict[str, Any]] = {}
    for name, label in _SCHOOL_LABELS.items():
        row = school_rows.get(name)
        if row is None or row["label"] != label:
            raise ValueError(f"existing classroom metadata does not support the stated label for {name}")
        choices[name] = {
            "label": label,
            "label_confidence": "user_supplied_existing_school_label",
            "label_reason": "Existing classroom metadata matches the explicit user-supplied label; formal annotation status remains pending.",
            "source_id": row["source_id"],
            "source_reference": row.get("source_reference", ""),
            "license_id": row.get("license_id", ""),
            "license_note": "School permission was reported by the user; documentary/reference fields are blank in existing metadata.",
            "review_basis": "existing classroom metadata and user-supplied class mapping",
        }
    choices.update(_PUBLIC_CANDIDATES)

    before_audio = sorted(
        path for path in (project_root / "ml/data").rglob("*")
        if path.is_file() and path.suffix.lower() in {".wav", ".mp3", ".flac", ".aiff", ".m4a"}
    )
    working_audio_root = dataset_root / "audio/recordings"
    dataset_root.mkdir(parents=True)
    records: list[dict[str, Any]] = []
    examples: list[FeatureExample] = []
    excluded: list[dict[str, str]] = []
    selected_originals: set[Path] = set()
    source_hashes: dict[str, str] = {}

    for ordinal, (name, choice) in enumerate(choices.items(), start=1):
        source = (source_root / name).resolve()
        if source_root not in source.parents or not source.is_file():
            excluded.append({"file": f"ml/data/classroom_collection/audio/recordings/{name}", "reason": "selected source file is missing or outside the known recording folder"})
            continue
        clip_id = Path(name).stem
        source_digest = _sha256(source)
        if source_digest in source_hashes:
            excluded.append({"file": f"ml/data/classroom_collection/audio/recordings/{name}", "reason": f"byte-identical duplicate of selected source {source_hashes[source_digest]}"})
            continue
        working_name = f"{ordinal:02d}_{clip_id}.wav"
        working_path = working_audio_root / working_name
        try:
            decode_info, decode_warnings = _to_working_wav(source, working_path)
            processed = preprocess_wav(working_path, preprocessing)
            features = extract_feature_vector(extractor, processed)
        except Exception as error:
            excluded.append({"file": f"ml/data/classroom_collection/audio/recordings/{name}", "reason": f"decoder/pipeline failed: {type(error).__name__}: {error}"})
            continue

        selected_originals.add(source)
        source_hashes[source_digest] = name
        original_recording_id = name if name in _SCHOOL_LABELS else name
        group_id = json.dumps((choice["source_id"], original_recording_id), separators=(",", ":"))
        examples.append(FeatureExample(clip_id, group_id, choice["label"], features))
        record = {
            "clip_id": clip_id,
            "source_file": f"ml/data/classroom_collection/audio/recordings/{name}",
            "source_sha256": source_digest,
            "working_copy": f"ml/data/expanded_local_demo_20261020/audio/recordings/{working_name}",
            "working_copy_sha256": _sha256(working_path),
            "assigned_label": choice["label"],
            "label_confidence_or_basis": choice["label_confidence"],
            "label_reason": choice["label_reason"],
            "review_basis": choice["review_basis"],
            "source_id": choice["source_id"],
            "source_reference_observed": choice.get("source_reference", ""),
            "license_id_observed": choice.get("license_id", ""),
            "license_conditions_or_notes": choice.get("license_note", ""),
            "existing_formal_review_state": (
                {key: school_rows[name].get(key, "") for key in (
                    "approval_status", "approval_reference", "consent_ref", "privacy_review_ref",
                    "annotation_status", "annotation_review_ref",
                )} if name in school_rows else {
                    "source_approval_status": "pending",
                    "consent_status": "unverified",
                    "privacy_review_status": "pending",
                    "annotation_status": "pending_formal_review_record",
                    "quality_review_status": "pending",
                }
            ),
            "audio_decode": decode_info,
            "decoder_warnings": decode_warnings,
            "technical_quality_review": "not performed; numeric decode checks are not a human quality review",
            "permission_status": "no new approval asserted; this remains a local demo-only fit",
        }
        records.append(record)

    counts = {label: sum(example.label == label for example in examples) for label in CLASSES}
    if not examples or any(counts[label] == 0 for label in CLASSES):
        raise ValueError(f"demo fit requires at least one decoded sample from each class; got {counts}")

    selected_names = {Path(item["source_file"]).name for item in records}
    for path in before_audio:
        if path in selected_originals:
            continue
        rel = path.relative_to(project_root).as_posix()
        if path.name in selected_names and "experimental_demo" in path.parts:
            reason = "byte-identical/demo copy is not counted as an independent recording"
        elif path.name in _EXCLUSION_NOTES:
            reason = _EXCLUSION_NOTES[path.name]
        else:
            reason = "existing inventory has no supportable mapping to either target class"
        excluded.append({"file": rel, "reason": reason})
    excluded.sort(key=lambda item: item["file"].casefold())

    class_groups = {
        label: len({example.group_id for example in examples if example.label == label})
        for label in CLASSES
    }
    manifest = {
        "manifest_version": 1,
        "dataset_mode": "local_only_expanded_school_demo_unreviewed",
        "source_scope": "existing recordings under ml/data; no downloads",
        "classes": list(CLASSES),
        "training_recording_count": len(records),
        "class_counts": counts,
        "independent_source_groups_per_class": class_groups,
        "formal_readiness": "not_passed; existing statuses and normal readiness gate were not changed or bypassed",
        "evaluation": None,
        "metrics": None,
        "preprocessing": asdict(preprocessing),
        "feature_extractor": extractor.metadata(),
        "audio_working_copy_method": "soundfile/libsndfile decode; generated PCM16 WAV copies at original sample rate/channel count; existing preprocessing then performs configured mono mix, center crop, and linear resample in memory",
        "training_samples": records,
        "excluded_audio_files": excluded,
        "limitations": [
            "No held-out evaluation was performed; all listed examples are fitted.",
            "Provisional source-description labels are weak labels, not human annotations.",
            "Listening decisions and label records reported by the user have no formal review reference in project metadata.",
            "Source-use approval, participant-rights/consent applicability, privacy, and human audio-quality reviews remain pending where recorded as such.",
            "The model is local demo-only and is not validated or production-ready.",
        ],
    }
    manifest_text = _canonical(manifest) + "\n"
    manifest_digest = hashlib.sha256(manifest_text.encode("utf-8")).hexdigest()
    (dataset_root / "demo_dataset_manifest.json").write_text(manifest_text, encoding="utf-8", newline="\n")

    classifier = LogisticRegressionTrainer(logistic_config).fit(
        examples, (), seed=int(config["split"]["seed"])
    )
    run_metadata = {
        "run_metadata_version": 1,
        "run_mode": "local_only_expanded_demo_unreviewed",
        "training_mode": "experimental_full_fit_no_held_out_evaluation",
        "training_clip_count": len(examples),
        "class_counts": counts,
        "independent_groups_per_class": class_groups,
        "dataset_formal_readiness": "not_passed; see demo_dataset_manifest.json",
        "held_out_evaluation": None,
        "metrics": None,
        "preprocessing": asdict(preprocessing),
        "feature_extractor": extractor.metadata(),
        "logistic_config": asdict(logistic_config),
        "dataset_manifest_sha256": manifest_digest,
        "source_config": str(config_file),
        "warning_policy_changed": False,
    }
    artifact_root.mkdir(parents=True, exist_ok=False)
    joblib.dump({
        "model": classifier.estimator,
        "classifier": classifier,
        "classes": list(CLASSES),
        "training_mode": "experimental_full_fit_no_held_out_evaluation",
        "logistic_config": asdict(logistic_config),
        "preprocessing": asdict(preprocessing),
        "feature_extractor": extractor.metadata(),
        "manifest_sha256": manifest_digest,
        "local_demo_status": "unreviewed_nonproduction_demo",
    }, artifact_root / "experimental_model.joblib")
    (artifact_root / "run_metadata.json").write_text(_canonical(run_metadata) + "\n", encoding="utf-8", newline="\n")
    (artifact_root / "demo_dataset_manifest.json").write_text(manifest_text, encoding="utf-8", newline="\n")
    return {
        "dataset_directory": str(dataset_root),
        "artifact_path": str(artifact_root / "experimental_model.joblib"),
        "class_counts": counts,
        "training_recordings": records,
        "excluded_audio_files": excluded,
        "held_out_evaluation": None,
        "metrics": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="ml/config/experimental-demo.json")
    parser.add_argument("--dataset-directory", default="ml/data/expanded_local_demo_20261020")
    parser.add_argument("--artifact-directory", default="ml/artifacts/expanded-local-demo-20261020")
    parser.add_argument("--acknowledge-demo-only-unreviewed-data", action="store_true", required=True)
    args = parser.parse_args()
    try:
        result = run_demo(
            config_path=args.config,
            dataset_directory=args.dataset_directory,
            artifact_directory=args.artifact_directory,
            acknowledge_demo_only_unreviewed_data=args.acknowledge_demo_only_unreviewed_data,
        )
    except (OSError, ValueError, RuntimeError, TypeError, KeyError) as error:
        print(f"expanded local demo refused/failed: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
