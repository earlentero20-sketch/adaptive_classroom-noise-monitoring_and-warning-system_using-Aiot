import json
import unittest

from ml.data_pipeline import AudioFileInfo, PreprocessedAudio, PreprocessingConfig
from ml.experiment import build_run_metadata, run_metadata_sha256
from ml.features import extract_feature_vector


class FixtureExtractor:
    name = "fixture-logmel"
    version = "test-v1"

    def extract(self, audio):
        return (len(audio.samples), audio.sample_rate_hz)


class ExperimentMetadataTests(unittest.TestCase):
    def setUp(self):
        self.preprocessing = PreprocessingConfig(16000, 1.0, "mean", "linear", "center", "none")
        self.kwargs = {
            "split_seed": 73,
            "split_fractions": {"train": 0.7, "validation": 0.15, "test": 0.15},
            "preprocessing_config": self.preprocessing,
            "feature_extractor": {"name": "mfcc", "version": "0.1", "config": {"n_coefficients": 20}},
            "code_revision": "revision-id",
            "dataset_manifest_sha256": "a" * 64,
        }

    def test_run_metadata_is_complete_json_and_stably_hashable(self):
        first = build_run_metadata(**self.kwargs)
        second = build_run_metadata(**self.kwargs)
        json.dumps(first, sort_keys=True)
        self.assertEqual(first, second)
        self.assertEqual(run_metadata_sha256(first), run_metadata_sha256(second))
        self.assertEqual(first["split_seed"], 73)
        self.assertEqual(first["split_fractions"]["test"], 0.15)
        self.assertEqual(first["preprocessing"]["target_sample_rate_hz"], 16000)

    def test_run_metadata_rejects_invalid_split_or_manifest_hash(self):
        invalid = dict(self.kwargs, split_fractions={"train": 1, "validation": 0, "test": 0})
        with self.assertRaises(ValueError):
            build_run_metadata(**invalid)
        invalid = dict(self.kwargs, dataset_manifest_sha256="not-a-hash")
        with self.assertRaises(ValueError):
            build_run_metadata(**invalid)

    def test_feature_extractor_boundary_returns_validated_vector(self):
        config = self.preprocessing
        info = AudioFileInfo(16000, 2, 1, 2, 0.000125, "NONE")
        audio = PreprocessedAudio((0.0, 0.0), 16000, info, config)
        self.assertEqual(extract_feature_vector(FixtureExtractor(), audio), (2.0, 16000.0))


if __name__ == "__main__":
    unittest.main()
