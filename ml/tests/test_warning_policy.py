import math
import unittest

from ml.warning_policy import evaluate_warning


class EvaluateWarningTests(unittest.TestCase):
    def test_student_conversation_above_configured_threshold_warns(self):
        decision = evaluate_warning(
            classification="Student Conversation",
            classification_is_confident=True,
            sound_level_db=71.0,
            threshold_db=70.0,
            level_is_calibrated=True,
        )
        self.assertTrue(decision.should_warn)

    def test_student_conversation_at_threshold_does_not_warn(self):
        decision = evaluate_warning(
            classification="Student Conversation",
            classification_is_confident=True,
            sound_level_db=70.0,
            threshold_db=70.0,
            level_is_calibrated=True,
        )
        self.assertFalse(decision.should_warn)
        self.assertEqual(decision.reason, "below_threshold")

    def test_ordinary_student_conversation_below_threshold_does_not_warn(self):
        decision = evaluate_warning(
            classification="Student Conversation",
            classification_is_confident=True,
            sound_level_db=55.0,
            threshold_db=70.0,
            level_is_calibrated=True,
        )
        self.assertFalse(decision.should_warn)
        self.assertEqual(decision.reason, "below_threshold")

    def test_teacher_discussion_never_triggers_this_warning(self):
        decision = evaluate_warning(
            classification="Teacher Discussion",
            classification_is_confident=True,
            sound_level_db=85.0,
            threshold_db=70.0,
            level_is_calibrated=True,
        )
        self.assertFalse(decision.should_warn)
        self.assertEqual(decision.reason, "teacher_discussion")

    def test_missing_or_uncalibrated_measurement_fails_closed(self):
        for level, calibrated in ((None, True), (80.0, False)):
            with self.subTest(level=level, calibrated=calibrated):
                decision = evaluate_warning(
                    classification="Student Conversation",
                    classification_is_confident=True,
                    sound_level_db=level,
                    threshold_db=70.0,
                    level_is_calibrated=calibrated,
                )
                self.assertFalse(decision.should_warn)

    def test_missing_threshold_fails_closed(self):
        decision = evaluate_warning(
            classification="Student Conversation",
            classification_is_confident=True,
            sound_level_db=80.0,
            threshold_db=None,
            level_is_calibrated=True,
        )
        self.assertFalse(decision.should_warn)
        self.assertEqual(decision.reason, "threshold_unconfigured")

    def test_unknown_or_unavailable_classification_fails_closed(self):
        for classification in (None, "Uncertain", "Background Noise"):
            with self.subTest(classification=classification):
                decision = evaluate_warning(
                    classification=classification,
                    classification_is_confident=True,
                    sound_level_db=80.0,
                    threshold_db=70.0,
                    level_is_calibrated=True,
                )
                self.assertFalse(decision.should_warn)

    def test_non_finite_values_fail_closed(self):
        for level, threshold in (
            (math.nan, 70.0),
            (math.inf, 70.0),
            (80.0, math.nan),
            (80.0, math.inf),
        ):
            with self.subTest(level=level, threshold=threshold):
                decision = evaluate_warning(
                    classification="Student Conversation",
                    classification_is_confident=True,
                    sound_level_db=level,
                    threshold_db=threshold,
                    level_is_calibrated=True,
                )
                self.assertFalse(decision.should_warn)

    def test_non_numeric_measurements_fail_closed(self):
        for level, threshold in (("80", 70.0), (80.0, "70"), (True, 70.0)):
            with self.subTest(level=level, threshold=threshold):
                decision = evaluate_warning(
                    classification="Student Conversation",
                    classification_is_confident=True,
                    sound_level_db=level,
                    threshold_db=threshold,
                    level_is_calibrated=True,
                )
                self.assertFalse(decision.should_warn)

    def test_calibration_flag_must_be_boolean_true(self):
        decision = evaluate_warning(
            classification="Student Conversation",
            classification_is_confident=True,
            sound_level_db=80.0,
            threshold_db=70.0,
            level_is_calibrated="yes",
        )
        self.assertFalse(decision.should_warn)
        self.assertEqual(decision.reason, "sound_level_uncalibrated")

    def test_uncertain_classification_does_not_warn(self):
        decision = evaluate_warning(
            classification="Student Conversation",
            classification_is_confident=False,
            sound_level_db=85.0,
            threshold_db=70.0,
            level_is_calibrated=True,
        )
        self.assertFalse(decision.should_warn)
        self.assertEqual(decision.reason, "classification_uncertain")


if __name__ == "__main__":
    unittest.main()
