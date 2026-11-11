"""Transport-neutral inference for a locally trained SONIQ WAV model.

This module accepts one complete PCM WAV byte string. It does not know about
HTTP, ESP32 devices, sensors, or warning policy.
"""

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any, Mapping

from ml.data_pipeline import (
    PreprocessingConfig,
    preprocess_wav_bytes,
    validate_audio_bytes,
)
from ml.evaluation import CLASSES
from ml.features import MFCCConfig, MFCCFeatureExtractor, extract_feature_vector


class InvalidAudioSample(ValueError):
    """The supplied sample is not a supported complete PCM WAV input."""


class ModelUnavailableError(RuntimeError):
    """No compatible trained artifact is available for inference."""


@dataclass(frozen=True)
class AudioModelRuntime:
    classifier: Any
    preprocessing: PreprocessingConfig
    feature_extractor: MFCCFeatureExtractor
    artifact_reference: str
    training_mode: str = "evaluated_baseline"

    def classify_wav_bytes(self, payload: bytes) -> dict[str, Any]:
        """Classify one WAV sample and return probability only if the model has it."""
        try:
            audio = preprocess_wav_bytes(payload, self.preprocessing)
        except (TypeError, ValueError) as error:
            raise InvalidAudioSample(str(error)) from error

        features = extract_feature_vector(self.feature_extractor, audio)
        predict_with_confidence = getattr(self.classifier, "predict_with_confidence", None)
        if callable(predict_with_confidence):
            label, probability = predict_with_confidence(features)
        else:
            label = self.classifier.predict(features)
            probability = None
        if label not in CLASSES:
            raise ModelUnavailableError("model returned a label outside the two-class contract")

        confidence = None
        if probability is not None:
            if (isinstance(probability, bool) or not isinstance(probability, (int, float))
                    or not math.isfinite(probability) or not 0.0 <= probability <= 1.0):
                raise ModelUnavailableError("model returned an invalid class probability")
            confidence = {
                "value": float(probability),
                "method": "predict_proba",
                "calibrated": False,
            }
        return {
            "label": label,
            "model_confidence": confidence,
            "artifact_reference": self.artifact_reference,
            "training_mode": self.training_mode,
        }


def load_audio_model(artifact_path: str | Path) -> AudioModelRuntime:
    """Load a trusted local baseline artifact; never load untrusted joblib files."""
    path = Path(artifact_path)
    if not path.is_file():
        raise ModelUnavailableError("trained model artifact is missing")
    try:
        import joblib
    except ImportError as error:
        raise ModelUnavailableError("loading the trained model requires approved joblib dependencies") from error
    try:
        artifact = joblib.load(path)
    except Exception as error:
        raise ModelUnavailableError("trained model artifact could not be loaded") from error
    if not isinstance(artifact, Mapping) or artifact.get("classes") != list(CLASSES):
        raise ModelUnavailableError("model artifact does not match the two-class contract")
    classifier = artifact.get("classifier")
    if not callable(getattr(classifier, "predict", None)):
        raise ModelUnavailableError("model artifact has no compatible classifier")
    preprocessing_data = artifact.get("preprocessing")
    feature_data = artifact.get("feature_extractor")
    if not isinstance(preprocessing_data, Mapping) or not isinstance(feature_data, Mapping):
        raise ModelUnavailableError("model artifact is missing preprocessing metadata")
    if feature_data.get("name") != "librosa-mfcc-mean-std":
        raise ModelUnavailableError("model artifact uses an unsupported feature extractor")
    feature_config = feature_data.get("config")
    if not isinstance(feature_config, Mapping):
        raise ModelUnavailableError("model artifact has invalid feature configuration")
    try:
        preprocessing = PreprocessingConfig(**preprocessing_data)
        extractor = MFCCFeatureExtractor(MFCCConfig(**feature_config))
    except (TypeError, ValueError) as error:
        raise ModelUnavailableError("model artifact has invalid preprocessing configuration") from error
    manifest_digest = artifact.get("manifest_sha256")
    reference = str(manifest_digest) if isinstance(manifest_digest, str) and manifest_digest else path.name
    training_mode = artifact.get("training_mode", "evaluated_baseline")
    if training_mode not in (
        "evaluated_baseline", "experimental_full_fit_no_held_out_evaluation"
    ):
        raise ModelUnavailableError("model artifact has an unknown training mode")
    return AudioModelRuntime(classifier, preprocessing, extractor, reference, training_mode)


def validate_wav_sample(payload: bytes) -> None:
    """Validate the transport-neutral input before checking model availability."""
    try:
        validate_audio_bytes(payload)
    except (TypeError, ValueError) as error:
        raise InvalidAudioSample(str(error)) from error
