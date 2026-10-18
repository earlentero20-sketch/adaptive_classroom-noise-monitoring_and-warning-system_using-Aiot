"""Canonical run metadata for reproducible, separately implemented training."""

from dataclasses import asdict, is_dataclass
import hashlib
import json
import math
from typing import Any, Mapping


SPLIT_NAMES = ("train", "validation", "test")


def build_run_metadata(
    *,
    split_seed: int,
    split_fractions: Mapping[str, float],
    preprocessing_config: Any,
    feature_extractor: Mapping[str, Any],
    code_revision: str | None,
    dataset_manifest_sha256: str | None,
    working_tree_dirty: bool | None = None,
    model_configuration: Mapping[str, Any] | None = None,
    runtime_info: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Create stable JSON-ready metadata; callers provide revision if available."""
    if type(split_seed) is not int:
        raise ValueError("split_seed must be an integer")
    if set(split_fractions) != set(SPLIT_NAMES):
        raise ValueError("split_fractions must define train, validation, and test")
    if any(isinstance(value, bool) or not isinstance(value, (int, float))
           or not math.isfinite(value) or value <= 0 for value in split_fractions.values()):
        raise ValueError("split fractions must be finite and positive")
    if not math.isclose(sum(split_fractions.values()), 1.0, rel_tol=0, abs_tol=1e-9):
        raise ValueError("split fractions must sum to 1")
    if is_dataclass(preprocessing_config):
        preprocessing = asdict(preprocessing_config)
    elif isinstance(preprocessing_config, Mapping):
        preprocessing = dict(preprocessing_config)
    else:
        raise ValueError("preprocessing_config must be a dataclass or mapping")
    if not feature_extractor.get("name") or not feature_extractor.get("version"):
        raise ValueError("feature_extractor must include name and version")
    if code_revision is not None and (not isinstance(code_revision, str) or not code_revision.strip()):
        raise ValueError("code_revision must be non-empty text or None")
    if working_tree_dirty is not None and type(working_tree_dirty) is not bool:
        raise ValueError("working_tree_dirty must be boolean or None")
    if dataset_manifest_sha256 is not None:
        if (not isinstance(dataset_manifest_sha256, str)
                or len(dataset_manifest_sha256) != 64
                or any(char not in "0123456789abcdefABCDEF" for char in dataset_manifest_sha256)):
            raise ValueError("dataset_manifest_sha256 must be a 64-character SHA-256 hex digest")
    result = {
        "run_metadata_version": 1,
        "split_method": "sha256_source_recording_group_v1",
        "split_seed": split_seed,
        "split_fractions": {name: float(split_fractions[name]) for name in SPLIT_NAMES},
        "preprocessing": preprocessing,
        "feature_extractor": dict(feature_extractor),
        "model_configuration": dict(model_configuration or {}),
        "runtime": dict(runtime_info or {}),
        "code_revision": code_revision,
        "working_tree_dirty": working_tree_dirty,
        "dataset_manifest_sha256": dataset_manifest_sha256,
    }
    # Fail early if a caller included non-JSON configuration objects.
    json.dumps(result, sort_keys=True, ensure_ascii=False, allow_nan=False)
    return result


def run_metadata_sha256(metadata: Mapping[str, Any]) -> str:
    """Hash canonical run metadata for a stable run/config identifier."""
    canonical = json.dumps(metadata, sort_keys=True, ensure_ascii=False,
                           separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
