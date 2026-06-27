"""Run pytest with host-native PDF renderer libraries discoverable.

Purpose:
    Provide the repo-owned pytest command surface for local validation where
    WeasyPrint-backed PDF renderers need macOS package-manager libraries.
Relationships:
    - Used by PDM `test` scripts and the pre-commit targeted pytest helper.
    - Keeps native library environment normalization outside domain and
      application code.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

MACOS_NATIVE_LIBRARY_ENV_VARS = (
    "DYLD_FALLBACK_LIBRARY_PATH",
    "DYLD_LIBRARY_PATH",
)
CONFIGURED_LIBRARY_DIRS_ENV = "SKRIPTOTEKET_NATIVE_LIBRARY_DIRS"
DEFAULT_MACOS_NATIVE_LIBRARY_DIRS = (
    Path("/opt/homebrew/lib"),
    Path("/usr/local/lib"),
    Path("/opt/local/lib"),
)


def build_pytest_environment(base_env: dict[str, str] | None = None) -> dict[str, str]:
    """Return environment variables for the pytest child process."""

    env = dict(os.environ if base_env is None else base_env)
    if sys.platform != "darwin":
        return env

    native_library_dirs = _configured_native_library_dirs(env)
    if not native_library_dirs:
        return env

    for env_var in MACOS_NATIVE_LIBRARY_ENV_VARS:
        env[env_var] = _prepend_path_entries(
            current_value=env.get(env_var, ""),
            new_entries=native_library_dirs,
        )
    return env


def _configured_native_library_dirs(env: dict[str, str]) -> tuple[str, ...]:
    """Return existing native-library directories for local PDF renderer tests."""

    raw_configured_dirs = env.get(CONFIGURED_LIBRARY_DIRS_ENV)
    if raw_configured_dirs:
        candidates = [Path(value).expanduser() for value in raw_configured_dirs.split(os.pathsep)]
    else:
        candidates = list(DEFAULT_MACOS_NATIVE_LIBRARY_DIRS)

    return tuple(str(candidate) for candidate in candidates if candidate.is_dir())


def _prepend_path_entries(*, current_value: str, new_entries: tuple[str, ...]) -> str:
    """Prepend path entries while preserving existing user-supplied values."""

    existing_entries = tuple(entry for entry in current_value.split(os.pathsep) if entry)
    merged_entries: list[str] = []
    for entry in (*new_entries, *existing_entries):
        if entry not in merged_entries:
            merged_entries.append(entry)
    return os.pathsep.join(merged_entries)


def main(argv: list[str]) -> int:
    """Execute pytest with the normalized child-process environment."""

    command = [sys.executable, "-m", "pytest", *argv]
    completed = subprocess.run(command, check=False, env=build_pytest_environment())
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
