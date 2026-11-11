"""Dependency-free dataset validation and deterministic WAV preprocessing.

This module does not acquire or authorize datasets. Metadata must affirm that
use has been reviewed before approved audio is opened or hashed.
"""

from dataclasses import asdict, dataclass
import csv
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path
import struct
from typing import Any, Mapping, Sequence
import wave

from ml.evaluation import CLASSES


METADATA_COLUMNS = (
    "clip_id",
    "relative_path",
    "label",
    "original_recording_id",
    "source_id",
    "source_type",
    "source_reference",
    "license_id",
    "license_reference",
    "approval_status",
    "approval_reference",
    "consent_ref",
    "privacy_review_ref",
    "annotation_status",
    "annotation_review_ref",
)
RECORDING_LOG_COLUMNS = (
    "source_id", "original_recording_id", "secure_record_ref", "recording_setup_ref",
    "session_code", "room_code", "microphone_model", "recorder_model",
    "microphone_placement_code", "container", "encoding", "sample_rate_hz",
    "bit_depth", "channel_count", "gain_setting", "original_duration_seconds",
    "teacher_discussion_present", "student_conversation_present",
    "ambiguous_intervals_present", "quality_review_status", "quality_review_ref",
    "annotation_status", "annotation_review_ref", "non_identifying_notes",
)
_REFERENCE_PLACEHOLDERS = frozenset(("pending", "unknown", "tbd", "n/a", "not applicable"))
SOURCE_TYPES = frozenset(("public", "classroom", "synthetic"))
SUPPORTED_AUDIO_SUFFIXES = frozenset((".wav",))
DISCOVERABLE_AUDIO_SUFFIXES = frozenset((
    ".wav", ".flac", ".mp3", ".ogg", ".opus", ".m4a", ".aac", ".aiff", ".wma",
))


@dataclass(frozen=True)
class PreprocessingConfig:
    """All waveform-changing choices are explicit and serialized in manifests."""

    target_sample_rate_hz: int
    target_duration_seconds: float
    channel_mix: str
    resampling_method: str
    clip_strategy: str
    normalization: str

    def __post_init__(self) -> None:
        if type(self.target_sample_rate_hz) is not int or self.target_sample_rate_hz <= 0:
            raise ValueError("target_sample_rate_hz must be a positive integer")
        if (
            isinstance(self.target_duration_seconds, bool)
            or not isinstance(self.target_duration_seconds, (int, float))
            or not math.isfinite(self.target_duration_seconds)
            or self.target_duration_seconds <= 0
        ):
            raise ValueError("target_duration_seconds must be finite and positive")
        if self.channel_mix not in ("mean", "first"):
            raise ValueError("channel_mix must be 'mean' or 'first'")
        if self.resampling_method != "linear":
            raise ValueError("resampling_method must be 'linear'")
        if self.clip_strategy not in ("start", "center"):
            raise ValueError("clip_strategy must be 'start' or 'center'")
        if self.normalization not in ("none", "peak"):
            raise ValueError("normalization must be 'none' or 'peak'")
        if self.target_sample_count <= 0:
            raise ValueError("configuration must produce at least one target sample")

    @property
    def target_sample_count(self) -> int:
        return round(self.target_sample_rate_hz * self.target_duration_seconds)


@dataclass(frozen=True)
class MetadataRecord:
    clip_id: str
    relative_path: str
    label: str
    original_recording_id: str
    source_id: str
    source_type: str
    source_reference: str
    license_id: str
    license_reference: str
    approval_status: str
    approval_reference: str
    consent_ref: str
    privacy_review_ref: str
    annotation_status: str
    annotation_review_ref: str

    @property
    def group_key(self) -> tuple[str, str]:
        """Namespace recording IDs by source to prevent cross-source collisions."""
        return self.source_id, self.original_recording_id


@dataclass(frozen=True)
class AudioFileInfo:
    sample_rate_hz: int
    frame_count: int
    channels: int
    sample_width_bytes: int
    duration_seconds: float
    encoding: str


@dataclass(frozen=True)
class ValidatedSample:
    metadata: MetadataRecord
    audio: AudioFileInfo
    sha256: str


@dataclass(frozen=True)
class DatasetIssue:
    code: str
    message: str
    relative_path: str = ""
    clip_id: str = ""


@dataclass(frozen=True)
class DatasetReport:
    samples: tuple[ValidatedSample, ...]
    issues: tuple[DatasetIssue, ...]
    discovered_audio_paths: tuple[str, ...]

    @property
    def ready_for_training(self) -> bool:
        return bool(self.samples) and not self.issues


@dataclass(frozen=True)
class PreprocessedAudio:
    samples: tuple[float, ...]
    sample_rate_hz: int
    source_info: AudioFileInfo
    config: PreprocessingConfig


def validate_audio_file(path: str | Path) -> AudioFileInfo:
    """Validate a complete uncompressed PCM WAV without loading it all at once."""
    audio_path = Path(path)
    if audio_path.suffix.lower() not in SUPPORTED_AUDIO_SUFFIXES:
        raise ValueError("unsupported audio format; only PCM WAV is currently supported")
    try:
        with wave.open(str(audio_path), "rb") as source:
            return _validate_wave_reader(source)
    except (wave.Error, EOFError, OSError) as error:
        raise ValueError(f"corrupt or unreadable WAV: {error}") from error


def validate_audio_bytes(payload: bytes) -> AudioFileInfo:
    """Validate a complete PCM WAV held in memory, without writing it to disk."""
    if not isinstance(payload, bytes) or not payload:
        raise ValueError("audio sample must be non-empty WAV bytes")
    try:
        with wave.open(BytesIO(payload), "rb") as source:
            return _validate_wave_reader(source)
    except (wave.Error, EOFError, OSError) as error:
        raise ValueError(f"corrupt or unreadable WAV: {error}") from error


def _validate_wave_reader(source: wave.Wave_read) -> AudioFileInfo:
    channels = source.getnchannels()
    sample_rate = source.getframerate()
    frames = source.getnframes()
    width = source.getsampwidth()
    encoding = source.getcomptype()
    if encoding != "NONE":
        raise ValueError(f"unsupported WAV encoding: {encoding}")
    if channels <= 0 or sample_rate <= 0 or frames <= 0:
        raise ValueError("audio must have positive channels, sample rate, and frame count")
    if width not in (1, 2, 3, 4):
        raise ValueError(f"unsupported PCM sample width: {width} bytes")
    block_size = channels * width
    remaining = frames
    while remaining:
        chunk = source.readframes(min(remaining, 8192))
        if not chunk:
            raise ValueError("WAV data is truncated before its declared frame count")
        if len(chunk) % block_size:
            raise ValueError("WAV data ends with an incomplete sample frame")
        remaining -= len(chunk) // block_size
        if remaining < 0:
            raise ValueError("WAV data exceeds its declared frame count")
    return AudioFileInfo(sample_rate, frames, channels, width, frames / sample_rate, encoding)


def discover_audio_files(root: str | Path) -> tuple[str, ...]:
    """List recognized audio suffixes in stable relative-path order."""
    dataset_root = Path(root).resolve()
    if not dataset_root.is_dir():
        return ()
    return tuple(sorted(
        path.relative_to(dataset_root).as_posix()
        for path in dataset_root.rglob("*")
        if path.is_file() and path.suffix.lower() in DISCOVERABLE_AUDIO_SUFFIXES
    ))


def validate_dataset(root: str | Path, metadata_csv: str | Path) -> DatasetReport:
    """Validate privacy-safe metadata and referenced audio without auto-using it.

    Only rows with approved source review and completed annotation review are
    opened or hashed. The CSV's status and references are intake gates, not
    proof that the cited license, permissions, consent, or privacy review is
    genuine or sufficient. Those require human verification.
    """
    dataset_root = Path(root).resolve()
    issues: list[DatasetIssue] = []
    samples: list[ValidatedSample] = []
    discovered = discover_audio_files(dataset_root)
    if not dataset_root.is_dir():
        return DatasetReport((), (DatasetIssue("dataset_root_missing", "dataset root does not exist"),), ())

    csv_path = Path(metadata_csv)
    if not csv_path.is_absolute():
        csv_path = dataset_root / csv_path
    if not csv_path.is_file():
        return DatasetReport((), (DatasetIssue("metadata_missing", "metadata CSV does not exist"),), discovered)

    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            headers = set(reader.fieldnames or ())
            missing_columns = sorted(set(METADATA_COLUMNS) - headers)
            if missing_columns:
                issues.append(DatasetIssue(
                    "metadata_columns_missing",
                    "required metadata columns are missing: " + ", ".join(missing_columns),
                ))
                return DatasetReport((), tuple(issues), discovered)
            rows = list(reader)
    except (OSError, UnicodeError, csv.Error) as error:
        return DatasetReport((), (DatasetIssue("metadata_unreadable", str(error)),), discovered)

    if not rows:
        return DatasetReport(
            (), (DatasetIssue("metadata_empty", "metadata CSV has a header but no clip rows"),), discovered
        )

    parsed: list[tuple[int, MetadataRecord | None, Path | None, str]] = []
    clip_ids: dict[str, list[int]] = {}
    paths: dict[str, list[int]] = {}
    for row_number, row in enumerate(rows, start=2):
        values = {key: (row.get(key) or "").strip() for key in METADATA_COLUMNS}
        clip_id = values["clip_id"]
        relative_path = values["relative_path"].replace("\\", "/")
        row_errors: list[str] = []
        for field in ("clip_id", "relative_path", "label", "original_recording_id", "source_id", "source_type",
                      "approval_status", "annotation_status"):
            if not values[field]:
                row_errors.append(f"{field} is missing")
        if values["label"] not in CLASSES:
            row_errors.append("label is not one of the two approved classes")
        if values["source_type"] not in SOURCE_TYPES:
            row_errors.append("source_type must be public, classroom, or synthetic")
        if values["approval_status"] not in ("approved", "pending", "rejected"):
            row_errors.append("approval_status must be approved, pending, or rejected")
        if values["annotation_status"] not in ("reviewed", "ambiguous", "pending", "rejected"):
            row_errors.append("annotation_status must be reviewed, ambiguous, pending, or rejected")
        resolved_path: Path | None = None
        if relative_path:
            relative_candidate = Path(relative_path)
            if relative_candidate.is_absolute() or ".." in relative_candidate.parts:
                row_errors.append("relative_path must stay inside the dataset root")
            else:
                resolved_path = (dataset_root / relative_candidate).resolve()
                if dataset_root not in resolved_path.parents:
                    row_errors.append("relative_path resolves outside the dataset root")
                else:
                    paths.setdefault(relative_candidate.as_posix().casefold(), []).append(row_number)
        if clip_id:
            clip_ids.setdefault(clip_id, []).append(row_number)

        record = None
        if not row_errors:
            record = MetadataRecord(**values)
        parsed.append((row_number, record, resolved_path, "; ".join(row_errors)))

    duplicate_clip_rows = {number for numbers in clip_ids.values() if len(numbers) > 1 for number in numbers}
    duplicate_path_rows = {number for numbers in paths.values() if len(numbers) > 1 for number in numbers}
    referenced = set(paths)
    for relative in discovered:
        key = relative.casefold()
        suffix = Path(relative).suffix.lower()
        if suffix not in SUPPORTED_AUDIO_SUFFIXES:
            issues.append(DatasetIssue("unsupported_audio_format", "audio suffix is not supported yet", relative))
        if suffix in SUPPORTED_AUDIO_SUFFIXES and key not in referenced:
            issues.append(DatasetIssue("audio_missing_metadata", "audio file has no metadata row", relative))

    has_classroom_rows = any(record and record.source_type == "classroom" for _, record, _, _ in parsed)
    if has_classroom_rows:
        classroom_logs, log_issues = _load_classroom_recording_log(dataset_root, csv_path)
        issues.extend(log_issues)
    else:
        classroom_logs = {}

    for row_number, record, audio_path, row_error in parsed:
        relative = record.relative_path if record else rows[row_number - 2].get("relative_path", "").strip()
        clip_id = record.clip_id if record else rows[row_number - 2].get("clip_id", "").strip()
        if row_error:
            issues.append(DatasetIssue("metadata_invalid", f"row {row_number}: {row_error}", relative, clip_id))
            continue
        assert record is not None
        ambiguous = False
        if row_number in duplicate_clip_rows:
            issues.append(DatasetIssue("clip_id_ambiguous", "clip_id occurs more than once", relative, clip_id))
            ambiguous = True
        if row_number in duplicate_path_rows:
            issues.append(DatasetIssue("audio_path_ambiguous", "audio path is assigned to multiple metadata rows", relative, clip_id))
            ambiguous = True
        if ambiguous:
            continue
        if record.approval_status != "approved":
            issues.append(DatasetIssue("source_not_approved", "source use has not been approved; audio was not opened", relative, clip_id))
            continue
        if record.annotation_status == "ambiguous":
            issues.append(DatasetIssue("label_ambiguous", "ambiguous annotation is held for human review; audio was not opened", relative, clip_id))
            continue
        if record.annotation_status != "reviewed":
            issues.append(DatasetIssue("annotation_not_approved", "annotation review is incomplete; audio was not opened", relative, clip_id))
            continue
        missing_references = []
        for field in ("source_reference", "license_id", "license_reference"):
            if not _has_reference(getattr(record, field)):
                missing_references.append(field)
        if record.approval_status == "approved" and not _has_reference(record.approval_reference):
            missing_references.append("approval_reference")
        if record.annotation_status == "reviewed" and not _has_reference(record.annotation_review_ref):
            missing_references.append("annotation_review_ref")
        if record.source_type == "classroom":
            for field in ("consent_ref", "privacy_review_ref"):
                if not _has_reference(getattr(record, field)):
                    missing_references.append(field)
            log_key = record.group_key
            log = classroom_logs.get(log_key)
            if log is None:
                issues.append(DatasetIssue("recording_log_missing", "classroom recording has no matching recording-log row", relative, clip_id))
                continue
            if log["quality_review_status"] != "pass" or not _has_reference(log["quality_review_ref"]):
                issues.append(DatasetIssue("quality_review_incomplete", "classroom audio requires a passed quality review with a real reference", relative, clip_id))
                continue
            if log["annotation_status"] != "reviewed" or not _has_reference(log["annotation_review_ref"]):
                issues.append(DatasetIssue("recording_annotation_review_incomplete", "recording-log annotation review is incomplete", relative, clip_id))
                continue
        if missing_references:
            issues.append(DatasetIssue(
                "review_reference_missing",
                "required review/provenance references are empty or placeholders: " + ", ".join(missing_references),
                relative, clip_id,
            ))
            continue
        if audio_path is None or not audio_path.is_file():
            issues.append(DatasetIssue("audio_missing", "referenced audio file does not exist", relative, clip_id))
            continue
        if audio_path.suffix.lower() not in SUPPORTED_AUDIO_SUFFIXES:
            issues.append(DatasetIssue("unsupported_audio_format", "only PCM WAV is currently supported", relative, clip_id))
            continue
        try:
            audio_info = validate_audio_file(audio_path)
            checksum = _sha256_file(audio_path)
        except (OSError, ValueError) as error:
            issues.append(DatasetIssue("audio_corrupt", str(error), relative, clip_id))
            continue
        samples.append(ValidatedSample(record, audio_info, checksum))

    issues.sort(key=lambda issue: (issue.relative_path.casefold(), issue.clip_id, issue.code, issue.message))
    samples.sort(key=lambda sample: (sample.metadata.clip_id, sample.metadata.relative_path))
    return DatasetReport(tuple(samples), tuple(issues), discovered)


def _has_reference(value: str) -> bool:
    """A status or placeholder is not evidence that a review record exists."""
    normalized = value.strip().casefold()
    return bool(normalized) and normalized not in _REFERENCE_PLACEHOLDERS and not (
        normalized.startswith("<") and normalized.endswith(">")
    )


def _load_classroom_recording_log(
    dataset_root: Path, metadata_path: Path
) -> tuple[dict[tuple[str, str], dict[str, str]], list[DatasetIssue]]:
    """Read the existing log schema; missing review data remains a blocking issue."""
    candidates = (
        dataset_root / "recording_log.csv",
        metadata_path.with_name("recording_log.csv"),
        metadata_path.with_name("classroom_recording_log.csv"),
    )
    log_path = next((path for path in candidates if path.is_file()), None)
    if log_path is None:
        return {}, []
    issues: list[DatasetIssue] = []
    logs: dict[tuple[str, str], dict[str, str]] = {}
    duplicate_keys: set[tuple[str, str]] = set()
    try:
        with log_path.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            missing = sorted(set(RECORDING_LOG_COLUMNS) - set(reader.fieldnames or ()))
            if missing:
                return {}, [DatasetIssue("recording_log_columns_missing", "recording-log columns are missing: " + ", ".join(missing))]
            for line, row in enumerate(reader, start=2):
                values = {key: (row.get(key) or "").strip() for key in RECORDING_LOG_COLUMNS}
                key = (values["source_id"], values["original_recording_id"])
                if not all(key):
                    issues.append(DatasetIssue("recording_log_group_missing", f"recording-log row {line} has no source/recording group ID"))
                    continue
                if key in logs or key in duplicate_keys:
                    issues.append(DatasetIssue("recording_log_group_ambiguous", "recording-log group occurs more than once"))
                    logs.pop(key)
                    duplicate_keys.add(key)
                    continue
                logs[key] = values
    except (OSError, UnicodeError, csv.Error) as error:
        return {}, [DatasetIssue("recording_log_unreadable", str(error))]
    return logs, issues


def group_id(record: MetadataRecord) -> str:
    """Stable namespaced group identity derived from source and original recording."""
    return json.dumps(record.group_key, ensure_ascii=False, separators=(",", ":"))


def split_by_source_group(
    records: Sequence[MetadataRecord],
    *,
    fractions: Mapping[str, float],
    seed: int,
) -> dict[str, str]:
    """Assign whole source-recording groups to train/validation/test reproducibly.

    Hash-based assignment does not inspect labels or audio. Every distinct
    group is kept intact; callers should inspect per-split class counts before
    training because small or imbalanced collections may omit a class.
    """
    split_names = ("train", "validation", "test")
    if set(fractions) != set(split_names):
        raise ValueError("fractions must define exactly train, validation, and test")
    if any(not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0 for value in fractions.values()):
        raise ValueError("all split fractions must be finite and positive")
    if not math.isclose(sum(fractions.values()), 1.0, rel_tol=0.0, abs_tol=1e-9):
        raise ValueError("split fractions must sum to 1")
    if type(seed) is not int:
        raise ValueError("seed must be an integer")
    if len({record.clip_id for record in records}) != len(records):
        raise ValueError("clip IDs must be unique before splitting")
    groups = {record.group_key for record in records}
    if len(groups) < 3:
        raise ValueError("at least three independent source-recording groups are required")

    boundaries = []
    running = 0.0
    for name in split_names:
        running += fractions[name]
        boundaries.append((name, running))
    assignment_by_group: dict[str, str] = {}
    for source_id, recording_id in sorted(groups):
        key = json.dumps((source_id, recording_id), ensure_ascii=False, separators=(",", ":"))
        digest = hashlib.sha256(f"{seed}\0{key}".encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:8], "big") / 2**64
        for name, boundary in boundaries:
            if bucket < boundary:
                assignment_by_group[key] = name
                break

    # Repair only empty partitions, moving the smallest deterministic donor group.
    for empty_name in split_names:
        if empty_name in assignment_by_group.values():
            continue
        counts = {name: sum(value == name for value in assignment_by_group.values()) for name in split_names}
        donor_names = [name for name in split_names if counts[name] > 1]
        if not donor_names:
            raise ValueError("cannot populate all splits without separating a source group")
        donor_name = max(donor_names, key=lambda name: (counts[name], name))
        movable = sorted(key for key, value in assignment_by_group.items() if value == donor_name)
        move_key = movable[-1]
        assignment_by_group[move_key] = empty_name

    assignments = {
        record.clip_id: assignment_by_group[group_id(record)]
        for record in records
    }
    assert_no_group_leakage(records, assignments)
    return assignments


def assert_no_group_leakage(
    records: Sequence[MetadataRecord],
    assignments: Mapping[str, str],
) -> None:
    """Reject missing assignments, unknown clips, and groups crossing splits."""
    known_ids = {record.clip_id for record in records}
    if set(assignments) != known_ids:
        raise ValueError("split assignments must cover each clip exactly once")
    group_splits: dict[tuple[str, str], set[str]] = {}
    for record in records:
        split = assignments[record.clip_id]
        if split not in ("train", "validation", "test"):
            raise ValueError(f"invalid split for clip {record.clip_id}")
        group_splits.setdefault(record.group_key, set()).add(split)
    leaking = [key for key, splits in group_splits.items() if len(splits) != 1]
    if leaking:
        raise ValueError(f"source-recording groups cross splits: {leaking!r}")


def summarize_split_readiness(
    records: Sequence[MetadataRecord], assignments: Mapping[str, str]
) -> dict[str, Any]:
    """Return class/group coverage per split without claiming model readiness.

    Each split must contain both target labels and at least two independent
    recording groups to be marked ready. This is a minimum diagnostic, not a
    statistically sufficient sample-size guarantee.
    """
    assert_no_group_leakage(records, assignments)
    summary: dict[str, Any] = {}
    for split in ("train", "validation", "test"):
        split_records = [record for record in records if assignments[record.clip_id] == split]
        counts = {label: sum(record.label == label for record in split_records) for label in CLASSES}
        groups_by_class = {
            label: sorted({group_id(record) for record in split_records if record.label == label})
            for label in CLASSES
        }
        missing = [label for label in CLASSES if counts[label] == 0]
        too_few_groups = [label for label in CLASSES if len(groups_by_class[label]) < 2]
        summary[split] = {
            "clip_count": len(split_records),
            "class_counts": counts,
            "distinct_group_count": len({record.group_key for record in split_records}),
            "groups_per_class": {label: len(groups_by_class[label]) for label in CLASSES},
            "missing_classes": missing,
            "classes_with_fewer_than_two_groups": too_few_groups,
            "ready_for_baseline": not missing and not too_few_groups,
        }
    return summary


def preprocess_wav(path: str | Path, config: PreprocessingConfig) -> PreprocessedAudio:
    """Downmix, resample, crop/pad, and optionally peak-normalize PCM WAV data."""
    info = validate_audio_file(path)
    with wave.open(str(path), "rb") as source:
        return _preprocess_wave_reader(source, info, config)


def preprocess_wav_bytes(payload: bytes, config: PreprocessingConfig) -> PreprocessedAudio:
    """Apply the same explicit preprocessing to an in-memory PCM WAV sample."""
    info = validate_audio_bytes(payload)
    with wave.open(BytesIO(payload), "rb") as source:
        return _preprocess_wave_reader(source, info, config)


def _preprocess_wave_reader(
    source: wave.Wave_read, info: AudioFileInfo, config: PreprocessingConfig
) -> PreprocessedAudio:
    target_frames = config.target_sample_count
    wanted_source_frames = max(1, math.ceil(config.target_duration_seconds * info.sample_rate_hz))
    available = min(wanted_source_frames, info.frame_count)
    if config.clip_strategy == "center" and info.frame_count > available:
        start = (info.frame_count - available) // 2
    else:
        start = 0

    source.setpos(start)
    raw = source.readframes(available)
    frame_width = info.channels * info.sample_width_bytes
    if len(raw) % frame_width:
        raise ValueError("WAV data ended in an incomplete sample frame during preprocessing")

    mono = _decode_mono(raw, info.channels, info.sample_width_bytes, config.channel_mix)
    resampled = _linear_resample(mono, info.sample_rate_hz, config.target_sample_rate_hz, target_frames)
    if config.normalization == "peak":
        peak = max((abs(value) for value in resampled), default=0.0)
        if peak > 0:
            resampled = [value / peak for value in resampled]
    return PreprocessedAudio(tuple(resampled), config.target_sample_rate_hz, info, config)


def build_manifest(
    report: DatasetReport,
    config: PreprocessingConfig,
    assignments: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Build stable, timestamp-free manifest data; consent references are omitted."""
    if assignments is not None:
        assert_no_group_leakage([sample.metadata for sample in report.samples], assignments)
        split_ready = all(
            item["ready_for_baseline"]
            for item in summarize_split_readiness(
                [sample.metadata for sample in report.samples], assignments
            ).values()
        )
    else:
        split_ready = False
    samples = []
    for sample in report.samples:
        record = sample.metadata
        samples.append({
            "clip_id": record.clip_id,
            "relative_path": record.relative_path,
            "label": record.label,
            "source_id": record.source_id,
            "source_type": record.source_type,
            "source_reference": record.source_reference,
            "license_id": record.license_id,
            "license_reference": record.license_reference,
            "original_recording_id": record.original_recording_id,
            "group_id": group_id(record),
            "approval_status": record.approval_status,
            "annotation_status": record.annotation_status,
            "split": assignments[record.clip_id] if assignments is not None else None,
            "sha256": sample.sha256,
            "audio": asdict(sample.audio),
        })
    return {
        "manifest_version": 1,
        "preprocessing": asdict(config),
        "samples": samples,
        "issues": [asdict(issue) for issue in report.issues],
        "ready_for_training": report.ready_for_training and not report.issues and split_ready,
    }


def write_manifest(manifest: Mapping[str, Any], destination: str | Path) -> None:
    """Write canonical JSON when explicitly called by a user workflow."""
    output = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    Path(destination).write_text(output + "\n", encoding="utf-8", newline="\n")


def _decode_mono(raw: bytes, channels: int, width: int, channel_mix: str) -> list[float]:
    values: list[float] = []
    bytes_per_frame = channels * width
    frame_count = len(raw) // bytes_per_frame
    for frame_index in range(frame_count):
        channel_values = []
        frame_start = frame_index * bytes_per_frame
        for channel_index in range(channels):
            start = frame_start + channel_index * width
            sample_bytes = raw[start:start + width]
            if width == 1:
                value = (sample_bytes[0] - 128) / 128.0
            elif width == 2:
                value = struct.unpack("<h", sample_bytes)[0] / 32768.0
            elif width == 3:
                integer = int.from_bytes(sample_bytes, "little", signed=False)
                if integer & 0x800000:
                    integer -= 1 << 24
                value = integer / 8388608.0
            else:
                value = struct.unpack("<i", sample_bytes)[0] / 2147483648.0
            channel_values.append(value)
        values.append(channel_values[0] if channel_mix == "first" else sum(channel_values) / channels)
    return values


def _linear_resample(
    samples: Sequence[float], source_rate: int, target_rate: int, target_count: int
) -> list[float]:
    if not samples:
        return [0.0] * target_count
    output = []
    for index in range(target_count):
        position = index * source_rate / target_rate
        # Resampling may request positions beyond a short source clip. Preserve
        # the explicit fixed-window policy by padding those positions with silence.
        if position >= len(samples):
            output.append(0.0)
            continue
        left = min(int(position), len(samples) - 1)
        right = min(left + 1, len(samples) - 1)
        fraction = position - left
        output.append(samples[left] + (samples[right] - samples[left]) * fraction)
    return output


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
