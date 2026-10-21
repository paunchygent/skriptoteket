"""Shared subprocess environment for the pre-push hook script tests.

A real `git push` runs the hook inside pre-commit's environment, which sets
PRE_COMMIT_* (and may set GIT_*) variables. Tests must not inherit those from
the developer's shell: strip every PRE_COMMIT_* and GIT_* name computed from
the environment instead of hard-coding a partial list, then apply the test's
own overrides.
"""

from __future__ import annotations

import os


def hook_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith("PRE_COMMIT_") and not name.startswith("GIT_")
    }
    if extra:
        env.update(extra)
    return env
