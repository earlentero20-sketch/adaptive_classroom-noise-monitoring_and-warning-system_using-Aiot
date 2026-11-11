"""Stable two-class prediction adapter for the provisional event contract."""

from datetime import datetime
from typing import Protocol, Sequence

from ml.evaluation import CLASSES


class Classifier(Protocol):
    def predict(self, features: Sequence[float]) -> str: ...


def classification_result(
    classifier: Classifier,
    features: Sequence[float],
    *,
    observed_at: str,
    confident: bool = False,
) -> dict[str, object]:
    """Return only contract fields; confidence stays false absent an approved rule."""
    if type(confident) is not bool:
        raise ValueError("confident must be a boolean")
    if not isinstance(observed_at, str) or not observed_at.strip():
        raise ValueError("observed_at must be a timezone-aware ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("observed_at must be a timezone-aware ISO-8601 timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("observed_at must include a timezone")
    label = classifier.predict(features)
    if label not in CLASSES:
        raise ValueError("classifier returned a label outside the two-class contract")
    return {"label": label, "confident": confident, "observed_at": observed_at}
