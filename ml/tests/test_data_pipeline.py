import csv
import json
from pathlib import Path
import tempfile
import unittest
import wave

from ml.data_pipeline import (
    METADATA_COLUMNS,
    RECORDING_LOG_COLUMNS,
    MetadataRecord,
    PreprocessingConfig,
    assert_no_group_leakage,
    build_manifest,
    discover_audio_files,
    preprocess_wav,
    split_by_source_group,
    summarize_split_readiness,
    validate_dataset,
)


CONFIG = PreprocessingConfig(8000, 0.01, "mean", "linear", "start", "none")


def write_wav(path: Path, *, rate=8000, channels=1, frames=80):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(channels)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(b"\0\0" * channels * frames)


def row(clip, relative, label="Teacher Discussion", *, group=None, approval="approved", annotation="reviewed"):
    return {
        "clip_id": clip,
        "relative_path": relative,
        "label": label,
        "original_recording_id": group or clip,
        "source_id": "fixture-source",
        "source_type": "synthetic",
        "source_reference": "fixture://source",
        "license_id": "controlled-fixture",
        "license_reference": "fixture://license-review",
        "approval_status": approval,
        "approval_reference": "fixture://approval-review",
        "consent_ref": "",
        "privacy_review_ref": "fixture://privacy-review",
        "annotation_status": annotation,
        "annotation_review_ref": "fixture://annotation-review",
    }


def metadata_record(clip, relative, label, group):
    return MetadataRecord(
        clip, relative, label, group, "source", "synthetic", "fixture://source",
        "fixture", "fixture://license-review", "approved", "fixture://approval",
        "", "", "reviewed", "fixture://annotation-review",
    )


class DatasetPipelineTests(unittest.TestCase):
    def test_header_only_metadata_is_reported_as_empty(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            metadata = root / "metadata.csv"
            self._write_csv(metadata, [])
            report = validate_dataset(root, metadata)
            self.assertFalse(report.ready_for_training)
            self.assertIn("metadata_empty", {issue.code for issue in report.issues})

    def test_accepts_variable_source_rates_durations_and_channels(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_wav(root / "a.wav", rate=8000, frames=40)
            write_wav(root / "b.wav", rate=16000, channels=2, frames=400)
            metadata = root / "metadata.csv"
            self._write_csv(metadata, [row("a", "a.wav"), row("b", "b.wav", group="b")])
            report = validate_dataset(root, metadata)
            self.assertEqual(len(report.samples), 2)
            self.assertEqual(report.samples[1].audio.channels, 2)
            processed = preprocess_wav(root / "a.wav", CONFIG)
            self.assertEqual(len(processed.samples), CONFIG.target_sample_count)
            self.assertEqual(processed.samples[-1], 0.0)

    def test_reports_missing_corrupt_unsupported_ambiguous_and_unlisted(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_wav(root / "ok.wav")
            (root / "broken.wav").write_bytes(b"not a wave")
            (root / "other.mp3").write_bytes(b"fixture only")
            write_wav(root / "orphan.wav")
            metadata = root / "metadata.csv"
            self._write_csv(metadata, [
                row("ok", "ok.wav"), row("ok", "ok.wav"),
                row("broken", "broken.wav"), row("missing", "missing.wav"),
                row("unsupported", "other.mp3"),
            ])
            report = validate_dataset(root, metadata)
            codes = {issue.code for issue in report.issues}
            self.assertTrue({"clip_id_ambiguous", "audio_path_ambiguous", "audio_corrupt",
                             "audio_missing", "unsupported_audio_format", "audio_missing_metadata"} <= codes)
            self.assertFalse(report.ready_for_training)

    def test_exact_labels_and_approval_gate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_wav(root / "pending.wav")
            metadata = root / "metadata.csv"
            self._write_csv(metadata, [row("pending", "pending.wav", label="Background Noise", approval="pending")])
            report = validate_dataset(root, metadata)
            self.assertFalse(report.samples)
            self.assertIn("metadata_invalid", {issue.code for issue in report.issues})

    def test_ambiguous_annotation_is_reported_and_never_opened(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_wav(root / "mixed.wav")
            metadata = root / "metadata.csv"
            self._write_csv(metadata, [row("mixed", "mixed.wav", annotation="ambiguous")])
            report = validate_dataset(root, metadata)
            self.assertFalse(report.samples)
            self.assertIn("label_ambiguous", {issue.code for issue in report.issues})

    def test_unapproved_source_is_reported_and_never_opened(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_wav(root / "pending.wav")
            metadata = root / "metadata.csv"
            self._write_csv(metadata, [row("pending", "pending.wav", approval="pending")])
            report = validate_dataset(root, metadata)
            self.assertFalse(report.samples)
            self.assertIn("source_not_approved", {issue.code for issue in report.issues})

    def test_manifest_is_reproducible_and_omits_consent_reference(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_wav(root / "a.wav")
            metadata = root / "metadata.csv"
            record = row("a", "a.wav")
            record["consent_ref"] = "private-reference"
            self._write_csv(metadata, [record])
            report = validate_dataset(root, metadata)
            first = build_manifest(report, CONFIG)
            second = build_manifest(report, CONFIG)
            self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))
            self.assertNotIn("private-reference", json.dumps(first))
            self.assertFalse(first["ready_for_training"])

    def test_empty_classroom_references_are_allowed_but_pending_reviews_block(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_wav(root / "clip.wav")
            record = self._classroom_row("clip", "clip.wav")
            for field in ("source_reference", "license_id", "license_reference", "approval_reference",
                          "consent_ref", "privacy_review_ref", "annotation_review_ref"):
                record[field] = ""
            self._write_csv(root / "metadata.csv", [record])
            self._write_recording_log(root, "fixture-source", "clip", quality="pass", annotation="reviewed")

            report = validate_dataset(root, root / "metadata.csv")
            codes = {issue.code for issue in report.issues}
            self.assertFalse(report.samples)
            self.assertNotIn("metadata_invalid", codes)
            self.assertIn("review_reference_missing", codes)
            self.assertFalse(report.ready_for_training)

    def test_pending_annotation_and_quality_statuses_block_classroom_audio(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_wav(root / "clip.wav")
            record = self._classroom_row("clip", "clip.wav")
            self._write_csv(root / "metadata.csv", [record])
            self._write_recording_log(root, "fixture-source", "clip", quality="pending", annotation="pending")

            report = validate_dataset(root, root / "metadata.csv")
            codes = {issue.code for issue in report.issues}
            self.assertFalse(report.samples)
            self.assertIn("quality_review_incomplete", codes)
            self.assertFalse(report.ready_for_training)

            self._write_recording_log(root, "fixture-source", "clip", quality="pass", annotation="pending")
            report = validate_dataset(root, root / "metadata.csv")
            self.assertIn("recording_annotation_review_incomplete", {issue.code for issue in report.issues})
            self.assertFalse(report.ready_for_training)

            record["annotation_status"] = "pending"
            self._write_csv(root / "metadata.csv", [record])
            self._write_recording_log(root, "fixture-source", "clip", quality="pass", annotation="reviewed")
            report = validate_dataset(root, root / "metadata.csv")
            self.assertIn("annotation_not_approved", {issue.code for issue in report.issues})
            self.assertFalse(report.ready_for_training)

    def test_missing_consent_reference_blocks_otherwise_reviewed_classroom_audio(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_wav(root / "clip.wav")
            record = self._classroom_row("clip", "clip.wav")
            record["consent_ref"] = ""
            self._write_csv(root / "metadata.csv", [record])
            self._write_recording_log(root, "fixture-source", "clip", quality="pass", annotation="reviewed")

            report = validate_dataset(root, root / "metadata.csv")
            self.assertFalse(report.samples)
            issue = next(issue for issue in report.issues if issue.code == "review_reference_missing")
            self.assertIn("consent_ref", issue.message)
            self.assertFalse(report.ready_for_training)

    def test_placeholder_words_are_not_accepted_as_reference_ids(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_wav(root / "clip.wav")
            record = row("clip", "clip.wav")
            record["source_reference"] = "pending"
            self._write_csv(root / "metadata.csv", [record])
            report = validate_dataset(root, root / "metadata.csv")
            self.assertFalse(report.samples)
            self.assertIn("review_reference_missing", {issue.code for issue in report.issues})

    def test_four_original_groups_are_not_training_ready(self):
        records = [
            metadata_record("t1", "t1.wav", "Teacher Discussion", "original-1"),
            metadata_record("t2", "t2.wav", "Teacher Discussion", "original-2"),
            metadata_record("s1", "s1.wav", "Student Conversation", "original-3"),
            metadata_record("s2", "s2.wav", "Student Conversation", "original-4"),
        ]
        assignments = split_by_source_group(
            records, fractions={"train": 0.6, "validation": 0.2, "test": 0.2}, seed=14
        )
        summary = summarize_split_readiness(records, assignments)
        self.assertTrue(all(not item["ready_for_baseline"] for item in summary.values()))

    @staticmethod
    def _classroom_row(clip, relative):
        record = row(clip, relative)
        record.update({
            "source_type": "classroom",
            "source_reference": "fixture-protocol",
            "license_id": "school-approved-use",
            "license_reference": "fixture-terms-review",
            "approval_reference": "fixture-permission-review",
            "consent_ref": "fixture-consent-review",
            "privacy_review_ref": "fixture-privacy-review",
            "annotation_review_ref": "fixture-annotation-review",
        })
        return record

    @staticmethod
    def _write_recording_log(root, source_id, original_id, *, quality, annotation):
        values = {column: "" for column in RECORDING_LOG_COLUMNS}
        values.update({
            "source_id": source_id,
            "original_recording_id": original_id,
            "quality_review_status": quality,
            "quality_review_ref": "fixture-quality-review" if quality == "pass" else "",
            "annotation_status": annotation,
            "annotation_review_ref": "fixture-recording-annotation" if annotation == "reviewed" else "",
        })
        with (root / "recording_log.csv").open("w", newline="", encoding="utf-8") as output:
            writer = csv.DictWriter(output, fieldnames=RECORDING_LOG_COLUMNS)
            writer.writeheader()
            writer.writerow(values)

    @staticmethod
    def _write_csv(path, rows):
        with path.open("w", newline="", encoding="utf-8") as output:
            writer = csv.DictWriter(output, fieldnames=METADATA_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)


class GroupSplitTests(unittest.TestCase):
    def test_group_split_is_deterministic_and_leakage_free(self):
        records = [metadata_record(str(i), f"{i}.wav", "Teacher Discussion", f"r{i}")
                   for i in range(12)]
        fractions = {"train": 0.6, "validation": 0.2, "test": 0.2}
        first = split_by_source_group(records, fractions=fractions, seed=14)
        self.assertEqual(first, split_by_source_group(records, fractions=fractions, seed=14))
        assert_no_group_leakage(records, first)
        self.assertEqual(set(first.values()), {"train", "validation", "test"})

    def test_related_clips_stay_together_and_invalid_splits_fail(self):
        records = [metadata_record(str(i), f"{i}.wav", "Student Conversation", "same" if i < 2 else str(i))
                   for i in range(5)]
        result = split_by_source_group(records, fractions={"train": 0.6, "validation": 0.2, "test": 0.2}, seed=2)
        self.assertEqual(result["0"], result["1"])
        with self.assertRaises(ValueError):
            assert_no_group_leakage(records, {"0": "train", "1": "test", "2": "train", "3": "validation", "4": "test"})

    def test_readiness_summary_flags_missing_classes_and_low_group_coverage(self):
        records = [
            metadata_record("t1", "t1.wav", "Teacher Discussion", "g1"),
            metadata_record("t2", "t2.wav", "Teacher Discussion", "g2"),
            metadata_record("s1", "s1.wav", "Student Conversation", "g3"),
            metadata_record("s2", "s2.wav", "Student Conversation", "g4"),
            metadata_record("t3", "t3.wav", "Teacher Discussion", "g5"),
            metadata_record("s3", "s3.wav", "Student Conversation", "g6"),
            metadata_record("t4", "t4.wav", "Teacher Discussion", "g7"),
            metadata_record("s4", "s4.wav", "Student Conversation", "g8"),
        ]
        assignments = {"t1": "train", "t2": "train", "s1": "validation",
                       "s2": "validation", "t3": "test", "s3": "test",
                       "t4": "test", "s4": "test"}
        summary = summarize_split_readiness(records, assignments)
        self.assertEqual(summary["train"]["missing_classes"], ["Student Conversation"])
        self.assertFalse(summary["train"]["ready_for_baseline"])
        self.assertFalse(summary["validation"]["ready_for_baseline"])
        self.assertTrue(summary["test"]["ready_for_baseline"])

    def test_preprocessing_configuration_rejects_invalid_settings(self):
        with self.assertRaises(ValueError):
            PreprocessingConfig(0, 1, "mean", "linear", "start", "none")
        with self.assertRaises(ValueError):
            PreprocessingConfig(8000, float("nan"), "mean", "linear", "start", "none")


if __name__ == "__main__":
    unittest.main()
