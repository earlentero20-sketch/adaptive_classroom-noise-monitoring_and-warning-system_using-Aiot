"""Dependency-free evaluation metrics for the two-class classifier."""

from dataclasses import dataclass
from typing import Sequence


CLASSES = ("Teacher Discussion", "Student Conversation")


@dataclass(frozen=True)
class ClassMetrics:
    precision: float
    recall: float
    f1_score: float
    support: int


@dataclass(frozen=True)
class EvaluationReport:
    class_metrics: dict[str, ClassMetrics]
    confusion_matrix: dict[str, dict[str, int]]
    accuracy: float
    macro_f1: float
    sample_count: int


def evaluate_predictions(
    actual: Sequence[str], predicted: Sequence[str]
) -> EvaluationReport:
    """Calculate per-class metrics and a matrix with actual rows/predicted columns.

    Undefined precision or recall is reported as zero. Inputs must contain
    only the two approved labels and have equal, non-zero lengths.
    """
    if len(actual) != len(predicted):
        raise ValueError("actual and predicted must have the same length")
    if not actual:
        raise ValueError("at least one labeled example is required")
    if any(label not in CLASSES for label in (*actual, *predicted)):
        raise ValueError(f"labels must be one of: {', '.join(CLASSES)}")

    matrix = {
        actual_label: {predicted_label: 0 for predicted_label in CLASSES}
        for actual_label in CLASSES
    }
    for actual_label, predicted_label in zip(actual, predicted):
        matrix[actual_label][predicted_label] += 1

    per_class: dict[str, ClassMetrics] = {}
    for label in CLASSES:
        true_positive = matrix[label][label]
        support = sum(matrix[label].values())
        predicted_count = sum(matrix[actual_label][label] for actual_label in CLASSES)
        false_negative = support - true_positive
        false_positive = predicted_count - true_positive
        precision = _ratio(true_positive, true_positive + false_positive)
        recall = _ratio(true_positive, true_positive + false_negative)
        f1_score = _ratio(2 * precision * recall, precision + recall)
        per_class[label] = ClassMetrics(precision, recall, f1_score, support)

    correct = sum(matrix[label][label] for label in CLASSES)
    return EvaluationReport(
        class_metrics=per_class,
        confusion_matrix=matrix,
        accuracy=correct / len(actual),
        macro_f1=sum(metric.f1_score for metric in per_class.values()) / len(CLASSES),
        sample_count=len(actual),
    )


def _ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0
