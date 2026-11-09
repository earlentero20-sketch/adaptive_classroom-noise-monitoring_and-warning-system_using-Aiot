"""Load private SONIQ settings and start the backend with this interpreter."""

from pathlib import Path
import os
import re
import subprocess
import sys


SONIQ_ENV_KEYS = frozenset(
    {
        "SONIQ_DATABASE_URL",
        "BACKEND_HOST",
        "BACKEND_PORT",
        "WARNING_THRESHOLD_DB_SPL",
        "MAX_INPUT_AGE_SECONDS",
        "SONIQ_AUDIO_MODEL_PATH",
        "SONIQ_DB_POOL_MIN_SIZE",
        "SONIQ_DB_POOL_MAX_SIZE",
    }
)
ENV_ASSIGNMENT = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")


def load_soniq_environment(env_file: Path, environment: dict[str, str]) -> dict[str, str]:
    """Read allowlisted .env entries without printing or executing their values."""
    child_environment = environment.copy()
    if not env_file.is_file():
        return child_environment

    for line_number, line in enumerate(env_file.read_text(encoding="utf-8-sig").splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = ENV_ASSIGNMENT.fullmatch(stripped)
        if match is None:
            print(
                f"WARNING: Ignoring malformed .env line {line_number}; value withheld.",
                file=sys.stderr,
            )
            continue

        key, value = match.groups()
        if key not in SONIQ_ENV_KEYS or child_environment.get(key):
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        child_environment[key] = value
    return child_environment


def main() -> int:
    repository_root = Path(__file__).resolve().parents[1]
    environment = load_soniq_environment(
        repository_root / ".env",
        dict(os.environ),
    )
    if not environment.get("SONIQ_DATABASE_URL", "").strip():
        print(
            "WARNING: SONIQ_DATABASE_URL is not configured. Backend will start "
            "in degraded mode; event endpoints return storage_unavailable."
        )
    if not environment.get("SONIQ_AUDIO_MODEL_PATH", "").strip():
        print(
            "WAV classification will report model_unavailable until "
            "SONIQ_AUDIO_MODEL_PATH points to a trusted compatible artifact."
        )

    print("Starting SONIQ backend. Environment values are not displayed.")
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "backend.app"],
            cwd=repository_root,
            env=environment,
            check=False,
        )
    except OSError:
        print(
            "ERROR: Could not launch the backend with the selected Python interpreter.",
            file=sys.stderr,
        )
        return 1
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
