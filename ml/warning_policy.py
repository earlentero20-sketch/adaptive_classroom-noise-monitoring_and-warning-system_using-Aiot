"""Provisional software policy for the excessive student-noise warning.

This module does not measure sound, classify audio, control a buzzer, or define
the team's real-world threshold. It consumes those values from a future agreed
interface and fails closed when required information is missing.
"""

from dataclasses import dataclass
import math
from numbers import Real


TEACHER_DISCUSSION = "Teacher Discussion"
STUDENT_CONVERSATION = "Student Conversation"


@dataclass(frozen=True)
class WarningDecision:
    should_warn: bool
    reason: str


def evaluate_warning(
    *,
    classification: str | None,
    classification_is_confident: bool,
    sound_level_db: Real | None,
    threshold_db: Real | None,
    level_is_calibrated: bool,
) -> WarningDecision:
    """Evaluate one window; missing or invalid safety inputs fail closed.

    Duration, hysteresis, cooldown, and physical buzzer behavior are not
    implemented because the team has not specified them.
    """
    if classification is None:
        return WarningDecision(False, "classification_unavailable")
    if classification not in (TEACHER_DISCUSSION, STUDENT_CONVERSATION):
        return WarningDecision(False, "classification_unknown")
    if classification == TEACHER_DISCUSSION:
        return WarningDecision(False, "teacher_discussion")
    if classification_is_confident is not True:
        return WarningDecision(False, "classification_uncertain")
    if level_is_calibrated is not True:
        return WarningDecision(False, "sound_level_uncalibrated")
    if sound_level_db is None:
        return WarningDecision(False, "sound_level_unavailable")
    if not _is_finite_number(sound_level_db):
        return WarningDecision(False, "sound_level_invalid")
    if threshold_db is None:
        return WarningDecision(False, "threshold_unconfigured")
    if not _is_finite_number(threshold_db):
        return WarningDecision(False, "threshold_invalid")
    if sound_level_db <= threshold_db:
        return WarningDecision(False, "below_threshold")
    return WarningDecision(True, "student_conversation_above_threshold")


def _is_finite_number(value: object) -> bool:
    """Reject booleans and non-numeric values before comparing measurements."""
    if not isinstance(value, Real) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except (OverflowError, TypeError, ValueError):
        return False
