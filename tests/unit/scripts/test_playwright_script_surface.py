"""Playwright script-surface hygiene tests.

Purpose:
    Keep the repo's runnable browser automation surface small and current so
    developers are not misled by superseded PR proof scripts.

Relationships:
    - Enforces the browser-automation policy in `.codex/rules/075-browser-automation.md`.
    - Preserves the retained HuleEdu auth/share proofs while routing small
      iterative checks to the Codex internal browser.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = ROOT / "scripts"

ALLOWED_PR_PLAYWRIGHT_SCRIPTS = {
    "playwright_pr_0252_auth_return_to_origin.py",
    "playwright_pr_0253_auth_retirement.py",
    "playwright_pr_0254_auth_cutover.py",
    "playwright_pr_0255_auth_bootstrap.py",
    "playwright_pr_0256_auth_ceremony.py",
    "playwright_pr_0258_auth_projection.py",
    "playwright_pr_0261_auth_action_matrix.py",
    "playwright_pr_0262_real_lifecycle.py",
    "playwright_pr_0274_authenticated_share_links.py",
    "playwright_pr_0286_share_export_affordance.py",
    "playwright_pr_0287_smart_settings_persistence.py",
    "playwright_pr_0299_logout_failure_toast.py",
    "playwright_pr_0302_toolbar_overflow_parity.py",
    "playwright_pr_0303_public_guest_overview_distribution.py",
    "playwright_pr_0310_phone_fixed_seat_rules_map.py",
    "playwright_pr_0311_phone_room_template_modal.py",
    "playwright_pr_0315_phone_rules_active_management.py",
    "playwright_pr_0316_smart_history_first_run_soft_degrade.py",
    "playwright_pr_0331_reviewed_ai_facit_live.py",
    "playwright_pr_0332_teacher_corrections_live.py",
}

ACTIVE_SCRIPT_SCAN_ROOTS = (
    SCRIPTS_DIR,
    ROOT / ".codex" / "skills",
)

LOCAL_AUTH_API_PREFIX = "/api/v1/auth"
RETIRED_LOGIN_PATH = f"{LOCAL_AUTH_API_PREFIX}/login"

RETIRED_LOCAL_AUTH_PATTERNS = {
    RETIRED_LOGIN_PATH,
    f'f"{{api_base_url}}{RETIRED_LOGIN_PATH}"',
    f'f"{{base_url}}{RETIRED_LOGIN_PATH}"',
}

RETIRED_COOKIE_PATTERN = "skriptoteket_session"
RETIRED_COOKIE_ALLOWLIST = {
    SCRIPTS_DIR / "_pr_0254_auth_cutover_browser.py",
}


def _text_files(root: Path) -> list[Path]:
    return [
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix in {".py", ".md", ".toml"}
    ]


def test_only_allowed_retained_pr_playwright_scripts_are_runnable() -> None:
    scripts = {path.name for path in SCRIPTS_DIR.glob("playwright_pr_*.py")}

    assert scripts == ALLOWED_PR_PLAYWRIGHT_SCRIPTS


def test_active_scripts_and_skills_do_not_advertise_retired_local_auth_login() -> None:
    offenders: list[str] = []
    for root in ACTIVE_SCRIPT_SCAN_ROOTS:
        for path in _text_files(root):
            text = path.read_text(encoding="utf-8")
            matches = sorted(pattern for pattern in RETIRED_LOCAL_AUTH_PATTERNS if pattern in text)
            if matches:
                offenders.append(f"{path.relative_to(ROOT)}: {', '.join(matches)}")

    assert offenders == []


def test_active_scripts_do_not_use_local_session_cookie_except_cutover_absence_probe() -> None:
    offenders: list[str] = []
    for path in _text_files(SCRIPTS_DIR):
        if path in RETIRED_COOKIE_ALLOWLIST:
            continue
        if RETIRED_COOKIE_PATTERN in path.read_text(encoding="utf-8"):
            offenders.append(str(path.relative_to(ROOT)))

    assert offenders == []
