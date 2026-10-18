"""Fit a local-only, explicitly unreviewed demo from the four SONIQ recordings.

This opt-in path does not alter or bypass the approved-data validator or the
normal experimental runner. It copies the existing recordings and metadata
unchanged, validates PCM WAV structure, and records the unresolved review state
in the local dataset and artifact manifests. It produces no evaluation metrics.
"""

import argparse
import csv
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import shutil
import sys
from typing import Any

import joblib

from ml.baseline import LogisticRegressionConfig, LogisticRegressionTrainer
from ml.data_pipeline import (
    PreprocessingConfig,
    group_id,
    preprocess_wav,
    validate_audio_file,
)
from ml.evaluation import CLASSES
from ml.features import MFCCConfig, MFCCFeatureExtractor, extract_feature_vector
from ml.run_baseline import _load_config
from ml.training import FeatureExample


DEMO_LABELS = {
    "StudentConversation.wav": "Student Conversation",
    "StudentConversation2.wav": "Student Conversation",
    "Teacher-Discussion.wav": "Teacher Discussion",
    "Teacher-Discussion2.wav": "Teacher Discussion",
}


def run_local_demo(
    *,
    config_path: str | Path,
    artifact_directory: str | Path,
    acknowledge_local_only_unreviewed_demo: bool,
) -> dict[str, Any]:
    if acknowledge_local_only_unreviewed_demo is not True:
        raise ValueError("explicit acknowledgement of local-only, unreviewed demo fitting is required")

    config_path = Path(config_path).resolve()
    project_root = Path(__file__).resolve().parents[1]
    original_root = (project_root / "ml/data/classroom_collection").resolve()
    metadata_source = (project_root / "ml/data/metadata/classroom_metadata.csv").resolve()
    log_source = (project_root / "ml/data/metadata/classroom_recording_log.csv").resolve()
    dataset_root = (project_root / "ml/data/experimental_demo").resolve()
    artifact_root = Path(artifact_directory).resolve()
    if dataset_root.exists():
        raise FileExistsError(f"local demo dataset already exists; refusing to overwrite: {dataset_root}")
    if artifact_root.exists():
        raise FileExistsError(f"local demo artifact directory already exists; refusing to overwrite: {artifact_root}")
    if dataset_root == artifact_root or dataset_root in artifact_root.parents or artifact_root in dataset_root.parents:
        raise ValueError("dataset and artifact directories must be separate")
    if not metadata_source.is_file() or not log_source.is_file():
        raise ValueError("existing classroom metadata and recording log are required")

    _, config = _load_config(config_path)
    metadata_rows = _read_csv(metadata_source)
    log_rows = _read_csv(log_source)
    if {row["clip_id"] for row in metadata_rows} != set(DEMO_LABELS):
        raise ValueError("classroom metadata must contain exactly the four specified demo recordings")
    if {row["label"] for row in metadata_rows} != set(CLASSES):
        raise ValueError("metadata labels must be exactly Teacher Discussion and Student Conversation")
    rows_by_clip = {row["clip_id"]: row for row in metadata_rows}
    logs_by_recording = {row["original_recording_id"]: row for row in log_rows}

    # Validate all sources before creating the separate copy-only demo dataset.
    source_info = {}
    for filename, expected_label in DEMO_LABELS.items():
        row = rows_by_clip[filename]
        if row["label"] != expected_label:
            raise ValueError(f"existing metadata label for {filename} does not match the supplied class mapping")
        source_path = (original_root / row["relative_path"]).resolve()
        if original_root not in source_path.parents or not source_path.is_file():
            raise ValueError(f"recording is missing or resolves outside the classroom collection: {filename}")
        source_info[filename] = validate_audio_file(source_path)
        if filename not in logs_by_recording:
            raise ValueError(f"recording log has no matching entry for {filename}")

    # Copy only. Existing metadata and log are byte-for-byte copies; no review
    # status, evidence reference, or source file is changed.
    audio_root = dataset_root / "audio/recordings"
    metadata_root = dataset_root / "metadata"
    audio_root.mkdir(parents=True)
    metadata_root.mkdir(parents=True)
    for filename in DEMO_LABELS:
        shutil.copy2(original_root / rows_by_clip[filename]["relative_path"], audio_root / filename)
        copied_info = validate_audio_file(audio_root / filename)
        if copied_info != source_info[filename]:
            raise ValueError(f"copy validation differs from source for {filename}")
    shutil.copy2(metadata_source, metadata_root / "classroom_metadata.csv")
    shutil.copy2(log_source, metadata_root / "classroom_recording_log.csv")

    preprocessing = PreprocessingConfig(**config["preprocessing"])
    feature_config = MFCCConfig(**config["feature_extractor"]["config"])
    if config["feature_extractor"].get("name") != "librosa-mfcc-mean-std":
        raise ValueError("experimental config must select librosa-mfcc-mean-std")
    extractor = MFCCFeatureExtractor(feature_config)
    examples = []
    manifest_rows = []
    for filename in DEMO_LABELS:
        row = rows_by_clip[filename]
        audio_path = audio_root / filename
        digest = _sha256_file(audio_path)
        features = extract_feature_vector(extractor, preprocess_wav(audio_path, preprocessing))
        examples.append(FeatureExample(
            row["clip_id"], group_id_from_row(row), row["label"], features
        ))
        log = logs_by_recording[row["original_recording_id"]]
        manifest_rows.append({
            "clip_id": row["clip_id"],
            "relative_path": f"audio/recordings/{filename}",
            "label": row["label"],
            "label_basis": "existing classroom metadata, matching the explicit user-supplied mapping",
            "group_id": group_id_from_row(row),
            "sha256": digest,
            "audio": asdict(source_info[filename]),
            "existing_review_state": {
                key: row[key] for key in (
                    "approval_status", "approval_reference", "consent_ref", "privacy_review_ref",
                    "annotation_status", "annotation_review_ref",
                )
            },
            "recording_log_review_state": {
                key: log[key] for key in (
                    "quality_review_status", "quality_review_ref",
                    "annotation_status", "annotation_review_ref",
                )
            },
        })

    groups_per_class = {
        label: len({item.group_id for item in examples if item.label == label})
        for label in CLASSES
    }
    if any(groups_per_class[label] < 2 for label in CLASSES):
        raise ValueError("local demo requires at least two distinct recording groups per class")

    demo_manifest = {
        "run_mode": "local_only_unreviewed_demo",
        "formal_dataset_readiness": "not_passed; existing review statuses and empty references are preserved",
        "permission_basis": "user states school permission; no documentary reference is present in project metadata",
        "formal_annotation_status": "pending; labels are not represented as formal annotation approval",
        "held_out_evaluation": None,
        "metrics": None,
        "classes": list(CLASSES),
        "samples": manifest_rows,
    }
    manifest_bytes = _canonical_json(demo_manifest).encode("utf-8")
    manifest_digest = hashlib.sha256(manifest_bytes).hexdigest()
    (dataset_root / "local_demo_manifest.json").write_bytes(manifest_bytes + b"\n")

    classifier = LogisticRegressionTrainer(
        LogisticRegressionConfig(**config.get("logistic_regression", {}))
    ).fit(examples, (), seed=config["split"]["seed"])
    run_metadata = {
        "run_metadata_version": 1,
        "run_mode": "local_only_unreviewed_demo",
        "training_mode": "experimental_full_fit_no_held_out_evaluation",
        "training_clip_count": len(examples),
        "class_counts": {label: sum(item.label == label for item in examples) for label in CLASSES},
        "independent_groups_per_class": groups_per_class,
        "dataset_review_status": "not_formally_cleared",
        "held_out_evaluation": None,
        "metrics": None,
        "preprocessing": asdict(preprocessing),
        "feature_extractor": extractor.metadata(),
        "logistic_config": asdict(LogisticRegressionConfig(**config.get("logistic_regression", {}))),
        "dataset_manifest_sha256": manifest_digest,
        "code_revision": None,
        "warning_policy_changed": False,
    }
    artifact_root.mkdir(parents=True)
    joblib.dump({
        "model": classifier.estimator,
        "classifier": classifier,
        "classes": list(CLASSES),
        "training_mode": "experimental_full_fit_no_held_out_evaluation",
        "logistic_config": run_metadata["logistic_config"],
        "preprocessing": asdict(preprocessing),
        "feature_extractor": extractor.metadata(),
        "manifest_sha256": manifest_digest,
        "local_demo_status": "unreviewed_nonproduction_demo",
    }, artifact_root / "experimental_model.joblib")
    (artifact_root / "run_metadata.json").write_text(
        _canonical_json(run_metadata) + "\n", encoding="utf-8", newline="\n"
    )
    return {
        "dataset_root": str(dataset_root),
        "artifact_path": str(artifact_root / "experimental_model.joblib"),
        "run_metadata": run_metadata,
        "held_out_evaluation": None,
        "metrics": None,
    }


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def group_id_from_row(row: dict[str, str]) -> str:
    return json.dumps((row["source_id"], row["original_recording_id"]), separators=(",", ":"))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="ml/config/experimental-demo.json")
    parser.add_argument("--artifact-directory", default="ml/artifacts/experimental-demo-local")
    parser.add_argument("--acknowledge-local-only-unreviewed-demo", action="store_true", required=True)
    args = parser.parse_args()
    try:
        result = run_local_demo(
            config_path=args.config,
            artifact_directory=args.artifact_directory,
            acknowledge_local_only_unreviewed_demo=args.acknowledge_local_only_unreviewed_demo,
        )
    except (KeyError, TypeError, ValueError, RuntimeError, OSError, AttributeError) as error:
        print(f"local experimental demo refused/failed: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
