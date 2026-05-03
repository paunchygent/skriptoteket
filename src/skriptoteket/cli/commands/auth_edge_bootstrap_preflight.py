"""Preflight local HuleEdu auth-edge bootstrap readiness.

Purpose:
    Diagnose the local shared-auth bootstrap chain before browser proof:
    HuleEdu credential seed, provider subject export, Gateway/login reachability,
    signing trust configuration, and Skriptoteket projection/RBAC state.

Relationships:
    - Consumes the same HuleEdu subject export schema as
      `consume_huleedu_subject_export`.
    - Reads Skriptoteket-local user/projection state without mutating it.
    - Keeps browser login authority in HuleEdu and product RBAC in Skriptoteket.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated
from urllib.error import URLError
from urllib.request import Request, urlopen

import typer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.application.identity.huleedu_subject_export_contract import (
    HuleEduSubjectExport,
    HuleEduSubjectExportRecord,
    parse_huleedu_subject_export,
)
from skriptoteket.cli._db import open_session
from skriptoteket.config import Settings
from skriptoteket.infrastructure.db.models.identity_projection import IdentityProjectionModel
from skriptoteket.infrastructure.db.models.user import UserModel

PREFLIGHT_SCHEMA_VERSION = "skriptoteket-auth-edge-bootstrap-preflight-v1"
DEFAULT_HULEEDU_IDENTITY_LOGIN_URL = "http://127.0.0.1:7005/v1/auth/login"
DEFAULT_HULEEDU_GATEWAY_HEALTH_URL = "http://localhost:8080/healthz"
DEFAULT_HULEEDU_LOGIN_UI_URL = "http://localhost:5174/login"

EXPECTED_LOCAL_MATRIX: Mapping[str, tuple[str, str]] = {
    "skriptoteket-proof-user": ("skriptoteket-proof-user@local.dev", "user"),
    "skriptoteket-proof-contributor": ("skriptoteket-proof-contributor@local.dev", "contributor"),
    "skriptoteket-proof-admin": ("skriptoteket-proof-admin@local.dev", "admin"),
    "skriptoteket-proof-superuser": ("superuser@local.dev", "superuser"),
}


@dataclass(frozen=True)
class PreflightIssue:
    """One sanitized local auth-edge preflight issue."""

    code: str
    message: str
    stable_account_key: str | None = None
    email: str | None = None
    field: str | None = None

    def to_dict(self) -> dict[str, str]:
        """Serialize non-secret issue details."""
        payload = {"code": self.code, "message": self.message}
        if self.stable_account_key is not None:
            payload["stable_account_key"] = self.stable_account_key
        if self.email is not None:
            payload["email"] = self.email
        if self.field is not None:
            payload["field"] = self.field
        return payload


def auth_edge_bootstrap_preflight(
    export_json: Annotated[
        Path,
        typer.Option(
            "--export-json",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
            help="Sanitized HuleEdu subject export JSON to verify against local projections.",
        ),
    ],
    output_json: Annotated[
        Path | None,
        typer.Option(
            "--output-json",
            file_okay=True,
            dir_okay=False,
            writable=True,
            resolve_path=True,
            help="Optional sanitized preflight result artifact path.",
        ),
    ] = None,
    huleedu_identity_login_url: Annotated[
        str,
        typer.Option(
            "--huleedu-identity-login-url",
            help="Local HuleEdu Identity login endpoint used for credential seed proof.",
        ),
    ] = DEFAULT_HULEEDU_IDENTITY_LOGIN_URL,
    huleedu_gateway_health_url: Annotated[
        str,
        typer.Option(
            "--huleedu-gateway-health-url",
            help="Local HuleEdu Gateway health endpoint used for auth-edge readiness.",
        ),
    ] = DEFAULT_HULEEDU_GATEWAY_HEALTH_URL,
    huleedu_login_ui_url: Annotated[
        str,
        typer.Option(
            "--huleedu-login-ui-url",
            help="Local HuleEdu login UI URL used for browser ceremony readiness.",
        ),
    ] = DEFAULT_HULEEDU_LOGIN_UI_URL,
    skip_network: Annotated[
        bool,
        typer.Option(
            "--skip-network",
            help="Skip HuleEdu HTTP reachability checks; DB/export checks still run.",
        ),
    ] = False,
) -> None:
    """Preflight local shared-auth bootstrap readiness."""
    settings = Settings()
    payload = json.loads(export_json.read_text(encoding="utf-8"))
    export = parse_huleedu_subject_export(payload)
    issues = _validate_export_matrix(export)
    issues.extend(_validate_signing_trust(settings))
    if not skip_network:
        issues.extend(
            _validate_huleedu_network(
                settings=settings,
                identity_login_url=huleedu_identity_login_url,
                gateway_health_url=huleedu_gateway_health_url,
                login_ui_url=huleedu_login_ui_url,
            )
        )
    issues.extend(asyncio.run(_validate_local_state(settings=settings, export=export)))

    result = {
        "schema_version": PREFLIGHT_SCHEMA_VERSION,
        "status": "failed" if issues else "ok",
        "checks": {
            "provider_export": "ok"
            if not _has_issue(issues, "provider_export_stale")
            else "failed",
            "huleedu_credential_seed": "skipped"
            if skip_network
            else _bucket_status(issues, "huleedu_credential_seed_stale"),
            "huleedu_auth_edge": "skipped"
            if skip_network
            else _bucket_status(
                issues,
                "huleedu_gateway_unreachable",
                "huleedu_login_ui_unreachable",
            ),
            "gateway_signing_trust": _bucket_status(issues, "gateway_signing_trust_missing"),
            "skriptoteket_projection_rbac": _bucket_status(
                issues,
                "bootstrap_identity_conflict",
                "local_identity_conflict",
                "missing_local_user",
                "inactive_local_user",
                "unverified_local_user",
                "wrong_local_role",
                "missing_identity_projection",
                "projection_user_mismatch",
            ),
        },
        "issues": [issue.to_dict() for issue in issues],
    }
    if output_json is not None:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))
    if issues:
        raise typer.Exit(code=1)


def _validate_export_matrix(export: HuleEduSubjectExport) -> list[PreflightIssue]:
    issues: list[PreflightIssue] = []
    records_by_key = {record.stable_account_key: record for record in export.accounts}
    for stable_key, (expected_email, expected_role) in EXPECTED_LOCAL_MATRIX.items():
        record = records_by_key.get(stable_key)
        if record is None:
            issues.append(
                PreflightIssue(
                    code="provider_export_stale",
                    message="HuleEdu export is missing a required local proof account.",
                    stable_account_key=stable_key,
                )
            )
            continue
        if record.email != expected_email:
            issues.append(
                PreflightIssue(
                    code="provider_export_stale",
                    message="HuleEdu export email does not match the local dev identity contract.",
                    stable_account_key=stable_key,
                    email=record.email,
                    field="email",
                )
            )
        if record.skriptoteket_role_hint != expected_role:
            issues.append(
                PreflightIssue(
                    code="provider_export_stale",
                    message="HuleEdu export role hint does not match the local dev role matrix.",
                    stable_account_key=stable_key,
                    email=record.email,
                    field="skriptoteket_role_hint",
                )
            )
    return issues


def _validate_signing_trust(settings: Settings) -> list[PreflightIssue]:
    if settings.HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY:
        return []
    if settings.HULEEDU_INTERNAL_IDENTITY_TRUSTED_PUBLIC_KEYS_JSON:
        return []
    key_path = settings.HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_PATH
    if key_path and Path(key_path).is_file():
        return []
    host_key_path = settings.HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_HOST_PATH
    if host_key_path and Path(host_key_path).is_file():
        return []
    return [
        PreflightIssue(
            code="gateway_signing_trust_missing",
            message="Skriptoteket has no readable HuleEdu Gateway signing public key configured.",
            field="HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_PATH",
        )
    ]


def _validate_huleedu_network(
    *,
    settings: Settings,
    identity_login_url: str,
    gateway_health_url: str,
    login_ui_url: str,
) -> list[PreflightIssue]:
    issues: list[PreflightIssue] = []
    email = settings.BOOTSTRAP_SUPERUSER_EMAIL.strip()
    password = settings.BOOTSTRAP_SUPERUSER_PASSWORD
    if not email or not password:
        issues.append(
            PreflightIssue(
                code="huleedu_credential_seed_stale",
                message="BOOTSTRAP_SUPERUSER_EMAIL/PASSWORD must be present for local proof.",
            )
        )
        return issues
    if not _post_json_ok(identity_login_url, {"email": email, "password": password}):
        issues.append(
            PreflightIssue(
                code="huleedu_credential_seed_stale",
                message="HuleEdu Identity did not accept the configured bootstrap credentials.",
                email=email,
            )
        )
    if not _get_ok(gateway_health_url):
        issues.append(
            PreflightIssue(
                code="huleedu_gateway_unreachable",
                message="HuleEdu Gateway health endpoint is not reachable.",
            )
        )
    if not _get_ok(login_ui_url):
        issues.append(
            PreflightIssue(
                code="huleedu_login_ui_unreachable",
                message="HuleEdu login UI is not reachable.",
            )
        )
    return issues


async def _validate_local_state(
    *,
    settings: Settings,
    export: HuleEduSubjectExport,
) -> list[PreflightIssue]:
    issues: list[PreflightIssue] = []
    async with open_session(settings) as session:
        for record in export.accounts:
            if record.stable_account_key not in EXPECTED_LOCAL_MATRIX:
                continue
            user_result = await session.execute(
                select(UserModel).where(UserModel.email == record.email)
            )
            user = user_result.scalar_one_or_none()
            if user is None:
                issues.append(_local_issue("missing_local_user", record))
                continue
            if user.auth_provider != "huleedu" or user.password_hash is not None:
                code = (
                    "bootstrap_identity_conflict"
                    if record.stable_account_key == "skriptoteket-proof-superuser"
                    else "local_identity_conflict"
                )
                issues.append(
                    _local_issue(
                        code,
                        record,
                        field="auth_provider",
                        message="Local user is not a HuleEdu-projected passwordless identity.",
                    )
                )
                continue
            if not user.is_active:
                issues.append(_local_issue("inactive_local_user", record))
            if not user.email_verified:
                issues.append(_local_issue("unverified_local_user", record))
            if user.role != record.skriptoteket_role_hint:
                issues.append(_local_issue("wrong_local_role", record, field="role"))
            projection = await _load_projection(session=session, record=record)
            if projection is None:
                issues.append(_local_issue("missing_identity_projection", record))
            elif projection.user_id != user.id:
                issues.append(_local_issue("projection_user_mismatch", record))
    return issues


async def _load_projection(
    *,
    session: AsyncSession,
    record: HuleEduSubjectExportRecord,
) -> IdentityProjectionModel | None:
    result = await session.execute(
        select(IdentityProjectionModel).where(
            IdentityProjectionModel.product_identity_realm == record.active_product_identity_realm,
            IdentityProjectionModel.realm_subject_id == record.realm_subject_id,
        )
    )
    return result.scalar_one_or_none()


def _local_issue(
    code: str,
    record: HuleEduSubjectExportRecord,
    *,
    field: str | None = None,
    message: str | None = None,
) -> PreflightIssue:
    return PreflightIssue(
        code=code,
        message=message or "Skriptoteket local projection/RBAC state is incomplete.",
        stable_account_key=record.stable_account_key,
        email=record.email,
        field=field,
    )


def _post_json_ok(url: str, payload: Mapping[str, str]) -> bool:
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return _request_ok(request)


def _get_ok(url: str) -> bool:
    return _request_ok(Request(url, method="GET"))


def _request_ok(request: Request) -> bool:
    try:
        with urlopen(request, timeout=5) as response:
            status = int(response.status)
            return 200 <= status < 400
    except (OSError, URLError):
        return False


def _has_issue(issues: Iterable[PreflightIssue], code: str) -> bool:
    return any(issue.code == code for issue in issues)


def _bucket_status(issues: Iterable[PreflightIssue], *codes: str) -> str:
    return "failed" if any(issue.code in codes for issue in issues) else "ok"
