"""Explicit full-fit command for a non-evaluated classroom demonstration."""

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from ml.baseline import (
    LogisticRegressionConfig,
    run_experimental_full_fit,
)
from ml.data_pipeline import PreprocessingConfig, validate_dataset
from ml.features import MFCCConfig, MFCCFeatureExtractor
from ml.run_baseline import _git_revision, _load_config, _resolve_path


def run_config(
    config_path: str | Path,
    *,
    artifact_directory: str | Path,
    acknowledge_no_held_out_evaluation: bool,
) -> dict[str, Any]:
    path, config = _load_config(config_path)
    dataset_root = _resolve_path(path.parent, config["dataset_root"])
    artifact_path = Path(artifact_directory).resolve()
    if dataset_root == artifact_path or dataset_root in artifact_path.parents:
        raise ValueError("model artifacts must be outside the dataset directory")
    report = validate_dataset(dataset_root, config["metadata_csv"])
    if not report.ready_for_training:
        problems = [
            f"{issue.code}" + (f" [clip_id={issue.clip_id}]" if issue.clip_id else "")
            for issue in report.issues
        ]
        raise ValueError("dataset review gates are not complete: " + "; ".join(problems))
    preprocessing = PreprocessingConfig(**config["preprocessing"])
    feature_config = MFCCConfig(**config["feature_extractor"]["config"])
    if config["feature_extractor"].get("name") != "librosa-mfcc-mean-std":
        raise ValueError("feature_extractor.name must be 'librosa-mfcc-mean-std'")
    code_revision, working_tree_dirty = _git_revision()
    result = run_experimental_full_fit(
        dataset_root=dataset_root,
        report=report,
        preprocessing_config=preprocessing,
        feature_extractor=MFCCFeatureExtractor(feature_config),
        split_seed=config["split"]["seed"],
        code_revision=code_revision,
        working_tree_dirty=working_tree_dirty,
        logistic_config=LogisticRegressionConfig(**config.get("logistic_regression", {})),
        artifact_directory=artifact_path,
        acknowledge_no_held_out_evaluation=acknowledge_no_held_out_evaluation,
    )
    return {
        "artifact_directory": result.artifact_directory,
        "run_metadata": result.run_metadata,
        "training_started": True,
        "held_out_evaluation": None,
        "metrics": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", help="approved dataset and preprocessing configuration JSON")
    parser.add_argument("--artifact-directory", required=True,
                        help="new or empty output directory for experimental artifacts")
    parser.add_argument(
        "--acknowledge-no-held-out-evaluation", action="store_true", required=True,
        help="required confirmation that all reviewed clips are fit and no held-out metrics are produced",
    )
    args = parser.parse_args()
    try:
        result = run_config(
            args.config,
            artifact_directory=args.artifact_directory,
            acknowledge_no_held_out_evaluation=args.acknowledge_no_held_out_evaluation,
        )
    except (KeyError, TypeError, ValueError, RuntimeError, OSError, AttributeError) as error:
        print(f"experimental fit refused/failed: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
