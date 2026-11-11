import unittest

from ml.evaluation import CLASSES, evaluate_predictions


class EvaluatePredictionsTests(unittest.TestCase):
    def test_perfect_predictions_have_perfect_metrics(self):
        report = evaluate_predictions(
            [CLASSES[0], CLASSES[1]], [CLASSES[0], CLASSES[1]]
        )
        self.assertEqual(report.accuracy, 1.0)
        self.assertEqual(report.macro_f1, 1.0)
        for metrics in report.class_metrics.values():
            self.assertEqual(metrics.precision, 1.0)
            self.assertEqual(metrics.recall, 1.0)
            self.assertEqual(metrics.f1_score, 1.0)

    def test_confusion_matrix_and_per_class_metrics(self):
        report = evaluate_predictions(
            [CLASSES[0], CLASSES[0], CLASSES[1], CLASSES[1]],
            [CLASSES[0], CLASSES[1], CLASSES[0], CLASSES[1]],
        )
        self.assertEqual(report.confusion_matrix[CLASSES[0]], {
            CLASSES[0]: 1,
            CLASSES[1]: 1,
        })
        self.assertEqual(report.confusion_matrix[CLASSES[1]], {
            CLASSES[0]: 1,
            CLASSES[1]: 1,
        })
        self.assertEqual(report.class_metrics[CLASSES[0]].precision, 0.5)
        self.assertEqual(report.class_metrics[CLASSES[0]].recall, 0.5)
        self.assertEqual(report.class_metrics[CLASSES[1]].f1_score, 0.5)
        self.assertEqual(report.macro_f1, 0.5)

    def test_absent_predictions_and_class_are_zero_not_division_error(self):
        report = evaluate_predictions([CLASSES[0]], [CLASSES[1]])
        self.assertEqual(report.class_metrics[CLASSES[0]].recall, 0.0)
        self.assertEqual(report.class_metrics[CLASSES[1]].precision, 0.0)
        self.assertEqual(report.macro_f1, 0.0)

    def test_rejects_empty_or_length_mismatched_inputs(self):
        with self.assertRaises(ValueError):
            evaluate_predictions([], [])
        with self.assertRaises(ValueError):
            evaluate_predictions([CLASSES[0]], [])

    def test_rejects_labels_outside_the_two_class_scope(self):
        with self.assertRaises(ValueError):
            evaluate_predictions(["Uncertain"], [CLASSES[0]])


if __name__ == "__main__":
    unittest.main()
