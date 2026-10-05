"""Compatibility entrypoint for the canonical native dependency check."""

from __future__ import annotations

import subprocess
from pathlib import Path


def main() -> None:
    """Run the same worker check as Compose and operator commands."""
    script = Path(__file__).with_name("healthcheck_execution_worker.sh")
    raise SystemExit(subprocess.call(["/bin/sh", str(script)]))


if __name__ == "__main__":
    main()
