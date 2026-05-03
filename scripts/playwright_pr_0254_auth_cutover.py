"""PR-0254 live Playwright proof for cross-app HuleEdu auth cutover.

Purpose:
    Certify the final local shared-session cutover across Skriptoteket SPA,
    HuleEdu Gateway auth entry, HuleEdu browser session/CSRF, Gateway-signed
    app continuation, Skriptoteket local projection/RBAC, write protection,
    and shared logout invalidation.

Relationships:
    - Targets PR-0254 / ST-28-04 cutover evidence.
    - Consumes retained PR-0261/PR-0262 and HuleEdu TASK-0326/TASK-0327
      artifacts before live browser work.
    - Persists `manifest.redacted.json` without raw URLs, credentials, tokens,
      cookies, CSRF, signed headers, raw subjects, or raw email addresses.
"""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from scripts._pr_0254_auth_cutover_browser import LoopbackLane, run_lane
from scripts._pr_0254_auth_cutover_manifest import (
    EnvironmentName,
    assert_final_manifest_redacted,
    build_manifest,
    validate_prerequisite_artifacts,
)

ARTIFACTS_DIR = Path(".artifacts/playwright-pr-0254-auth-cutover")
DEFAULT_BASE_URL = "http://localhost:5173"
DEFAULT_HULEEDU_LOGIN_ORIGIN = "http://localhost:5174"
DEFAULT_HULEEDU_AUTH_ORIGIN = "http://localhost:8080"
DEFAULT_127_BASE_URL = "http://127.0.0.1:5173"
DEFAULT_127_HULEEDU_LOGIN_ORIGIN = "http://127.0.0.1:5174"
DEFAULT_127_HULEEDU_AUTH_ORIGIN = "http://127.0.0.1:8080"
DEFAULT_DOTENV_PATH = "../../huleedu/.env"
DEFAULT_HULEEDU_TASK_0326_ARTIFACT = (
    "../../huleedu/.artifacts/skriptoteket-auth-bootstrap/local-verify-export.json"
)
DEFAULT_HULEEDU_TASK_0327_ROOT = "../../huleedu/.artifacts/skriptoteket-lifecycle-proof/dev"
DEFAULT_PR_0261_ARTIFACT = ".artifacts/playwright-pr-0261-auth-action-matrix/manifest.redacted.json"
DEFAULT_PR_0262_ROOT = ".artifacts/playwright-pr-0262-real-lifecycle/local-nonprod"
LocalRole = Literal["user", "contributor", "admin", "superuser"]


class ProviderLanePreflightError(RuntimeError):
    """Raised when the HuleEdu provider lane is not ready for browser proof."""


@dataclass(frozen=True)
class ArtifactPaths:
    """Resolved prerequisite artifact paths for PR-0254 preflight."""

    huleedu_task_0326: Path
    huleedu_task_0327: Path
    pr_0261: Path
    pr_0262: Path


@dataclass(frozen=True)
class AuthCutoverConfig:
    """Resolved PR-0254 auth-cutover proof settings."""

    environment: EnvironmentName
    primary_lane: LoopbackLane
    secondary_127_lane: LoopbackLane
    include_127_lane: bool
    require_127_lane: bool
    artifact_root: Path
    artifacts: ArtifactPaths
    expected_local_role: LocalRole
    email: str
    password: str


def _read_dotenv(path: Path) -> dict[str, str]:
    """Read simple dotenv files without evaluating shell syntax."""
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _value(
    *,
    cli_value: str | None,
    env_key: str,
    dotenv: dict[str, str],
    default: str | None = None,
) -> str | None:
    """Resolve one config value from CLI, env, dotenv, then default."""
    return cli_value or os.environ.get(env_key) or dotenv.get(env_key) or default


def _credentials(
    *,
    email: str | None,
    password: str | None,
    dotenv: dict[str, str],
) -> tuple[str | None, str | None]:
    """Resolve Playwright credentials without printing or persisting secrets."""
    resolved_email = (
        email
        or os.environ.get("PLAYWRIGHT_EMAIL")
        or dotenv.get("PLAYWRIGHT_EMAIL")
        or os.environ.get("SKRIPTOTEKET_LIFECYCLE_PROOF_EMAIL")
        or dotenv.get("SKRIPTOTEKET_LIFECYCLE_PROOF_EMAIL")
        or os.environ.get("BOOTSTRAP_SUPERUSER_EMAIL")
        or dotenv.get("BOOTSTRAP_SUPERUSER_EMAIL")
    )
    resolved_password = (
        password
        or os.environ.get("PLAYWRIGHT_PASSWORD")
        or dotenv.get("PLAYWRIGHT_PASSWORD")
        or os.environ.get("SKRIPTOTEKET_LIFECYCLE_PROOF_PASSWORD")
        or dotenv.get("SKRIPTOTEKET_LIFECYCLE_PROOF_PASSWORD")
        or os.environ.get("BOOTSTRAP_SUPERUSER_PASSWORD")
        or dotenv.get("BOOTSTRAP_SUPERUSER_PASSWORD")
    )
    return resolved_email, resolved_password


def _normalize_origin(value: str, *, field_name: str) -> str:
    """Validate and normalize an origin-like URL."""
    normalized = value.rstrip("/")
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path:
        raise SystemExit(f"Invalid {field_name}: {value}")
    return normalized


def _latest_file(root: Path, pattern: str, *, label: str) -> Path:
    """Return the newest matching artifact under a run root."""
    matches = sorted(path for path in root.glob(pattern) if path.is_file())
    if not matches:
        raise SystemExit(f"No {label} artifact found under {root} matching {pattern}")
    return matches[-1]


def _resolve_path(value: str | None, *, default: str) -> Path:
    """Resolve an optional artifact path without following symlinks."""
    return Path(value or default).expanduser()


def _environment_name(value: str) -> EnvironmentName:
    """Narrow argparse environment strings to the manifest environment type."""
    if value == "local-nonprod":
        return "local-nonprod"
    if value == "production":
        return "production"
    raise SystemExit(f"Unsupported environment: {value}")


def _local_role(value: str) -> LocalRole:
    """Narrow argparse role strings to the supported local role type."""
    if value == "user":
        return "user"
    if value == "contributor":
        return "contributor"
    if value == "admin":
        return "admin"
    if value == "superuser":
        return "superuser"
    raise SystemExit(f"Unsupported local role: {value}")


def _resolve_artifacts(args: argparse.Namespace) -> ArtifactPaths:
    """Resolve retained upstream artifact paths used by the preflight."""
    huleedu_0326 = _resolve_path(
        args.huleedu_task_0326_artifact or os.environ.get("HULEEDU_TASK_0326_ARTIFACT"),
        default=DEFAULT_HULEEDU_TASK_0326_ARTIFACT,
    )
    huleedu_0327_value = args.huleedu_task_0327_artifact or os.environ.get(
        "HULEEDU_TASK_0327_ARTIFACT"
    )
    huleedu_0327 = (
        Path(huleedu_0327_value).expanduser()
        if huleedu_0327_value
        else _latest_file(
            Path(DEFAULT_HULEEDU_TASK_0327_ROOT),
            "skriptoteket-lifecycle-proof-apply-*.json",
            label="HuleEdu TASK-0327",
        )
    )
    pr_0261 = _resolve_path(
        args.pr_0261_artifact or os.environ.get("PR_0261_ARTIFACT"),
        default=DEFAULT_PR_0261_ARTIFACT,
    )
    pr_0262_value = args.pr_0262_artifact or os.environ.get("PR_0262_ARTIFACT")
    pr_0262 = (
        Path(pr_0262_value).expanduser()
        if pr_0262_value
        else _latest_file(
            Path(DEFAULT_PR_0262_ROOT),
            "*/manifest.redacted.json",
            label="PR-0262",
        )
    )
    return ArtifactPaths(
        huleedu_task_0326=huleedu_0326,
        huleedu_task_0327=huleedu_0327,
        pr_0261=pr_0261,
        pr_0262=pr_0262,
    )


def _parse_args(argv: Sequence[str] | None = None) -> AuthCutoverConfig:
    """Parse CLI args and dotenv-backed defaults."""
    parser = argparse.ArgumentParser(
        description="PR-0254 live HuleEdu/Skriptoteket auth-cutover proof"
    )
    parser.add_argument(
        "--environment",
        choices=["local-nonprod", "production"],
        default="local-nonprod",
    )
    parser.add_argument(
        "--dotenv",
        default=os.environ.get("DOTENV_PATH") or DEFAULT_DOTENV_PATH,
        help=(f"Dotenv file for proof credentials (default: DOTENV_PATH or {DEFAULT_DOTENV_PATH})"),
    )
    parser.add_argument("--artifact-dir", default=None, help="Artifact root; run id is appended.")
    parser.add_argument("--base-url", default=None, help=f"Skriptoteket URL ({DEFAULT_BASE_URL})")
    parser.add_argument("--huleedu-login-origin", default=None)
    parser.add_argument("--huleedu-auth-origin", default=None)
    parser.add_argument("--base-url-127", default=None)
    parser.add_argument("--huleedu-login-origin-127", default=None)
    parser.add_argument("--huleedu-auth-origin-127", default=None)
    parser.add_argument("--include-127-lane", action="store_true")
    parser.add_argument("--require-127-lane", action="store_true")
    parser.add_argument("--huleedu-task-0326-artifact", default=None)
    parser.add_argument("--huleedu-task-0327-artifact", default=None)
    parser.add_argument("--pr-0261-artifact", default=None)
    parser.add_argument("--pr-0262-artifact", default=None)
    parser.add_argument(
        "--expected-local-role",
        choices=["user", "contributor", "admin", "superuser"],
        default="contributor",
    )
    parser.add_argument("--email", default=None, help="Login email override")
    parser.add_argument("--password", default=None, help="Login password override")
    args = parser.parse_args(argv)

    if args.require_127_lane and not args.include_127_lane:
        parser.error("--require-127-lane requires --include-127-lane")

    dotenv = _read_dotenv(Path(args.dotenv))
    email, password = _credentials(email=args.email, password=args.password, dotenv=dotenv)
    if not email or not password:
        parser.error(
            "Missing credentials. Provide --email/--password, PLAYWRIGHT_* values, "
            "or BOOTSTRAP_SUPERUSER_* values in --dotenv."
        )

    primary_lane = LoopbackLane(
        name="localhost",
        base_url=_normalize_origin(
            _value(
                cli_value=args.base_url,
                env_key="BASE_URL",
                dotenv=dotenv,
                default=DEFAULT_BASE_URL,
            )
            or DEFAULT_BASE_URL,
            field_name="--base-url",
        ),
        huleedu_login_origin=_normalize_origin(
            _value(
                cli_value=args.huleedu_login_origin,
                env_key="HULEEDU_LOGIN_ORIGIN",
                dotenv=dotenv,
                default=DEFAULT_HULEEDU_LOGIN_ORIGIN,
            )
            or DEFAULT_HULEEDU_LOGIN_ORIGIN,
            field_name="--huleedu-login-origin",
        ),
        huleedu_auth_origin=_normalize_origin(
            _value(
                cli_value=args.huleedu_auth_origin,
                env_key="HULEEDU_AUTH_ORIGIN",
                dotenv=dotenv,
                default=DEFAULT_HULEEDU_AUTH_ORIGIN,
            )
            or DEFAULT_HULEEDU_AUTH_ORIGIN,
            field_name="--huleedu-auth-origin",
        ),
    )
    secondary_127_lane = LoopbackLane(
        name="127",
        base_url=_normalize_origin(
            args.base_url_127 or DEFAULT_127_BASE_URL,
            field_name="--base-url-127",
        ),
        huleedu_login_origin=_normalize_origin(
            args.huleedu_login_origin_127 or DEFAULT_127_HULEEDU_LOGIN_ORIGIN,
            field_name="--huleedu-login-origin-127",
        ),
        huleedu_auth_origin=_normalize_origin(
            args.huleedu_auth_origin_127 or DEFAULT_127_HULEEDU_AUTH_ORIGIN,
            field_name="--huleedu-auth-origin-127",
        ),
    )
    return AuthCutoverConfig(
        environment=_environment_name(str(args.environment)),
        primary_lane=primary_lane,
        secondary_127_lane=secondary_127_lane,
        include_127_lane=args.include_127_lane,
        require_127_lane=args.require_127_lane,
        artifact_root=(
            Path(args.artifact_dir).expanduser()
            if args.artifact_dir
            else ARTIFACTS_DIR / args.environment
        ),
        artifacts=_resolve_artifacts(args),
        expected_local_role=_local_role(str(args.expected_local_role)),
        email=email,
        password=password,
    )


def _run_id() -> str:
    """Return the UTC run id used for retained artifacts."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _http_status(url: str, *, timeout_seconds: float = 3.0) -> int:
    """Return the HTTP status for a provider-lane readiness URL."""
    request = Request(url, method="GET", headers={"Accept": "application/json,text/html"})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            return int(response.status)
    except HTTPError as exc:
        return int(exc.code)
    except URLError as exc:
        raise ProviderLanePreflightError(f"{url} failed: {exc.reason}") from exc


def _assert_provider_surface(lane: LoopbackLane) -> None:
    """Fail fast when the HuleEdu provider lane cannot serve this loopback host."""
    checks = (
        (f"{lane.huleedu_auth_origin}/v1/auth/session", 200, "Gateway session surface"),
        (f"{lane.huleedu_login_origin}/login", 200, "login/lifecycle UI"),
    )
    for url, expected_status, label in checks:
        status = _http_status(url)
        if status != expected_status:
            raise ProviderLanePreflightError(
                f"{label} for lane {lane.name} returned {status}, expected {expected_status}: {url}"
            )


def _preflight_provider_lanes(lanes: Iterable[LoopbackLane]) -> None:
    """Validate HuleEdu provider surfaces before opening Playwright."""
    failures: list[str] = []
    for lane in lanes:
        try:
            _assert_provider_surface(lane)
        except ProviderLanePreflightError as exc:
            failures.append(str(exc))
    if failures:
        detail = "\n".join(f"- {failure}" for failure in failures)
        raise ProviderLanePreflightError(
            "HuleEdu provider regression: required local shared-auth provider "
            "surface is unavailable before browser launch.\n"
            f"{detail}\n"
            "Expected HuleEdu auth integration lane: "
            "`pdm run run-local-pdm auth-integration start` and "
            "`pdm run run-local-pdm auth-integration fe-dev`."
        )


def _artifact_list(result: dict[str, object]) -> list[str]:
    """Extract retained artifact paths from a lane result."""
    artifacts = result.get("artifacts")
    if not isinstance(artifacts, list):
        return []
    return [str(item) for item in artifacts if isinstance(item, str)]


def _section(result: dict[str, object], key: str) -> dict[str, object]:
    """Return a named lane-result section after validating its shape."""
    section = result.get(key)
    if not isinstance(section, dict):
        raise AssertionError(f"Lane result missing object section: {key}")
    return {str(section_key): section_value for section_key, section_value in section.items()}


def _run(config: AuthCutoverConfig) -> Path:
    """Run prerequisite preflight, browser proof, and redacted manifest writing."""
    run_dir = config.artifact_root / _run_id()
    run_dir.mkdir(parents=True, exist_ok=True)
    prerequisite_artifacts = validate_prerequisite_artifacts(
        huleedu_task_0326_path=config.artifacts.huleedu_task_0326,
        huleedu_task_0327_path=config.artifacts.huleedu_task_0327,
        pr_0261_path=config.artifacts.pr_0261,
        pr_0262_path=config.artifacts.pr_0262,
    )
    provider_lanes = [config.primary_lane]
    if config.include_127_lane:
        provider_lanes.append(config.secondary_127_lane)
    _preflight_provider_lanes(provider_lanes)

    primary, forbidden_values = run_lane(
        lane=config.primary_lane,
        email=config.email,
        password=config.password,
        expected_local_role=config.expected_local_role,
        run_dir=run_dir,
    )
    lane_assertions: dict[str, object] = {"localhost": _section(primary, "lane_summary")}
    retained_artifacts = _artifact_list(primary)
    if config.include_127_lane:
        secondary, secondary_forbidden = run_lane(
            lane=config.secondary_127_lane,
            email=config.email,
            password=config.password,
            expected_local_role=config.expected_local_role,
            run_dir=run_dir,
        )
        forbidden_values.extend(secondary_forbidden)
        lane_assertions["127"] = _section(secondary, "lane_summary")
        retained_artifacts.extend(_artifact_list(secondary))
    else:
        lane_assertions["127"] = {
            "status": "blocked",
            "reason": "127 lane was not requested; rerun with --include-127-lane when ready.",
        }

    logout_assertions = _section(primary, "logout_assertions")
    logout_assertions["session_authority"] = primary["session_authority_assertions"]
    manifest = build_manifest(
        environment=config.environment,
        run_id=run_dir.name,
        command="pdm run auth-cutover-proof",
        validated_prerequisite_artifacts=prerequisite_artifacts,
        public_route_assertions=_section(primary, "public_route_assertions"),
        auth_entry_assertions=_section(primary, "auth_entry_assertions"),
        gateway_proxy_assertions=_section(primary, "gateway_proxy_assertions"),
        callback_assertions=_section(primary, "callback_assertions"),
        projection_assertions=_section(primary, "projection_assertions"),
        local_role_assertions=_section(primary, "local_role_assertions"),
        csrf_write_assertions=_section(primary, "csrf_write_assertions"),
        logout_assertions=logout_assertions,
        lane_assertions=lane_assertions,
        artifacts=retained_artifacts,
        forbidden_values=forbidden_values,
    )
    manifest_path = run_dir / "manifest.redacted.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    assert_final_manifest_redacted(
        json.loads(manifest_path.read_text(encoding="utf-8")),
        forbidden_values=forbidden_values,
    )
    return manifest_path


def main(argv: Sequence[str] | None = None) -> None:
    """CLI entrypoint."""
    manifest_path = _run(_parse_args(argv))
    print(f"playwright-pr-0254-auth-cutover: ok manifest={manifest_path}")


if __name__ == "__main__":
    main()
