"""Print named non-secret configuration settings from a dotenv file.

Purpose:
    The Hemma deploy workers read a few plain configuration settings (for
    example BOOTSTRAP_SUPERUSER_EMAIL) from the production checkout's `.env`.
    This helper parses that file with python-dotenv, so quoting and inline
    comments mean what they mean everywhere else, and prints `NAME=value`
    lines only for the names the caller passes. Secrets never come from here:
    the deploy launcher starts the workers under the production secrets set.

Usage:
    pdm run python scripts/hemma_deploy_config.py <dotenv-path> NAME [NAME...]

Relationships:
    - Called by scripts/hemma_deploy_and_verify_seating_export.sh and
      scripts/hemma_deploy_and_verify_share_previews.sh.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

from dotenv import dotenv_values


def read_config(dotenv_path: Path, names: Sequence[str]) -> dict[str, str]:
    """Return the set, non-empty values of `names` from the dotenv file."""
    values = dotenv_values(dotenv_path)
    config: dict[str, str] = {}
    for name in names:
        value = values.get(name)
        if not value:
            continue
        if "\n" in value:
            raise ValueError(f"{name} in {dotenv_path} spans several lines")
        config[name] = value
    return config


def main(argv: Sequence[str]) -> int:
    if len(argv) < 2:
        print(
            "Usage: hemma_deploy_config.py <dotenv-path> NAME [NAME...]",
            file=sys.stderr,
        )
        return 2
    dotenv_path = Path(argv[0])
    if not dotenv_path.is_file():
        print(f"Missing dotenv file: {dotenv_path}", file=sys.stderr)
        return 1
    try:
        config = read_config(dotenv_path, argv[1:])
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    for name, value in config.items():
        print(f"{name}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
