"""Contract tests for the trusted shared-owner docs workflow."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import yaml

WORKFLOW = Path(__file__).resolve().parents[3] / ".github/workflows/docs-validate.yml"


def _workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def _workflow() -> dict[str, dict[str, dict[str, str]]]:
    parsed = yaml.safe_load(_workflow_text())
    return parsed


def test_workflow_keeps_events_and_required_admission_and_shared_checks() -> None:
    workflow = _workflow()
    triggers = workflow.get("on") or workflow.get(True)
    assert isinstance(triggers, dict)
    assert "pull_request" in triggers
    assert "push" in triggers
    jobs = workflow["jobs"]
    assert "docs-validate-admission" in jobs
    assert "docs-validate-shared" in jobs

    text = _workflow_text()
    assert "fork_requires_trusted_mirror" in text
    assert "github.event.pull_request.head.repo.full_name" in text
    assert "github.repository" in text
    assert "trusted/fork-pr-" in text
    assert "/trust-docs-validate" in text
    assert "github.event.pull_request.head.sha" in text


def test_shared_job_is_trusted_owner_bootstrap_only() -> None:
    text = _workflow_text()
    shared = _workflow()["jobs"]["docs-validate-shared"]
    assert shared["needs"] == "docs-validate-admission"
    assert shared["environment"] == {"name": "skill-repository-read"}
    assert "vars.SKILL_REPOSITORY_APP_ID" in text
    assert "secrets.SKILL_REPOSITORY_APP_PRIVATE_KEY" in text
    assert "permission-contents: read" in text
    assert "paunchygent" in text
    assert "skill-repository" in text
    assert "path: .shared/skill-repository" in text
    assert "persist-credentials: false" in text
    assert "~/.codex/skill-repository" in text
    assert "pdm install -G monorepo-tools --frozen-lockfile" in text
    assert 'cd "$GITHUB_WORKSPACE/.shared/skill-repository"' in text
    assert 'cd "$GITHUB_WORKSPACE"' in text
    assert "actions/cache" not in text
    assert "upload-artifact" not in text


def test_workflow_rejects_unsafe_secret_execution_shapes() -> None:
    text = _workflow_text()
    assert "pull_request_target" not in text
    assert "workflow_run" not in text
    assert "workflow_dispatch" not in text
    admission = _workflow()["jobs"]["docs-validate-admission"]
    assert admission["runs-on"] == "ubuntu-latest"
    assert "secrets" not in str(admission)


def _run_admission(
    tmp_path: Path,
    *,
    event_name: str,
    head_repository: str,
    head_sha: str,
    head_ref: str,
    gh_mode: str = "approved",
    permission: str = "write",
) -> subprocess.CompletedProcess[str]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    workflow = _workflow()
    admission_step = workflow["jobs"]["docs-validate-admission"]["steps"][0]
    script = tmp_path / "admission.sh"
    script.write_text(admission_step["run"], encoding="utf-8")
    fake_gh = tmp_path / "gh"
    fake_gh.write_text(
        "#!/bin/sh\n"
        'args="$*"\n'
        'case "$args" in\n'
        "  *'.head.sha'*) printf '%s\\n' \"$FAKE_ORIGINAL_SHA\" ;;\n"
        "  *'.head.repo.full_name'*) printf '%s\\n' \"paunchygent/forked-skriptoteket\" ;;\n"
        "  *'.head.repo.fork'*) printf '%s\\n' 'true' ;;\n"
        "  *'/comments'*) [ \"$FAKE_GH_MODE\" = 'missing' ] || "
        "printf '%s\\t1\\n' \"$FAKE_COMMENTER\" ;;\n"
        "  *'/collaborators/'*) printf '%s\\n' \"$FAKE_PERMISSION\" ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)
    output = tmp_path / "github-output"
    environment = os.environ.copy()
    environment.update(
        {
            "PATH": f"{tmp_path}:{environment['PATH']}",
            "EVENT_NAME": event_name,
            "REPOSITORY": "paunchygent/skriptoteket",
            "HEAD_REPOSITORY": head_repository,
            "HEAD_SHA": head_sha,
            "HEAD_REF": head_ref,
            "GH_TOKEN": "test-token",
            "GITHUB_OUTPUT": str(output),
            "FAKE_ORIGINAL_SHA": head_sha,
            "FAKE_GH_MODE": gh_mode,
            "FAKE_COMMENTER": "maintainer",
            "FAKE_PERMISSION": permission,
        }
    )
    return subprocess.run(
        ["bash", str(script)],
        check=False,
        text=True,
        capture_output=True,
        env=environment,
    )


def test_admission_script_simulates_trusted_fork_and_mirror_contexts(tmp_path: Path) -> None:
    sha = "a" * 40
    trusted = _run_admission(
        tmp_path / "trusted",
        event_name="pull_request",
        head_repository="paunchygent/skriptoteket",
        head_sha=sha,
        head_ref="feature/docs",
    )
    assert trusted.returncode == 0

    fork = _run_admission(
        tmp_path / "fork",
        event_name="pull_request",
        head_repository="contributor/skriptoteket",
        head_sha=sha,
        head_ref="feature/docs",
    )
    assert fork.returncode == 1
    assert "fork_requires_trusted_mirror" in fork.stderr

    changed_sha = _run_admission(
        tmp_path / "changed-sha",
        event_name="pull_request",
        head_repository="paunchygent/skriptoteket",
        head_sha="b" * 40,
        head_ref=f"trusted/fork-pr-42-{sha}",
    )
    assert changed_sha.returncode == 1
    assert "trusted_mirror_sha_mismatch" in changed_sha.stderr

    short_sha = _run_admission(
        tmp_path / "short-sha",
        event_name="pull_request",
        head_repository="paunchygent/skriptoteket",
        head_sha="c" * 39,
        head_ref=f"trusted/fork-pr-42-{sha}",
    )
    assert short_sha.returncode == 1
    assert "trusted_mirror_sha_mismatch" in short_sha.stderr

    missing_approval = _run_admission(
        tmp_path / "missing-approval",
        event_name="pull_request",
        head_repository="paunchygent/skriptoteket",
        head_sha=sha,
        head_ref=f"trusted/fork-pr-42-{sha}",
        gh_mode="missing",
    )
    assert missing_approval.returncode == 1
    assert "trusted_mirror_approval_missing" in missing_approval.stderr

    unauthorized = _run_admission(
        tmp_path / "unauthorized",
        event_name="pull_request",
        head_repository="paunchygent/skriptoteket",
        head_sha=sha,
        head_ref=f"trusted/fork-pr-42-{sha}",
        permission="read",
    )
    assert unauthorized.returncode == 1
    assert "trusted_mirror_approval_unauthorized" in unauthorized.stderr

    approved = _run_admission(
        tmp_path / "approved",
        event_name="pull_request",
        head_repository="paunchygent/skriptoteket",
        head_sha=sha,
        head_ref=f"trusted/fork-pr-42-{sha}",
    )
    assert approved.returncode == 0
