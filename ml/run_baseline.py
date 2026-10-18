"""Command-line runner for an explicitly configured approved-data baseline."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

from ml.baseline import LogisticRegressionConfig, run_baseline_experiment
from ml.data_pipeline import (
    PreprocessingConfig,
    split_by_source_group,
    summarize_split_readiness,
    validate_dataset,
)
from ml.features import MFCCConfig, MFCCFeatureExtractor


def run_config(config_path: str | Path) -> dict[str, Any]:
    path, config = _load_config(config_path)
    base = path.parent
    dataset_root = _resolve_path(base, config["dataset_root"])
    metadata_csv = config["metadata_csv"]
    artifact_directory = _resolve_path(base, config["artifact_directory"])
    if dataset_root == artifact_directory or dataset_root in artifact_directory.parents:
        raise ValueError("model artifacts must be outside the dataset directory")

    report = validate_dataset(dataset_root, metadata_csv)
    if not report.ready_for_training:
        problems = [f"{issue.code}" + (f" [clip_id={issue.clip_id}]" if issue.clip_id else "")
                    for issue in report.issues]
        raise ValueError("dataset is not ready for training: " + "; ".join(problems))
    split = config["split"]
    assignments = split_by_source_group(
        [sample.metadata for sample in report.samples],
        fractions=split["fractions"],
        seed=split["seed"],
    )
    preprocessing = PreprocessingConfig(**config["preprocessing"])
    feature_config = MFCCConfig(**config["feature_extractor"]["config"])
    if config["feature_extractor"].get("name") != "librosa-mfcc-mean-std":
        raise ValueError("feature_extractor.name must be 'librosa-mfcc-mean-std'")
    feature_extractor = MFCCFeatureExtractor(feature_config)
    logistic = LogisticRegressionConfig(**config.get("logistic_regression", {}))
    revision, dirty = _git_revision()
    result = run_baseline_experiment(
        dataset_root=dataset_root,
        report=report,
        assignments=assignments,
        split_fractions=split["fractions"],
        split_seed=split["seed"],
        preprocessing_config=preprocessing,
        feature_extractor=feature_extractor,
        code_revision=revision,
        working_tree_dirty=dirty,
        logistic_config=logistic,
        artifact_directory=artifact_directory,
    )
    return {
        "artifact_directory": result.artifact_directory,
        "majority_class": result.majority_class,
        "model_evaluation": asdict(result.model_evaluation),
        "majority_evaluation": asdict(result.majority_evaluation),
        "run_metadata": result.run_metadata,
    }


def check_config_data(config_path: str | Path) -> dict[str, Any]:
    """Validate approved dataset metadata and report group-aware split counts.

    This check does not import ML dependencies, fit a model, or write artifacts.
    """
    path, config = _load_config(config_path)
    dataset_root = _resolve_path(path.parent, config["dataset_root"])
    report = validate_dataset(dataset_root, config["metadata_csv"])
    if not report.ready_for_training:
        problems = [
            f"{issue.code}" + (f" [clip_id={issue.clip_id}]" if issue.clip_id else "")
            for issue in report.issues
        ]
        raise ValueError("dataset is not ready for inspection: " + "; ".join(problems))
    split = config["split"]
    records = [sample.metadata for sample in report.samples]
    assignments = split_by_source_group(
        records, fractions=split["fractions"], seed=split["seed"]
    )
    summary = summarize_split_readiness(records, assignments)
    return {
        "dataset_root": str(dataset_root),
        "clip_count": len(records),
        "grouped_split_ready_for_baseline": all(
            item["ready_for_baseline"] for item in summary.values()
        ),
        "split_seed": split["seed"],
        "split_fractions": split["fractions"],
        "splits": summary,
        "training_started": False,
        "artifacts_written": False,
    }


def _load_config(config_path: str | Path) -> tuple[Path, dict[str, Any]]:
    path = Path(config_path).resolve()
    config = json.loads(path.read_text(encoding="utf-8"))
    _validate_config_shape(config)
    if config.get("config_version") != 1:
        raise ValueError("config_version must be 1")
    return path, config


def _validate_config_shape(config: Any) -> None:
    """Fail early with beginner-readable errors for malformed run JSON."""
    if not isinstance(config, dict):
        raise ValueError("configuration must be a JSON object")
    required = (
        "config_version", "dataset_root", "metadata_csv", "artifact_directory",
        "split", "preprocessing", "feature_extractor",
    )
    missing = [key for key in required if key not in config]
    if missing:
        raise ValueError("configuration is missing required fields: " + ", ".join(missing))
    for key in ("dataset_root", "metadata_csv", "artifact_directory"):
        if not isinstance(config[key], str) or not config[key].strip():
            raise ValueError(f"{key} must be a non-empty path string")
    _require_object_fields(config, "split", ("seed", "fractions"))
    _require_object_fields(config, "preprocessing", (
        "target_sample_rate_hz", "target_duration_seconds", "channel_mix",
        "resampling_method", "clip_strategy", "normalization",
    ))
    _require_object_fields(config, "feature_extractor", ("name", "config"))
    _require_object_fields(config["feature_extractor"], "config", (
        "sample_rate_hz", "channel_handling", "n_mfcc", "n_mels", "n_fft",
        "win_length", "hop_length", "window", "fmin_hz", "fmax_hz",
    ))
    if "logistic_regression" in config and not isinstance(config["logistic_regression"], dict):
        raise ValueError("logistic_regression must be a JSON object")


def _require_object_fields(parent: dict[str, Any], key: str, fields: tuple[str, ...]) -> None:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be a JSON object")
    missing = [field for field in fields if field not in value]
    if missing:
        raise ValueError(f"{key} is missing required fields: " + ", ".join(missing))


def _resolve_path(base: Path, value: str) -> Path:
    path = Path(value)
    return (base / path).resolve() if not path.is_absolute() else path.resolve()


def _git_revision() -> tuple[str | None, bool | None]:
    repository_root = Path(__file__).resolve().parents[1]
    try:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repository_root,
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=repository_root,
            capture_output=True, text=True, check=True,
        ).stdout
        return revision, bool(status.strip())
    except (OSError, subprocess.CalledProcessError):
        return None, None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", help="path to an approved run configuration JSON")
    parser.add_argument(
        "--check-data", action="store_true",
        help="validate reviewed dataset metadata and print grouped split counts; do not train",
    )
    args = parser.parse_args()
    try:
        result = check_config_data(args.config) if args.check_data else run_config(args.config)
    except (KeyError, TypeError, ValueError, RuntimeError, OSError, AttributeError) as error:
        print(f"baseline run refused/failed: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
