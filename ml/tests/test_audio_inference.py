from io import BytesIO
import importlib.util
import math
from pathlib import Path
import tempfile
import unittest
import wave
from dataclasses import asdict

from ml.audio_inference import (
    AudioModelRuntime,
    InvalidAudioSample,
    ModelUnavailableError,
    load_audio_model,
    validate_wav_sample,
)
from ml.baseline import SklearnClassifier
from ml.data_pipeline import PreprocessingConfig, preprocess_wav_bytes
from ml.evaluation import CLASSES
from ml.features import MFCCConfig, MFCCFeatureExtractor
from ml.training import FeatureExample


def pcm_wav_bytes(*, rate=8000, frames=800, channels=1, sample_width=2):
    output = BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(sample_width)
        wav.setframerate(rate)
        wav.writeframes(b"\0" * frames * channels * sample_width)
    return output.getvalue()


class FixtureExtractor:
    name = "controlled-unit-fixture"
    version = "1"

    def extract(self, audio):
        return (float(len(audio.samples)), float(audio.sample_rate_hz))


class FixtureClassifier:
    def predict(self, features):
        return "Teacher Discussion"

    def predict_with_confidence(self, features):
        return "Teacher Discussion", 0.625


class AudioInferenceTests(unittest.TestCase):
    def test_valid_wav_is_preprocessed_deterministically_in_memory(self):
        sample = pcm_wav_bytes(rate=8000, frames=800)
        config = PreprocessingConfig(8000, 0.1, "mean", "linear", "center", "none")
        first = preprocess_wav_bytes(sample, config)
        second = preprocess_wav_bytes(sample, config)
        self.assertEqual(first, second)
        self.assertEqual(len(first.samples), 800)
        self.assertEqual(first.sample_rate_hz, 8000)

    def test_invalid_and_empty_audio_are_rejected(self):
        for sample in (b"", b"not a wav", pcm_wav_bytes()[:-5]):
            with self.subTest(length=len(sample)):
                with self.assertRaises(InvalidAudioSample):
                    validate_wav_sample(sample)

    def test_runtime_returns_two_class_result_and_uncalibrated_model_probability(self):
        config = PreprocessingConfig(8000, 0.1, "mean", "linear", "center", "none")
        runtime = AudioModelRuntime(
            FixtureClassifier(), config, FixtureExtractor(), "controlled-test-artifact"
        )
        result = runtime.classify_wav_bytes(pcm_wav_bytes())
        self.assertEqual(result["label"], "Teacher Discussion")
        self.assertEqual(result["artifact_reference"], "controlled-test-artifact")
        self.assertEqual(result["model_confidence"], {
            "value": 0.625,
            "method": "predict_proba",
            "calibrated": False,
        })

    def test_runtime_rejects_invalid_wav_before_classification(self):
        config = PreprocessingConfig(8000, 0.1, "mean", "linear", "center", "none")
        runtime = AudioModelRuntime(
            FixtureClassifier(), config, FixtureExtractor(), "controlled-test-artifact"
        )
        with self.assertRaises(InvalidAudioSample):
            runtime.classify_wav_bytes(b"invalid")

    def test_missing_model_artifact_fails_clearly(self):
        with self.assertRaisesRegex(ModelUnavailableError, "artifact is missing"):
            load_audio_model("path-that-does-not-exist.joblib")

    @unittest.skipUnless(
        importlib.util.find_spec("joblib")
        and importlib.util.find_spec("sklearn")
        and importlib.util.find_spec("librosa")
        and importlib.util.find_spec("numpy"),
        "approved model artifact dependencies are not installed",
    )
    def test_synthetic_baseline_artifact_round_trips_through_backend_runtime(self):
        import joblib

        from ml.baseline import LogisticRegressionConfig, LogisticRegressionTrainer

        examples = (
            FeatureExample("teacher-a", "group-teacher-a", CLASSES[0], tuple([0.0] * 40)),
            FeatureExample("teacher-b", "group-teacher-b", CLASSES[0], tuple([0.1] * 40)),
            FeatureExample("student-a", "group-student-a", CLASSES[1], tuple([1.0] * 40)),
            FeatureExample("student-b", "group-student-b", CLASSES[1], tuple([0.9] * 40)),
        )
        classifier = LogisticRegressionTrainer(LogisticRegressionConfig()).fit(
            examples, (), seed=73
        )
        preprocessing = PreprocessingConfig(8000, 0.1, "mean", "linear", "center", "none")
        feature_config = MFCCConfig(
            sample_rate_hz=8000,
            channel_handling="preprocessed_mono",
            n_mfcc=20,
            n_mels=40,
            n_fft=256,
            win_length=256,
            hop_length=128,
            window="hann",
            fmin_hz=0.0,
            fmax_hz=3900.0,
        )
        bundle = {
            "model": classifier.estimator,
            "classifier": classifier,
            "classes": list(CLASSES),
            "training_mode": "evaluated_baseline",
            "logistic_config": asdict(LogisticRegressionConfig()),
            "preprocessing": asdict(preprocessing),
            "feature_extractor": MFCCFeatureExtractor(feature_config).metadata(),
        }

        with tempfile.TemporaryDirectory() as temporary:
            artifact = Path(temporary) / "baseline.joblib"
            joblib.dump(bundle, artifact)
            runtime = load_audio_model(artifact)
            result = runtime.classify_wav_bytes(pcm_wav_bytes(rate=8000, frames=800))

        self.assertIn(result["label"], CLASSES)
        self.assertEqual(result["training_mode"], "evaluated_baseline")
        self.assertEqual(result["artifact_reference"], "baseline.joblib")

    def test_classifier_without_probability_reports_confidence_unavailable(self):
        class LabelOnlyClassifier:
            def predict(self, features):
                return "Student Conversation"

        config = PreprocessingConfig(8000, 0.1, "mean", "linear", "center", "none")
        runtime = AudioModelRuntime(
            LabelOnlyClassifier(), config, FixtureExtractor(), "controlled-test-artifact"
        )
        result = runtime.classify_wav_bytes(pcm_wav_bytes())
        self.assertEqual(result["label"], "Student Conversation")
        self.assertIsNone(result["model_confidence"])

    def test_invalid_probability_is_not_returned(self):
        class InvalidProbabilityClassifier:
            def predict_with_confidence(self, features):
                return "Student Conversation", math.inf

        config = PreprocessingConfig(8000, 0.1, "mean", "linear", "center", "none")
        runtime = AudioModelRuntime(
            InvalidProbabilityClassifier(), config, FixtureExtractor(), "controlled-test-artifact"
        )
        with self.assertRaises(ModelUnavailableError):
            runtime.classify_wav_bytes(pcm_wav_bytes())

    def test_sklearn_adapter_returns_the_probability_for_its_predicted_class(self):
        class EstimatorFixture:
            classes_ = ["Student Conversation", "Teacher Discussion"]

            def predict(self, rows):
                return ["Teacher Discussion"]

            def predict_proba(self, rows):
                return [[0.35, 0.65]]

        label, probability = SklearnClassifier(EstimatorFixture()).predict_with_confidence((1.0, 2.0))
        self.assertEqual(label, "Teacher Discussion")
        self.assertEqual(probability, 0.65)


if __name__ == "__main__":
    unittest.main()
