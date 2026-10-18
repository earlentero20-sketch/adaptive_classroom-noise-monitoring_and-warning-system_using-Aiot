import json
import csv
import tempfile
import unittest
from pathlib import Path

from ml.data_pipeline import METADATA_COLUMNS
from ml.run_baseline import _load_config, check_config_data, run_config


class RunConfigValidationTests(unittest.TestCase):
    def test_checked_in_example_is_complete_but_keeps_placeholders(self):
        template = Path(__file__).parents[1] / "config" / "first-baseline.example.json"
        _, config = _load_config(template)
        self.assertIn("<REPLACE_WITH_APPROVED_DATASET_DIRECTORY>", config["dataset_root"])
        self.assertIn("<REPLACE_WITH_UNIQUE_RUN_NAME>", config["artifact_directory"])

    def test_check_data_refuses_missing_dataset_without_training(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = root / "config.json"
            value = {
                "config_version": 1,
                "dataset_root": "missing-dataset",
                "metadata_csv": "metadata.csv",
                "artifact_directory": "artifacts/run",
                "split": {"seed": 73, "fractions": {"train": 0.7, "validation": 0.15, "test": 0.15}},
                "preprocessing": {
                    "target_sample_rate_hz": 16000, "target_duration_seconds": 1.0,
                    "channel_mix": "mean", "resampling_method": "linear",
                    "clip_strategy": "center", "normalization": "none",
                },
                "feature_extractor": {
                    "name": "librosa-mfcc-mean-std",
                    "config": {
                        "sample_rate_hz": 16000, "channel_handling": "preprocessed_mono",
                        "n_mfcc": 20, "n_mels": 40, "n_fft": 400, "win_length": 400,
                        "hop_length": 160, "window": "hann", "fmin_hz": 0.0,
                        "fmax_hz": 7600.0,
                    },
                },
            }
            config.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "dataset_root_missing"):
                check_config_data(config)

    def test_check_data_resolves_metadata_relative_to_dataset_root_outside_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = root / "config" / "first-baseline.json"
            config.parent.mkdir()
            dataset_root = root / "data" / "classroom_collection"
            dataset_root.mkdir(parents=True)
            metadata = root / "data" / "metadata" / "classroom_metadata.csv"
            metadata.parent.mkdir(parents=True)
            row = {column: "" for column in METADATA_COLUMNS}
            row.update({
                "clip_id": "fixture-clip",
                "relative_path": "audio/fixture.wav",
                "label": "Student Conversation",
                "original_recording_id": "fixture-recording",
                "source_id": "fixture-source",
                "source_type": "classroom",
                "approval_status": "pending",
                "annotation_status": "pending",
            })
            with metadata.open("w", newline="", encoding="utf-8") as output:
                writer = csv.DictWriter(output, fieldnames=METADATA_COLUMNS)
                writer.writeheader()
                writer.writerow(row)

            value = {
                "config_version": 1,
                "dataset_root": "../data/classroom_collection",
                "metadata_csv": "../metadata/classroom_metadata.csv",
                "artifact_directory": "../artifacts/run",
                "split": {"seed": 73, "fractions": {"train": 0.7, "validation": 0.15, "test": 0.15}},
                "preprocessing": {
                    "target_sample_rate_hz": 16000, "target_duration_seconds": 1.0,
                    "channel_mix": "mean", "resampling_method": "linear",
                    "clip_strategy": "center", "normalization": "none",
                },
                "feature_extractor": {
                    "name": "librosa-mfcc-mean-std",
                    "config": {
                        "sample_rate_hz": 16000, "channel_handling": "preprocessed_mono",
                        "n_mfcc": 20, "n_mels": 40, "n_fft": 400, "win_length": 400,
                        "hop_length": 160, "window": "hann", "fmin_hz": 0.0,
                        "fmax_hz": 7600.0,
                    },
                },
            }
            config.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "source_not_approved") as raised:
                check_config_data(config)
            self.assertNotIn("metadata_missing", str(raised.exception))

    def test_non_object_configuration_has_clear_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / "config.json"
            config.write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "configuration must be a JSON object"):
                run_config(config)

    def test_all_missing_top_level_fields_are_reported_together(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / "config.json"
            config.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(
                ValueError,
                "configuration is missing required fields: config_version, dataset_root, metadata_csv",
            ):
                run_config(config)

    def test_incomplete_nested_fields_have_section_context(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / "config.json"
            value = {
                "config_version": 1,
                "dataset_root": "data",
                "metadata_csv": "metadata.csv",
                "artifact_directory": "artifacts/run",
                "split": {},
                "preprocessing": {},
                "feature_extractor": {},
            }
            config.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "split is missing required fields: seed, fractions"):
                run_config(config)


if __name__ == "__main__":
    unittest.main()
