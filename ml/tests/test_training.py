import unittest

from ml.evaluation import CLASSES
from ml.inference import classification_result
from ml.training import FeatureExample, evaluate_held_out, fit_model


class NearestFixture:
    def fit(self, training, validation, *, seed):
        return FixtureClassifier()


class FixtureClassifier:
    def predict(self, features):
        return CLASSES[0] if features[0] < 0.5 else CLASSES[1]


class FixedClassifier:
    def predict(self, features):
        return CLASSES[0]


class TrainingInterfaceTests(unittest.TestCase):
    def setUp(self):
        self.training = [
            FeatureExample("a", "group-a", CLASSES[0], (0.0,)),
            FeatureExample("b", "group-b", CLASSES[1], (1.0,)),
        ]
        self.validation = [FeatureExample("c", "group-c", CLASSES[0], (0.1,))]
        self.testing = [
            FeatureExample("d", "group-d", CLASSES[0], (0.0,)),
            FeatureExample("e", "group-e", CLASSES[1], (1.0,)),
        ]

    def test_train_then_evaluate_uses_existing_metrics(self):
        run = fit_model(NearestFixture(), self.training, self.validation, seed=4)
        report = evaluate_held_out(run, self.testing)
        self.assertEqual(report.sample_count, 2)
        self.assertEqual(report.macro_f1, 1.0)
        self.assertEqual(report.confusion_matrix[CLASSES[0]][CLASSES[0]], 1)

    def test_training_validation_and_test_groups_must_be_disjoint(self):
        with self.assertRaisesRegex(ValueError, "training and validation"):
            fit_model(NearestFixture(), self.training,
                      [FeatureExample("c", "group-a", CLASSES[0], (0.0,))], seed=4)
        run = fit_model(NearestFixture(), self.training, self.validation, seed=4)
        with self.assertRaisesRegex(ValueError, "test source groups"):
            evaluate_held_out(run, [FeatureExample("d", "group-a", CLASSES[0], (0.0,))])

    def test_training_rejects_missing_class_and_invalid_features(self):
        with self.assertRaisesRegex(ValueError, "both approved classes"):
            fit_model(NearestFixture(), self.training[:1], self.validation, seed=1)
        with self.assertRaisesRegex(ValueError, "finite"):
            fit_model(NearestFixture(), [self.training[0], FeatureExample("z", "group-z", CLASSES[1], (float("nan"),))], self.validation, seed=1)

    def test_contract_adapter_keeps_confidence_false_by_default(self):
        result = classification_result(FixedClassifier(), (0.0,), observed_at="2026-10-11T12:00:00Z")
        self.assertEqual(set(result), {"label", "confident", "observed_at"})
        self.assertEqual(result["label"], CLASSES[0])
        self.assertIs(result["confident"], False)
        with self.assertRaisesRegex(ValueError, "include a timezone"):
            classification_result(FixedClassifier(), (0.0,), observed_at="2026-10-11T12:00:00")


if __name__ == "__main__":
    unittest.main()
