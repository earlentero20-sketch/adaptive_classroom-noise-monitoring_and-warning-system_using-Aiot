import importlib.util
import unittest
from dataclasses import replace

from ml.baseline import (
    LogisticRegressionConfig,
    LogisticRegressionTrainer,
    run_baseline_experiment,
    run_experimental_full_fit,
)
from ml.data_pipeline import AudioFileInfo, DatasetReport, MetadataRecord, ValidatedSample
from ml.evaluation import CLASSES
from ml.training import FeatureExample


def metadata(source_type="synthetic", approval="approved", annotation="reviewed"):
    return MetadataRecord(
        "fixture-clip", "fixture.wav", CLASSES[0], "fixture-recording", "fixture-source",
        source_type, "fixture://source", "fixture-license", "fixture://license-review",
        approval, "fixture://approval-review", "", "fixture://privacy-review",
        annotation, "fixture://annotation-review",
    )


class BaselineGateTests(unittest.TestCase):
    def test_experimental_fit_requires_explicit_no_evaluation_acknowledgement(self):
        record = metadata(source_type="public")
        sample = ValidatedSample(record, AudioFileInfo(8000, 8000, 1, 2, 1.0, "NONE"), "0" * 64)
        report = DatasetReport((sample,), (), ("fixture.wav",))
        with self.assertRaisesRegex(ValueError, "explicit acknowledgement"):
            run_experimental_full_fit(
                dataset_root=".", report=report, preprocessing_config=None,
                feature_extractor=None, split_seed=1,
            )

    def test_experimental_fit_preserves_human_annotation_gate(self):
        record = metadata(source_type="public", annotation="pending")
        sample = ValidatedSample(record, AudioFileInfo(8000, 8000, 1, 2, 1.0, "NONE"), "0" * 64)
        report = DatasetReport((sample,), (), ("fixture.wav",))
        with self.assertRaisesRegex(ValueError, "annotation is not reviewed"):
            run_experimental_full_fit(
                dataset_root=".", report=report, preprocessing_config=None,
                feature_extractor=None, split_seed=1,
                acknowledge_no_held_out_evaluation=True,
            )

    def test_experimental_fit_requires_independent_groups_for_both_classes(self):
        template = metadata(source_type="public")
        records = (
            replace(template, clip_id="teacher", label=CLASSES[0], original_recording_id="teacher-group"),
            replace(template, clip_id="student", label=CLASSES[1], original_recording_id="student-group"),
        )
        samples = tuple(
            ValidatedSample(record, AudioFileInfo(8000, 8000, 1, 2, 1.0, "NONE"), "0" * 64)
            for record in records
        )
        report = DatasetReport(samples, (), ("teacher.wav", "student.wav"))
        with self.assertRaisesRegex(ValueError, "at least two independent"):
            run_experimental_full_fit(
                dataset_root=".", report=report, preprocessing_config=None,
                feature_extractor=None, split_seed=1,
                acknowledge_no_held_out_evaluation=True,
            )

    def test_real_experiment_refuses_synthetic_fixture_data(self):
        record = metadata()
        sample = ValidatedSample(record, AudioFileInfo(8000, 8000, 1, 2, 1.0, "NONE"), "0" * 64)
        report = DatasetReport((sample,), (), ("fixture.wav",))
        with self.assertRaisesRegex(ValueError, "synthetic fixtures"):
            run_baseline_experiment(
                dataset_root=".", report=report, assignments={},
                split_fractions={"train": 0.7, "validation": 0.15, "test": 0.15},
                split_seed=1, preprocessing_config=None, feature_extractor=None,
            )

    def test_real_experiment_refuses_unreviewed_annotation(self):
        record = metadata(source_type="public", annotation="ambiguous")
        sample = ValidatedSample(record, AudioFileInfo(8000, 8000, 1, 2, 1.0, "NONE"), "0" * 64)
        report = DatasetReport((sample,), (), ("fixture.wav",))
        with self.assertRaisesRegex(ValueError, "annotation is not reviewed"):
            run_baseline_experiment(
                dataset_root=".", report=report, assignments={},
                split_fractions={"train": 0.7, "validation": 0.15, "test": 0.15},
                split_seed=1, preprocessing_config=None, feature_extractor=None,
            )

    def test_real_experiment_refuses_pending_source_approval(self):
        record = metadata(source_type="public", approval="pending")
        sample = ValidatedSample(record, AudioFileInfo(8000, 8000, 1, 2, 1.0, "NONE"), "0" * 64)
        report = DatasetReport((sample,), (), ("fixture.wav",))
        with self.assertRaisesRegex(ValueError, "source is not approved"):
            run_baseline_experiment(
                dataset_root=".", report=report, assignments={},
                split_fractions={"train": 0.7, "validation": 0.15, "test": 0.15},
                split_seed=1, preprocessing_config=None, feature_extractor=None,
            )

    def test_logistic_configuration_validation(self):
        with self.assertRaises(ValueError):
            LogisticRegressionConfig(regularization_c=0)
        with self.assertRaises(ValueError):
            LogisticRegressionConfig(max_iterations=0)


class LogisticTrainerTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec("sklearn"), "approved scikit-learn is not installed")
    def test_training_scaler_is_fit_on_training_only(self):
        training = [
            FeatureExample("a", "ga", CLASSES[0], (0.0,)),
            FeatureExample("b", "gb", CLASSES[0], (0.2,)),
            FeatureExample("c", "gc", CLASSES[1], (0.8,)),
            FeatureExample("d", "gd", CLASSES[1], (1.0,)),
        ]
        validation = [FeatureExample("v", "gv", CLASSES[1], (100.0,))]
        model = LogisticRegressionTrainer(LogisticRegressionConfig()).fit(training, validation, seed=3)
        scaler = model.estimator.named_steps["standardscaler"]
        self.assertAlmostEqual(float(scaler.mean_[0]), 0.5)
        self.assertIn(model.predict((0.0,)), CLASSES)


if __name__ == "__main__":
    unittest.main()
