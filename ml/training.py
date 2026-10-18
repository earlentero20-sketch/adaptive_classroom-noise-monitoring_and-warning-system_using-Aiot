"""Architecture-neutral training and held-out evaluation interfaces.

This module deliberately contains no model implementation. A team-approved
trainer can implement the protocol without coupling inference to its library.
"""

from dataclasses import dataclass
import math
from typing import Protocol, Sequence

from ml.evaluation import CLASSES, EvaluationReport, evaluate_predictions


@dataclass(frozen=True)
class FeatureExample:
    clip_id: str
    group_id: str
    label: str
    features: tuple[float, ...]


class FittedClassifier(Protocol):
    def predict(self, features: Sequence[float]) -> str: ...


class Trainer(Protocol):
    def fit(
        self,
        training: Sequence[FeatureExample],
        validation: Sequence[FeatureExample],
        *,
        seed: int,
    ) -> FittedClassifier: ...


@dataclass(frozen=True)
class TrainingRun:
    classifier: FittedClassifier
    seen_group_ids: frozenset[str]
    seen_clip_ids: frozenset[str]
    feature_count: int


def fit_model(
    trainer: Trainer,
    training: Sequence[FeatureExample],
    validation: Sequence[FeatureExample],
    *,
    seed: int,
) -> TrainingRun:
    """Fit a supplied implementation after checking labels, shapes, and groups."""
    if type(seed) is not int:
        raise ValueError("seed must be an integer")
    training = tuple(training)
    validation = tuple(validation)
    if not training or not validation:
        raise ValueError("training and validation sets must both be non-empty")
    _validate_examples((*training, *validation))
    train_groups = {example.group_id for example in training}
    validation_groups = {example.group_id for example in validation}
    if train_groups & validation_groups:
        raise ValueError("source groups must not cross training and validation")
    if {example.label for example in training} != set(CLASSES):
        raise ValueError("training set must contain examples from both approved classes")
    classifier = trainer.fit(training, validation, seed=seed)
    if not callable(getattr(classifier, "predict", None)):
        raise TypeError("trainer must return an object with predict(features)")
    return TrainingRun(
        classifier,
        frozenset(train_groups | validation_groups),
        frozenset(example.clip_id for example in (*training, *validation)),
        len(training[0].features),
    )


def evaluate_held_out(
    run: TrainingRun, testing: Sequence[FeatureExample]
) -> EvaluationReport:
    """Evaluate once on held-out groups and return the existing metrics report."""
    testing = tuple(testing)
    if not testing:
        raise ValueError("test set must be non-empty")
    _validate_examples(testing, expected_feature_count=run.feature_count)
    if run.seen_clip_ids & {example.clip_id for example in testing}:
        raise ValueError("test clips overlap training or validation")
    test_groups = {example.group_id for example in testing}
    if run.seen_group_ids & test_groups:
        raise ValueError("test source groups overlap training or validation")
    predictions = [run.classifier.predict(example.features) for example in testing]
    return evaluate_predictions(
        [example.label for example in testing], predictions
    )


def _validate_examples(
    examples: Sequence[FeatureExample], expected_feature_count: int | None = None
) -> None:
    if len({example.clip_id for example in examples}) != len(examples):
        raise ValueError("clip IDs must be unique")
    feature_count = expected_feature_count
    for example in examples:
        if not example.clip_id.strip() or not example.group_id.strip():
            raise ValueError("clip and source group IDs must be non-empty")
        if example.label not in CLASSES:
            raise ValueError("labels must be one of the two approved classes")
        if not example.features:
            raise ValueError("feature vectors must not be empty")
        if feature_count is None:
            feature_count = len(example.features)
        if len(example.features) != feature_count:
            raise ValueError("feature vectors must all have the same length")
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
               for value in example.features):
            raise ValueError("feature values must be finite numbers")
