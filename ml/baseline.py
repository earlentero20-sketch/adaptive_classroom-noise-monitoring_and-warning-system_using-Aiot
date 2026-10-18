"""Approved-data MFCC + regularized logistic-regression baseline workflow."""

from dataclasses import asdict, dataclass
import hashlib
from importlib.metadata import PackageNotFoundError, version as package_version
import json
import math
from pathlib import Path
import platform
from typing import Any, Mapping, Sequence

from ml.data_pipeline import (
    DatasetReport,
    PreprocessingConfig,
    ValidatedSample,
    assert_no_group_leakage,
    build_manifest,
    group_id,
    preprocess_wav,
    split_by_source_group,
    summarize_split_readiness,
)
from ml.evaluation import CLASSES, EvaluationReport
from ml.experiment import build_run_metadata
from ml.features import AudioFeatureExtractor, extract_feature_vector
from ml.training import (
    FeatureExample,
    TrainingRun,
    evaluate_held_out,
    fit_model,
)


@dataclass(frozen=True)
class LogisticRegressionConfig:
    regularization_c: float = 1.0
    max_iterations: int = 2000

    def __post_init__(self) -> None:
        if isinstance(self.regularization_c, bool) or not isinstance(self.regularization_c, (int, float)):
            raise ValueError("regularization_c must be finite and positive")
        if not float(self.regularization_c) > 0 or not math.isfinite(self.regularization_c):
            raise ValueError("regularization_c must be finite and positive")
        if type(self.max_iterations) is not int or self.max_iterations <= 0:
            raise ValueError("max_iterations must be a positive integer")


@dataclass(frozen=True)
class BaselineResult:
    classifier: Any
    majority_class: str
    model_evaluation: EvaluationReport
    majority_evaluation: EvaluationReport
    run_metadata: dict[str, Any]
    artifact_directory: str | None


@dataclass(frozen=True)
class ExperimentalFitResult:
    classifier: Any
    run_metadata: dict[str, Any]
    artifact_directory: str | None


class LogisticRegressionTrainer:
    """Fits scaling and L2 logistic regression using training examples only."""

    def __init__(self, config: LogisticRegressionConfig):
        self.config = config

    def fit(
        self,
        training: Sequence[FeatureExample],
        validation: Sequence[FeatureExample],
        *,
        seed: int,
    ) -> "SklearnClassifier":
        del validation  # Fixed baseline: validation is held out, not used to fit.
        try:
            from sklearn.linear_model import LogisticRegression
            from sklearn.pipeline import make_pipeline
            from sklearn.preprocessing import StandardScaler
        except ImportError as error:
            raise RuntimeError(
                "baseline training requires approved scikit-learn dependencies"
            ) from error
        estimator = make_pipeline(
            StandardScaler(),
            LogisticRegression(
                C=float(self.config.regularization_c),
                max_iter=self.config.max_iterations,
                solver="liblinear",
                penalty="l2",
                random_state=seed,
            ),
        )
        estimator.fit(
            [example.features for example in training],
            [example.label for example in training],
        )
        return SklearnClassifier(estimator)


class SklearnClassifier:
    """Adapts scikit-learn's 2D predict API to the project's feature interface."""

    def __init__(self, estimator: Any):
        self.estimator = estimator

    def predict(self, features: Sequence[float]) -> str:
        prediction = self.estimator.predict([list(features)])[0]
        label = str(prediction)
        if label not in CLASSES:
            raise ValueError("trained classifier returned a label outside the two-class contract")
        return label

    def predict_with_confidence(
        self, features: Sequence[float]
    ) -> tuple[str, float | None]:
        """Return the predicted class and its model probability when supported.

        Logistic-regression probabilities are not calibrated confidence and
        are not used as a warning gate.
        """
        label = self.predict(features)
        predict_proba = getattr(self.estimator, "predict_proba", None)
        classes = getattr(self.estimator, "classes_", None)
        if not callable(predict_proba) or classes is None:
            return label, None
        probabilities = predict_proba([list(features)])[0]
        for model_class, probability in zip(classes, probabilities):
            if str(model_class) == label:
                score = float(probability)
                if not math.isfinite(score) or not 0.0 <= score <= 1.0:
                    raise ValueError("classifier returned an invalid class probability")
                return label, score
        raise ValueError("classifier probability classes do not include its prediction")


class MajorityClassifier:
    def __init__(self, label: str):
        if label not in CLASSES:
            raise ValueError("majority label must be one of the two approved classes")
        self.label = label

    def predict(self, features: Sequence[float]) -> str:
        del features
        return self.label


def run_baseline_experiment(
    *,
    dataset_root: str | Path,
    report: DatasetReport,
    assignments: Mapping[str, str],
    split_fractions: Mapping[str, float],
    split_seed: int,
    preprocessing_config: PreprocessingConfig,
    feature_extractor: AudioFeatureExtractor,
    code_revision: str | None = None,
    working_tree_dirty: bool | None = None,
    logistic_config: LogisticRegressionConfig = LogisticRegressionConfig(),
    artifact_directory: str | Path | None = None,
) -> BaselineResult:
    """Train/evaluate two host baselines on approved real WAV data only.

    This function requires an already reviewed dataset. Approval fields are
    still human assertions and are not legal or consent verification. Artifacts
    are written only after a successful real-data run and only when an explicit
    output directory is supplied.
    """
    _require_approved_real_dataset(report)
    root = Path(dataset_root).resolve()
    records = [sample.metadata for sample in report.samples]
    assert_no_group_leakage(records, assignments)
    expected_assignments = split_by_source_group(
        records, fractions=split_fractions, seed=split_seed
    )
    if dict(assignments) != expected_assignments:
        raise ValueError("assignments do not match the recorded grouped-split seed and proportions")
    readiness = summarize_split_readiness(records, assignments)
    if not all(result["ready_for_baseline"] for result in readiness.values()):
        raise ValueError("each split needs both classes and at least two independent groups per class")
    _check_artifact_destination(artifact_directory)

    by_split: dict[str, list[FeatureExample]] = {name: [] for name in ("train", "validation", "test")}
    for sample in report.samples:
        audio_path = (root / sample.metadata.relative_path).resolve()
        if root not in audio_path.parents:
            raise ValueError("sample path resolves outside dataset root")
        if _sha256_file(audio_path) != sample.sha256:
            raise ValueError(f"audio changed since validation: {sample.metadata.clip_id}")
        processed = preprocess_wav(audio_path, preprocessing_config)
        if _sha256_file(audio_path) != sample.sha256:
            raise ValueError(f"audio changed during preprocessing: {sample.metadata.clip_id}")
        features = extract_feature_vector(feature_extractor, processed)
        example = FeatureExample(
            sample.metadata.clip_id,
            group_id(sample.metadata),
            sample.metadata.label,
            features,
        )
        by_split[assignments[sample.metadata.clip_id]].append(example)

    training = by_split["train"]
    validation = by_split["validation"]
    testing = by_split["test"]
    train_counts = {label: sum(example.label == label for example in training) for label in CLASSES}
    majority_label = max(CLASSES, key=lambda label: (train_counts[label], -CLASSES.index(label)))
    training_run = fit_model(
        LogisticRegressionTrainer(logistic_config), training, validation, seed=split_seed
    )
    model_evaluation = evaluate_held_out(training_run, testing)
    majority_run = TrainingRun(
        MajorityClassifier(majority_label),
        training_run.seen_group_ids,
        training_run.seen_clip_ids,
        training_run.feature_count,
    )
    majority_evaluation = evaluate_held_out(majority_run, testing)

    manifest = build_manifest(report, preprocessing_config, assignments)
    manifest_digest = hashlib.sha256(_canonical_json(manifest).encode("utf-8")).hexdigest()
    feature_metadata = _extractor_metadata(feature_extractor)
    run_metadata = build_run_metadata(
        split_seed=split_seed,
        split_fractions=split_fractions,
        preprocessing_config=preprocessing_config,
        feature_extractor=feature_metadata,
        code_revision=code_revision,
        dataset_manifest_sha256=manifest_digest,
        working_tree_dirty=working_tree_dirty,
        model_configuration={
            "family": "logistic_regression",
            "regularization": "l2",
            "regularization_c": float(logistic_config.regularization_c),
            "max_iterations": logistic_config.max_iterations,
            "solver": "liblinear",
            "standard_scaler": True,
        },
        runtime_info=_runtime_info(),
    )
    result = BaselineResult(
        classifier=training_run.classifier,
        majority_class=majority_label,
        model_evaluation=model_evaluation,
        majority_evaluation=majority_evaluation,
        run_metadata=run_metadata,
        artifact_directory=None,
    )
    if artifact_directory is not None:
        _write_artifacts(
            Path(artifact_directory), result, manifest, logistic_config, feature_metadata
        )
        result = BaselineResult(
            result.classifier,
            result.majority_class,
            result.model_evaluation,
            result.majority_evaluation,
            result.run_metadata,
            str(Path(artifact_directory).resolve()),
        )
    return result


def run_experimental_full_fit(
    *,
    dataset_root: str | Path,
    report: DatasetReport,
    preprocessing_config: PreprocessingConfig,
    feature_extractor: AudioFeatureExtractor,
    split_seed: int,
    code_revision: str | None = None,
    working_tree_dirty: bool | None = None,
    logistic_config: LogisticRegressionConfig = LogisticRegressionConfig(),
    artifact_directory: str | Path | None = None,
    acknowledge_no_held_out_evaluation: bool = False,
) -> ExperimentalFitResult:
    """Fit all approved clips for an explicitly non-evaluated demonstration.

    This is not the normal baseline command. It preserves all source, consent,
    annotation, quality, and privacy gates, but deliberately does not split or
    evaluate groups. Its artifacts must be labeled experimental.
    """
    if acknowledge_no_held_out_evaluation is not True:
        raise ValueError("experimental fit requires explicit acknowledgement that no held-out evaluation is performed")
    if type(split_seed) is not int:
        raise ValueError("split_seed must be an integer")
    _require_approved_real_dataset(report)
    records = [sample.metadata for sample in report.samples]
    if {record.label for record in records} != set(CLASSES):
        raise ValueError("experimental fit requires reviewed examples from both approved classes")
    groups_by_class = {
        label: {group_id(record) for record in records if record.label == label}
        for label in CLASSES
    }
    if any(len(groups_by_class[label]) < 2 for label in CLASSES):
        raise ValueError("experimental fit requires at least two independent reviewed source recordings per class")
    _check_experimental_artifact_destination(artifact_directory)

    root = Path(dataset_root).resolve()
    examples = []
    for sample in report.samples:
        audio_path = (root / sample.metadata.relative_path).resolve()
        if root not in audio_path.parents:
            raise ValueError("sample path resolves outside dataset root")
        if _sha256_file(audio_path) != sample.sha256:
            raise ValueError(f"audio changed since validation: {sample.metadata.clip_id}")
        processed = preprocess_wav(audio_path, preprocessing_config)
        if _sha256_file(audio_path) != sample.sha256:
            raise ValueError(f"audio changed during preprocessing: {sample.metadata.clip_id}")
        examples.append(FeatureExample(
            sample.metadata.clip_id,
            group_id(sample.metadata),
            sample.metadata.label,
            extract_feature_vector(feature_extractor, processed),
        ))
    if len({item.clip_id for item in examples}) != len(examples):
        raise ValueError("clip IDs must be unique for experimental fit")
    if len({len(item.features) for item in examples}) != 1:
        raise ValueError("feature vectors must all have the same length")

    # No validation or test examples are implied: every reviewed clip is fit.
    classifier = LogisticRegressionTrainer(logistic_config).fit(
        examples, (), seed=split_seed
    )
    manifest = build_manifest(report, preprocessing_config)
    manifest_digest = hashlib.sha256(_canonical_json(manifest).encode("utf-8")).hexdigest()
    feature_metadata = _extractor_metadata(feature_extractor)
    class_counts = {label: sum(record.label == label for record in records) for label in CLASSES}
    run_metadata = {
        "run_metadata_version": 1,
        "run_mode": "experimental_full_fit_no_held_out_evaluation",
        "split_method": "none_all_approved_clips_used_for_fit",
        "split_seed": split_seed,
        "training_clip_count": len(examples),
        "class_counts": class_counts,
        "independent_groups_per_class": {label: len(groups_by_class[label]) for label in CLASSES},
        "preprocessing": asdict(preprocessing_config),
        "feature_extractor": feature_metadata,
        "model_configuration": {
            "family": "logistic_regression", "regularization": "l2",
            "regularization_c": float(logistic_config.regularization_c),
            "max_iterations": logistic_config.max_iterations,
            "solver": "liblinear", "standard_scaler": True,
        },
        "code_revision": code_revision,
        "working_tree_dirty": working_tree_dirty,
        "dataset_manifest_sha256": manifest_digest,
        "held_out_evaluation": None,
        "metrics": None,
        "runtime": _runtime_info(),
    }
    _canonical_json(run_metadata)
    output = None
    if artifact_directory is not None:
        try:
            import joblib
        except ImportError as error:
            raise RuntimeError("experimental artifact saving requires approved scikit-learn/joblib dependencies") from error
        destination = Path(artifact_directory)
        destination.mkdir(parents=True, exist_ok=True)
        joblib.dump({
            "model": classifier.estimator,
            "classifier": classifier,
            "classes": list(CLASSES),
            "training_mode": "experimental_full_fit_no_held_out_evaluation",
            "logistic_config": asdict(logistic_config),
            "preprocessing": asdict(preprocessing_config),
            "feature_extractor": feature_metadata,
            "manifest_sha256": manifest_digest,
        }, destination / "experimental_model.joblib")
        (destination / "run_metadata.json").write_text(
            _canonical_json(run_metadata) + "\n", encoding="utf-8", newline="\n"
        )
        (destination / "dataset_manifest.json").write_text(
            _canonical_json(manifest) + "\n", encoding="utf-8", newline="\n"
        )
        output = str(destination.resolve())
    return ExperimentalFitResult(classifier, run_metadata, output)


def _check_experimental_artifact_destination(destination: str | Path | None) -> None:
    if destination is None:
        return
    path = Path(destination)
    if path.exists() and (not path.is_dir() or any(path.iterdir())):
        raise FileExistsError("experimental artifact destination must be a new or empty directory")


def _require_approved_real_dataset(report: DatasetReport) -> None:
    if not report.ready_for_training or report.issues or not report.samples:
        raise ValueError("dataset validation must be ready and have no unresolved issues")
    for sample in report.samples:
        record = sample.metadata
        if record.approval_status != "approved":
            raise ValueError(f"source is not approved: {record.clip_id}")
        if record.annotation_status != "reviewed":
            raise ValueError(f"annotation is not reviewed: {record.clip_id}")
        if record.source_type == "synthetic":
            raise ValueError("synthetic fixtures are not accepted for a real training run")
        required_references = (
            record.source_reference, record.license_id, record.license_reference,
            record.approval_reference, record.privacy_review_ref,
            record.annotation_review_ref,
        )
        if not all(required_references):
            raise ValueError(f"required human review references are missing: {record.clip_id}")
        if record.source_type == "classroom" and not record.consent_ref:
            raise ValueError(f"classroom consent reference is missing: {record.clip_id}")


def _extractor_metadata(extractor: AudioFeatureExtractor) -> dict[str, Any]:
    metadata_method = getattr(extractor, "metadata", None)
    if callable(metadata_method):
        return metadata_method()
    return {"name": extractor.name, "version": extractor.version}


def _check_artifact_destination(destination: str | Path | None) -> None:
    if destination is None:
        return
    path = Path(destination)
    if path.exists() and not path.is_dir():
        raise ValueError("artifact destination exists and is not a directory")
    expected = ("baseline.joblib", "run_metadata.json", "evaluation.json", "dataset_manifest.json")
    if path.is_dir() and any((path / name).exists() for name in expected):
        raise FileExistsError("artifact destination already contains a baseline run")


def _write_artifacts(
    destination: Path,
    result: BaselineResult,
    manifest: Mapping[str, Any],
    logistic_config: LogisticRegressionConfig,
    feature_metadata: Mapping[str, Any],
) -> None:
    try:
        import joblib
    except ImportError as error:
        raise RuntimeError("artifact saving requires the approved scikit-learn/joblib dependency") from error
    destination.mkdir(parents=True, exist_ok=True)
    bundle = {
        "model": result.classifier.estimator,
        "classifier": result.classifier,
        "classes": list(CLASSES),
        "training_mode": "evaluated_baseline",
        "logistic_config": asdict(logistic_config),
        "preprocessing": dict(manifest["preprocessing"]),
        "feature_extractor": dict(feature_metadata),
        "manifest_sha256": result.run_metadata["dataset_manifest_sha256"],
    }
    joblib.dump(bundle, destination / "baseline.joblib")
    (destination / "run_metadata.json").write_text(
        _canonical_json(result.run_metadata) + "\n", encoding="utf-8", newline="\n"
    )
    (destination / "dataset_manifest.json").write_text(
        _canonical_json(manifest) + "\n", encoding="utf-8", newline="\n"
    )
    evaluation = {
        "model": asdict(result.model_evaluation),
        "majority_class": result.majority_class,
        "majority_reference": asdict(result.majority_evaluation),
    }
    (destination / "evaluation.json").write_text(
        _canonical_json(evaluation) + "\n", encoding="utf-8", newline="\n"
    )


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _runtime_info() -> dict[str, Any]:
    result: dict[str, Any] = {"python": platform.python_version()}
    for distribution in ("numpy", "librosa", "scikit-learn", "scipy"):
        try:
            result[distribution] = package_version(distribution)
        except PackageNotFoundError:
            result[distribution] = None
    return result


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
