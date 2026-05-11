"""PR-0253 local browser-auth retirement contract tests.

Purpose:
    Prevent local browser-auth routes, schemas, and dependency imports from
    re-entering the API surface after the HuleEdu-owned session cutover.

Relationships:
    - Complements route-level signed-context tests in
      `test_profile_app_continuation_api`.
    - Guards the generated OpenAPI contract consumed by the Vue SPA.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from fastapi import FastAPI

from skriptoteket.web.router import router as web_router

ROOT = Path(__file__).resolve().parents[3]
WEB_SOURCE_ROOTS = (
    ROOT / "src" / "skriptoteket" / "web" / "api",
    ROOT / "src" / "skriptoteket" / "web" / "routes",
)
FRONTEND_SOURCE_ROOT = ROOT / "frontend" / "apps" / "skriptoteket" / "src"
PYPROJECT_PATH = ROOT / "pyproject.toml"
RETIRED_DOC_COMMAND_SCAN_ROOTS = (
    ROOT / ".codex" / "rules",
    ROOT / "docs" / "runbooks",
    ROOT / "docs" / "reference",
)
RETIRED_AUTH_SURFACE_SCAN_ROOTS = (
    ROOT / "src" / "skriptoteket",
    ROOT / "tests" / "fixtures",
    ROOT / "tests" / "unit" / "web",
)

LOCAL_AUTH_API_PREFIX = "/api/v1/auth"
LOCAL_PROFILE_API_PREFIX = "/api/v1/profile"

RETIRED_LOCAL_AUTH_PATHS = {
    f"{LOCAL_AUTH_API_PREFIX}/login",
    f"{LOCAL_AUTH_API_PREFIX}/logout",
    f"{LOCAL_AUTH_API_PREFIX}/me",
    f"{LOCAL_AUTH_API_PREFIX}/csrf",
    f"{LOCAL_AUTH_API_PREFIX}/register",
    f"{LOCAL_AUTH_API_PREFIX}/register/validate",
    f"{LOCAL_AUTH_API_PREFIX}/resend-verification",
    f"{LOCAL_AUTH_API_PREFIX}/verify-email",
    f"{LOCAL_AUTH_API_PREFIX}/forgot-password",
    f"{LOCAL_AUTH_API_PREFIX}/reset-password",
    f"{LOCAL_PROFILE_API_PREFIX}/password",
    f"{LOCAL_PROFILE_API_PREFIX}/email",
}

RETIRED_LOCAL_AUTH_SCHEMAS = {
    "LoginRequest",
    "LoginResponse",
    "LogoutRequest",
    "MeResponse",
    "CsrfResponse",
    "RegisterRequest",
    "RegisterResponse",
    "ValidateRegistrationRequest",
    "ValidateRegistrationResponse",
    "VerifyEmailRequest",
    "VerifyEmailResponse",
    "ResendVerificationRequest",
    "ResendVerificationResponse",
    "ForgotPasswordRequest",
    "ForgotPasswordResponse",
    "ResetPasswordRequest",
    "ResetPasswordResponse",
    "ChangePasswordRequest",
    "ChangeEmailRequest",
    "ChangeEmailResponse",
}

RETIRED_BACKEND_IMPORTS = {
    "skriptoteket.web.auth.api_dependencies",
    "require_user_api",
    "require_contributor_api",
    "require_admin_api",
    "require_superuser_api",
    "require_session_api",
    "require_csrf_token",
}

RETIRED_BROWSER_SESSION_SYMBOLS = {
    "SessionRepositoryProtocol",
    "CurrentUserProviderProtocol",
    "LoginHandlerProtocol",
    "LogoutHandlerProtocol",
    "LoginCommand",
    "LoginResult",
    "LogoutCommand",
    "SESSION_COOKIE_NAME",
    "SESSION_TTL_SECONDS",
    "make_session",
    "skriptoteket_session",
}

RETIRED_DOC_COMMANDS = {
    "ui-smoke",
    "ui-editor-smoke",
    "ui-runtime-smoke",
}

RETAINED_PRODUCT_IDENTITY_CONCEPTS = {
    "AuthProvider.LOCAL",
    "ResetPasswordCommand",
    "RegisterUserCommand",
    "ValidateRegistrationCommand",
    "AdminUserCreateRequest",
}


def _python_files(paths: tuple[Path, ...]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        files.extend(sorted(path.rglob("*.py")))
    return files


def _frontend_source_files() -> list[Path]:
    return [
        path
        for path in FRONTEND_SOURCE_ROOT.rglob("*")
        if path.suffix in {".ts", ".vue"}
        and path.name != "openapi.d.ts"
        and ".spec." not in path.name
    ]


def _text_files(paths: tuple[Path, ...], suffixes: set[str]) -> list[Path]:
    files: list[Path] = []
    for root in paths:
        files.extend(
            sorted(path for path in root.rglob("*") if path.is_file() and path.suffix in suffixes)
        )
    return files


def test_openapi_excludes_retired_local_browser_auth_paths_and_schemas() -> None:
    app = FastAPI()
    app.include_router(web_router)

    openapi = app.openapi()

    assert RETIRED_LOCAL_AUTH_PATHS.isdisjoint(set(openapi["paths"]))
    assert RETIRED_LOCAL_AUTH_SCHEMAS.isdisjoint(set(openapi["components"]["schemas"]))


def test_browser_api_routes_do_not_import_retired_local_session_guards() -> None:
    offenders: list[str] = []
    for path in _python_files(WEB_SOURCE_ROOTS):
        text = path.read_text(encoding="utf-8")
        matches = sorted(token for token in RETIRED_BACKEND_IMPORTS if token in text)
        if matches:
            offenders.append(f"{path.relative_to(ROOT)}: {', '.join(matches)}")

    assert offenders == []


def test_source_and_web_tests_do_not_reintroduce_browser_session_contracts() -> None:
    offenders: list[str] = []
    for path in _text_files(RETIRED_AUTH_SURFACE_SCAN_ROOTS, {".py"}):
        if path == Path(__file__):
            continue
        text = path.read_text(encoding="utf-8")
        matches = sorted(
            token
            for token in RETIRED_BROWSER_SESSION_SYMBOLS
            if re.search(rf"\b{re.escape(token)}\b", text)
        )
        if matches:
            offenders.append(f"{path.relative_to(ROOT)}: {', '.join(matches)}")

    assert offenders == []


def test_no_zombie_contract_keeps_product_identity_concepts_allowed() -> None:
    """Document that PR-0253 retires browser sessions, not local identity concepts."""
    retired_tokens = RETIRED_BACKEND_IMPORTS | RETIRED_BROWSER_SESSION_SYMBOLS

    assert RETAINED_PRODUCT_IDENTITY_CONCEPTS.isdisjoint(retired_tokens)


def test_current_docs_rules_do_not_advertise_retired_smoke_commands() -> None:
    offenders: list[str] = []
    for path in _text_files(RETIRED_DOC_COMMAND_SCAN_ROOTS, {".md"}):
        text = path.read_text(encoding="utf-8")
        matches = sorted(token for token in RETIRED_DOC_COMMANDS if token in text)
        if matches:
            offenders.append(f"{path.relative_to(ROOT)}: {', '.join(matches)}")

    assert offenders == []


def test_frontend_source_does_not_call_local_auth_or_mint_gateway_identity_headers() -> None:
    retired_auth_fragments = {
        "/v1/auth/login",
        "/v1/auth/register",
        "/v1/auth/request-password-reset",
        "/v1/auth/reset-password",
        "/v1/auth/request-email-verification",
        "/v1/auth/verify-email",
        f"{LOCAL_AUTH_API_PREFIX}/login",
        f"{LOCAL_AUTH_API_PREFIX}/logout",
        f"{LOCAL_AUTH_API_PREFIX}/register",
        f"{LOCAL_AUTH_API_PREFIX}/forgot-password",
        f"{LOCAL_AUTH_API_PREFIX}/reset-password",
        f"{LOCAL_AUTH_API_PREFIX}/verify-email",
        f"{LOCAL_AUTH_API_PREFIX}/resend-verification",
        f"{LOCAL_AUTH_API_PREFIX}/csrf",
        f"{LOCAL_AUTH_API_PREFIX}/me",
        "X-HuleEdu-Identity-",
    }
    offenders: list[str] = []
    for path in _frontend_source_files():
        text = path.read_text(encoding="utf-8")
        matches = sorted(token for token in retired_auth_fragments if token in text)
        if matches:
            offenders.append(f"{path.relative_to(ROOT)}: {', '.join(matches)}")

    assert offenders == []


def test_active_playwright_command_surfaces_do_not_call_retired_local_auth() -> None:
    pyproject = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
    scripts = pyproject["tool"]["pdm"]["scripts"]
    active_modules = {
        value.removeprefix("python -m ").split(" ", 1)[0]
        for value in scripts.values()
        if isinstance(value, str) and value.startswith("python -m scripts.playwright")
    }
    active_paths = {ROOT / (module.replace(".", "/") + ".py") for module in active_modules}

    retired_fragments = {f"{LOCAL_AUTH_API_PREFIX}/login", f"{LOCAL_AUTH_API_PREFIX}/csrf"}
    offenders: list[str] = []
    for path in sorted(active_paths):
        text = path.read_text(encoding="utf-8")
        matches = sorted(token for token in retired_fragments if token in text)
        if matches:
            offenders.append(f"{path.relative_to(ROOT)}: {', '.join(matches)}")

    assert offenders == []
