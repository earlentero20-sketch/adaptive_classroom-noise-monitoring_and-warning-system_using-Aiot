import importlib.util
import math
import unittest

from ml.data_pipeline import AudioFileInfo, PreprocessedAudio, PreprocessingConfig
from ml.features import MFCCConfig, MFCCFeatureExtractor, extract_feature_vector


def audio_fixture(*, rate=8000, duration=1.0, sample_value=None):
    config = PreprocessingConfig(rate, duration, "mean", "linear", "center", "none")
    count = config.target_sample_count
    values = tuple(
        sample_value(index, rate) if sample_value else math.sin(2 * math.pi * 440 * index / rate)
        for index in range(count)
    )
    info = AudioFileInfo(rate, count, 1, 2, count / rate, "NONE")
    return PreprocessedAudio(values, rate, info, config)


def config(*, sample_rate_hz=8000, n_fft=256, win_length=256, hop_length=128):
    return MFCCConfig(
        sample_rate_hz=sample_rate_hz,
        channel_handling="preprocessed_mono",
        n_mfcc=20,
        n_mels=40,
        n_fft=n_fft,
        win_length=win_length,
        hop_length=hop_length,
        window="hann",
        fmin_hz=0.0,
        fmax_hz=3900.0 if sample_rate_hz == 8000 else sample_rate_hz / 2 - 100,
    )


class MFCCFeatureTests(unittest.TestCase):
    def test_invalid_configuration_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "win_length"):
            config(n_fft=128, win_length=256)
        with self.assertRaisesRegex(ValueError, "frequency bounds"):
            MFCCConfig(8000, "preprocessed_mono", 20, 40, 256, 256, 128, "hann", 4000.0, 4100.0)

    def test_invalid_audio_is_rejected_before_optional_import(self):
        extractor = MFCCFeatureExtractor(config())
        with self.assertRaisesRegex(ValueError, "sample rate"):
            extractor.extract(audio_fixture(rate=16000))
        sample = audio_fixture()
        inconsistent = PreprocessedAudio(
            sample.samples[:-1], sample.sample_rate_hz, sample.source_info, sample.config
        )
        with self.assertRaisesRegex(ValueError, "length does not match"):
            extractor.extract(inconsistent)
        too_short = audio_fixture(duration=0.01)
        with self.assertRaisesRegex(ValueError, "shorter than one"):
            extractor.extract(too_short)
        non_finite = audio_fixture(sample_value=lambda index, rate: float("nan"))
        with self.assertRaisesRegex(ValueError, "finite"):
            extractor.extract(non_finite)

    def test_extractor_boundary_rejects_invalid_vector_values(self):
        class BadExtractor:
            name = "bad"
            version = "1"

            def extract(self, audio):
                return (1.0, float("inf"))

        with self.assertRaisesRegex(ValueError, "finite numeric"):
            extract_feature_vector(BadExtractor(), audio_fixture())

    @unittest.skipUnless(
        importlib.util.find_spec("librosa") and importlib.util.find_spec("numpy"),
        "approved librosa and NumPy packages are not installed",
    )
    def test_mfcc_shape_and_output_are_deterministic(self):
        extractor = MFCCFeatureExtractor(config())
        sample = audio_fixture()
        first = extractor.extract(sample)
        second = extractor.extract(sample)
        self.assertEqual(len(first), 40)
        self.assertEqual(first, second)
        self.assertTrue(all(math.isfinite(value) for value in first))

    @unittest.skipIf(
        importlib.util.find_spec("librosa") and importlib.util.find_spec("numpy"),
        "the optional dependencies are installed",
    )
    def test_missing_optional_dependencies_fail_with_clear_message(self):
        with self.assertRaisesRegex(RuntimeError, "librosa and NumPy"):
            MFCCFeatureExtractor(config()).extract(audio_fixture())


if __name__ == "__main__":
    unittest.main()
