"""Script-surface hygiene tests.

Domain purpose:
    Keep the repo's runnable browser automation surface small and current so
    developers are not misled by superseded PR proof scripts or stale retained
    production proof fixtures.

Relationships:
    - Enforces the browser-automation policy in `.codex/rules/075-browser-automation.md`.
    - Preserves the retained HuleEdu auth/share proofs while routing small
      iterative checks to the Codex internal browser.
"""

from __future__ import annotations

from pathlib import Path

from scripts._document_converter_proof import (
    FORBIDDEN_ARTIFACT_MARKERS,
    build_document_converter_fixture_files,
)
from scripts.document_converter_artifact_hygiene_production_proof import (
    build_project_fixture,
    inspect_artifact,
)

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
    "playwright_pr_0337_correction_session_live.py",
    "playwright_pr_0356_source_only_fixture_proof.py",
}

ACTIVE_REUSABLE_PROOF_SCRIPTS = {
    "audio_transcription_parity_live.py",
    "audio_transcription_retryable_reattempt_public_proof.py",
    "authenticated_app_identity_split.py",
    "authenticated_home_work_apps.py",
    "authenticated_shell_navigation.py",
}

META_NAMED_ACTIVE_PROOF_SCRIPTS = {
    "playwright_pr_0349_transcript_parity_live.py": "audio_transcription_parity_live.py",
    "playwright_pr_0363_conversion_mode_deeplink.py": "authenticated_app_identity_split.py",
    "playwright_pr_0364_authenticated_home_work_apps.py": "authenticated_home_work_apps.py",
    "playwright_pr_0365_authenticated_shell_navigation.py": "authenticated_shell_navigation.py",
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


def test_active_reusable_proof_scripts_use_domain_names() -> None:
    scripts = {path.name for path in SCRIPTS_DIR.glob("*.py")}

    offenders = sorted(name for name in META_NAMED_ACTIVE_PROOF_SCRIPTS if name in scripts)
    missing = sorted(name for name in ACTIVE_REUSABLE_PROOF_SCRIPTS if name not in scripts)

    assert offenders == []
    assert missing == []


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


def test_document_converter_proof_fixture_matches_artifact_hygiene_contract(
    tmp_path: Path,
) -> None:
    """Keep the live proof fixture aligned with PR-0400 artifact hygiene."""
    fixture_paths = [Path(path) for path in build_document_converter_fixture_files(tmp_path)]
    text_payload = "\n".join(
        path.read_text(encoding="utf-8")
        for path in fixture_paths
        if path.suffix.lower() in {".css", ".html"}
    )

    assert "project:///cover.png" in text_payload
    assert "project:///saknas.png" not in text_payload
    assert [path.name for path in fixture_paths] == [
        "agnes-leandersson.html",
        "styles.css",
        "cover.png",
    ]
    assert [marker for marker in FORBIDDEN_ARTIFACT_MARKERS if marker in text_payload] == []


def test_document_converter_native_proof_uses_real_declared_project_assets() -> None:
    """Keep the Hemma-native production proof aligned with PR-0400."""
    manifest, files = build_project_fixture()
    text_payload = "\n".join(
        project_file.content.decode("utf-8")
        for project_file in files
        if project_file.content_type in {"text/css", "text/html"}
    )

    assert manifest.image_files == ["cover.png"]
    assert "project:///cover.png" in text_payload
    assert "project:///saknas.png" not in text_payload
    assert [marker for marker in FORBIDDEN_ARTIFACT_MARKERS if marker in text_payload] == []


def test_document_converter_native_proof_reports_dirty_docx_markers(tmp_path: Path) -> None:
    """Prove retained proof inspection catches forbidden text inside DOCX XML."""
    docx_path = tmp_path / "dirty.docx"
    import zipfile

    with zipfile.ZipFile(docx_path, "w") as archive:
        archive.writestr(
            "word/document.xml",
            "<w:document>pdf_checkpointed_output</w:document>",
        )

    result = inspect_artifact(
        output_dir=tmp_path,
        label="dirty-proof",
        filename="dirty.docx",
        content_type=("application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        content=docx_path.read_bytes(),
    )

    assert result["forbidden_marker_hits"] == ["pdf_checkpointed_output"]
