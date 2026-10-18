"""Validated librosa MFCC extraction with explicit, serialized parameters."""

from dataclasses import asdict, dataclass
import math
from typing import Protocol, Sequence

from ml.data_pipeline import PreprocessedAudio


class AudioFeatureExtractor(Protocol):
    name: str
    version: str

    def extract(self, audio: PreprocessedAudio) -> Sequence[float]: ...


@dataclass(frozen=True)
class MFCCConfig:
    sample_rate_hz: int
    channel_handling: str
    n_mfcc: int
    n_mels: int
    n_fft: int
    win_length: int
    hop_length: int
    window: str
    fmin_hz: float
    fmax_hz: float
    center: bool = False
    power: float = 2.0
    aggregation: str = "mean_std"

    def __post_init__(self) -> None:
        for name in ("sample_rate_hz", "n_mfcc", "n_mels", "n_fft", "win_length", "hop_length"):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if self.n_mfcc > self.n_mels:
            raise ValueError("n_mfcc must not exceed n_mels")
        if self.channel_handling != "preprocessed_mono":
            raise ValueError("channel_handling must be 'preprocessed_mono'; mix channels in preprocessing")
        if self.win_length > self.n_fft:
            raise ValueError("win_length must not exceed n_fft")
        if self.hop_length > self.n_fft:
            raise ValueError("hop_length must not exceed n_fft")
        if not isinstance(self.window, str) or not self.window.strip():
            raise ValueError("window must be a non-empty librosa window name")
        if (isinstance(self.fmin_hz, bool) or not isinstance(self.fmin_hz, (int, float))
                or isinstance(self.fmax_hz, bool) or not isinstance(self.fmax_hz, (int, float))
                or not math.isfinite(self.fmin_hz) or not math.isfinite(self.fmax_hz)
                or self.fmin_hz < 0 or self.fmax_hz <= self.fmin_hz
                or self.fmax_hz > self.sample_rate_hz / 2):
            raise ValueError("frequency bounds must satisfy 0 <= fmin < fmax <= Nyquist")
        if (isinstance(self.power, bool) or not isinstance(self.power, (int, float))
                or not math.isfinite(self.power) or self.power <= 0):
            raise ValueError("power must be finite and positive")
        if type(self.center) is not bool:
            raise ValueError("center must be boolean")
        if self.aggregation != "mean_std":
            raise ValueError("aggregation must be 'mean_std'")


@dataclass(frozen=True)
class MFCCFeatureExtractor:
    config: MFCCConfig
    name: str = "librosa-mfcc-mean-std"
    version: str = "1"

    def __post_init__(self) -> None:
        if not isinstance(self.config, MFCCConfig):
            raise ValueError("config must be MFCCConfig")

    def metadata(self) -> dict[str, object]:
        return {
            "name": self.name,
            "version": self.version,
            "implementation_library": "librosa",
            "config": asdict(self.config),
        }

    def extract(self, audio: PreprocessedAudio) -> tuple[float, ...]:
        if audio.sample_rate_hz != self.config.sample_rate_hz:
            raise ValueError("preprocessed sample rate does not match MFCC configuration")
        if audio.config.target_sample_rate_hz != self.config.sample_rate_hz:
            raise ValueError("preprocessing and MFCC sample rates must match")
        if len(audio.samples) != audio.config.target_sample_count:
            raise ValueError("preprocessed audio length does not match its configuration")
        if len(audio.samples) < self.config.n_fft:
            raise ValueError("audio is shorter than one configured MFCC frame")
        if any(not math.isfinite(value) for value in audio.samples):
            raise ValueError("audio samples must be finite")
        try:
            import librosa
            import numpy as np
        except ImportError as error:
            raise RuntimeError(
                "MFCC extraction requires approved librosa and NumPy dependencies"
            ) from error

        waveform = np.asarray(audio.samples, dtype=np.float32)
        try:
            coefficients = librosa.feature.mfcc(
                y=waveform,
                sr=self.config.sample_rate_hz,
                n_mfcc=self.config.n_mfcc,
                dct_type=2,
                norm="ortho",
                lifter=0,
                n_fft=self.config.n_fft,
                hop_length=self.config.hop_length,
                win_length=self.config.win_length,
                window=self.config.window,
                center=self.config.center,
                n_mels=self.config.n_mels,
                fmin=self.config.fmin_hz,
                fmax=self.config.fmax_hz,
                power=self.config.power,
                mel_norm="slaney",
            )
        except (TypeError, ValueError) as error:
            raise ValueError(f"invalid MFCC configuration or waveform: {error}") from error
        if coefficients.ndim != 2 or coefficients.shape[0] != self.config.n_mfcc or coefficients.shape[1] == 0:
            raise ValueError("librosa returned an unexpected MFCC tensor shape")
        pooled = np.concatenate((coefficients.mean(axis=1), coefficients.std(axis=1)))
        return _validate_feature_values(pooled)


def extract_feature_vector(
    extractor: AudioFeatureExtractor, audio: PreprocessedAudio
) -> tuple[float, ...]:
    """Validate a fixed-length, finite feature vector from a plug-in extractor."""
    if (not isinstance(extractor.name, str) or not extractor.name.strip()
            or not isinstance(extractor.version, str) or not extractor.version.strip()):
        raise ValueError("feature extractor must identify its name and version")
    return _validate_feature_values(extractor.extract(audio))


def _validate_feature_values(values: Sequence[float]) -> tuple[float, ...]:
    raw_values = tuple(values)
    if len(raw_values) == 0:
        raise ValueError("feature extractor returned an empty vector")
    normalized: list[float] = []
    for value in raw_values:
        if isinstance(value, bool):
            raise ValueError("feature extractor must return finite numeric values")
        try:
            numeric = float(value)
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError("feature extractor must return finite numeric values") from error
        if not math.isfinite(numeric):
            raise ValueError("feature extractor must return finite numeric values")
        normalized.append(numeric)
    return tuple(normalized)
