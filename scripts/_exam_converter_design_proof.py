"""Exam Converter design proof helpers.

Domain purpose:
    Verify the authenticated Exam Converter design-alignment fixture through
    the shared HuleEdu browser-session ceremony.

Relationships:
    - Consumed by retained PR artifact adapters instead of creating new
      permanent PR-numbered Playwright entrypoints.
    - Uses the dev-only Exam Converter UI fixture route and route-owned
      inspection selectors for desktop and phone screenshot proof.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict
from urllib.parse import urlparse

from playwright.sync_api import Page, expect, sync_playwright

from scripts._playwright_auth import login_via_auth_entry
from scripts._playwright_browser import launch_chromium
from scripts._playwright_config import get_config

ARTIFACT_ROOT = Path(".artifacts/pr-0408-exam-converter-design-proof")
FIXTURE_PATH = "/apps/documents.conversion_hub/exam-converter/ui-fixtures/ai-facit-review"
FIXTURE_READY_SELECTOR = '[data-inspection-fixture-id="ai-facit-review"]'


class JsonObject(TypedDict, total=False):
    artifact_dir: str
    base_url: str
    captures: list["Capture"]
    command: str
    error: str
    fixture: str
    name: str
    overflow: dict[str, int | bool]
    path: str
    screenshot: str
    status: str
    timestamp_utc: str
    viewport: dict[str, int] | None


class Capture(TypedDict):
    name: str
    overflow: dict[str, int | bool]
    path: str
    screenshot: str
    viewport: dict[str, int] | None


def run_dir(root: Path = ARTIFACT_ROOT) -> Path:
    """Create a timestamped proof artifact directory."""
    path = root / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path.mkdir(parents=True, exist_ok=False)
    return path


def write_manifest(artifact_dir: Path, manifest: JsonObject) -> None:
    """Write the redacted proof manifest."""
    (artifact_dir / "manifest.redacted.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def assert_no_horizontal_overflow(page: Page) -> dict[str, int | bool]:
    """Assert the current viewport has no document-level horizontal overflow."""
    metrics = page.evaluate(
        """() => {
          const doc = document.documentElement;
          const body = document.body;
          return {
            bodyClientWidth: body.clientWidth,
            bodyScrollWidth: body.scrollWidth,
            docClientWidth: doc.clientWidth,
            docScrollWidth: doc.scrollWidth,
            ok: doc.scrollWidth <= doc.clientWidth + 1 && body.scrollWidth <= body.clientWidth + 1,
          };
        }"""
    )
    if not metrics["ok"]:
        raise AssertionError(f"horizontal overflow: {metrics}")
    return metrics


def capture(page: Page, artifact_dir: Path, name: str) -> Capture:
    """Capture a screenshot plus route and overflow evidence."""
    screenshot = artifact_dir / f"{name}.png"
    page.wait_for_timeout(500)
    page.screenshot(path=str(screenshot), full_page=True)
    return {
        "name": name,
        "overflow": assert_no_horizontal_overflow(page),
        "path": urlparse(page.url).path,
        "screenshot": str(screenshot),
        "viewport": page.viewport_size,
    }


def open_fixture(
    page: Page,
    *,
    artifact_dir: Path,
    base_url: str,
    email: str,
    password: str,
) -> None:
    """Open the authenticated Exam Converter design fixture."""
    login_via_auth_entry(
        page,
        base_url=base_url,
        email=email,
        password=password,
        next_path=FIXTURE_PATH,
        success_heading_pattern=r"^Konvertera prov$",
        success_selector=FIXTURE_READY_SELECTOR,
        recover_to_next_path=True,
        rate_limit_backoff=True,
        failure_artifacts_dir=artifact_dir,
        failure_screenshot_name="login-failure.png",
        success_timeout_ms=60_000,
    )
    if urlparse(page.url).path != FIXTURE_PATH:
        page.goto(FIXTURE_PATH, wait_until="domcontentloaded")
    expect(page.locator(FIXTURE_READY_SELECTOR)).to_be_visible(timeout=60_000)


def prove_desktop(page: Page, artifact_dir: Path) -> list[Capture]:
    """Assert and capture desktop PR-0408 design-alignment states."""
    page.set_viewport_size({"width": 1366, "height": 900})
    page.goto(FIXTURE_PATH, wait_until="domcontentloaded")
    expect(page.locator(FIXTURE_READY_SELECTOR)).to_be_visible(timeout=60_000)
    expect(page.locator('[data-test="exam-converter-workflow-rail-shell"]')).to_be_visible()
    expect(page.locator('[data-test="exam-converter-question-review-shell"]')).to_be_visible()
    expect(page.locator(".exam-converter-question-table")).to_be_visible()
    expect(page.locator('[data-test="exam-converter-selected-question-detail"]')).to_be_visible()
    prefill_panel = page.locator('[data-test="exam-converter-ai-prefill-panel"]')
    expect(prefill_panel).to_contain_text("Kontrollera facit")
    expect(prefill_panel).to_contain_text("Granska frågorna som saknar rätt svar eller facitsvar.")
    expect(page.locator(".lucide-bot")).to_have_count(0)
    _assert_symbolic_step_navigation(page)
    captures = [capture(page, artifact_dir, "desktop-questions")]

    page.locator('[data-test="exam-converter-inspection-tab-files"]').click()
    _assert_files_surface(page)
    captures.append(capture(page, artifact_dir, "desktop-files"))

    page.locator('[data-test="exam-converter-inspection-tab-report"]').click()
    _assert_report_surface(page)
    captures.append(capture(page, artifact_dir, "desktop-report"))
    return captures


def prove_phone(page: Page, artifact_dir: Path) -> list[Capture]:
    """Assert and capture phone PR-0408 design-alignment states."""
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(FIXTURE_PATH, wait_until="domcontentloaded")
    expect(page.locator(FIXTURE_READY_SELECTOR)).to_be_visible(timeout=60_000)
    expect(page.locator('[data-test="exam-converter-question-review-shell"]')).to_be_visible()
    expect(page.locator(".exam-converter-question-table")).to_be_hidden()
    expect(page.locator(".exam-converter-question-navigator")).to_be_visible()
    captures = [capture(page, artifact_dir, "phone-list")]

    page.locator('[data-test="exam-converter-open-ai-prefill-action"]').click()
    review_shell = page.locator('[data-test="exam-converter-question-review-shell"]')
    expect(review_shell).to_have_class(re.compile(r"\bis-compact-detail-open\b"))
    expect(page.locator('[data-test="exam-converter-selected-question-detail"]')).to_have_attribute(
        "data-selected-item-id", "item-001"
    )
    captures.append(capture(page, artifact_dir, "phone-review-action"))
    page.locator('[data-test="exam-converter-compact-back-to-questions"]').click()

    page.locator('[data-test="exam-converter-question-navigator-row-item-001"]').click()
    expect(page.locator('[data-test="exam-converter-selected-question-detail"]')).to_be_visible()
    expect(page.locator('[data-test="exam-converter-compact-back-to-questions"]')).to_be_visible()
    captures.append(capture(page, artifact_dir, "phone-detail"))

    page.locator('[data-test="exam-converter-inspection-tab-files"]').click()
    _assert_files_surface(page)
    captures.append(capture(page, artifact_dir, "phone-files"))

    page.locator('[data-test="exam-converter-inspection-tab-report"]').click()
    _assert_report_surface(page)
    captures.append(capture(page, artifact_dir, "phone-report"))
    return captures


def prove_review_routing_journey(page: Page, artifact_dir: Path) -> Capture:
    """Exercise production review navigation in a real browser with local projections."""
    page.goto("/", wait_until="domcontentloaded")
    page.evaluate(
        """async () => {
          document.body.innerHTML = '<main><div id="review-routing-proof"></div></main>';
          const vue = await import('/node_modules/.vite/deps/vue.js');
          const component = (await import(
            '/@fs/WORKTREE/frontend/apps/skriptoteket/src/views/apps/exam-converter-authenticated/ExamConverterQuestionReviewShell.vue'
          )).default;
          const candidate = (itemId, sequence, correctIds) => ({
            answerPayload: { correctAlternativeIds: correctIds, kind: 'choice' },
            backendFailureCode: null,
            backendStatus: 'success',
            candidateId: `candidate-${itemId}`,
            candidatePayloadDigest: `sha256:candidate-${itemId}`,
            completionReportSha256: 'sha256:completion',
            decisionState: 'suggested',
            itemId,
            itemType: sequence === 1 ? 'single_choice' : 'multiple_response',
            modelProfile: 'browser-proof',
            promptTemplateVersion: 'browser-proof-v1',
            providerProfileId: 'local',
            schemaName: 'digiexam_choice_answer_key_decision_v1',
            schemaVersion: 'digiexam_choice_answer_key_decision_v1',
            sequence,
            validationState: 'valid',
          });
          const question = (itemId, sequence, correctIds) => ({
            alternatives: [
              { id: '1', text: 'Alternativ ett' },
              { id: '2', text: 'Alternativ två' },
              { id: '3', text: 'Alternativ tre' },
            ],
            answerKeyReviewOrigin: 'none',
            answerKeyReviewReasons: ['advisory_candidate_pending'],
            answerKeyReviewState: 'review_required',
            answerKeyReviewStateLabel: 'Granska facit',
            answerKeyReviewStateReasonLabel: null,
            currentAnswerKeyProvenance: 'machine_proposed',
            effectiveAnswerKey: null,
            effectivePointCorrection: null,
            gaps: [],
            itemId,
            itemType: sequence === 1 ? 'single_choice' : 'multiple_response',
            llmCandidate: candidate(itemId, sequence, correctIds),
            lucktextStructure: null,
            manualFollowUpMessages: [],
            missingFields: ['Facit'],
            pointsLabel: '1 p',
            pointsValue: 1,
            promptText: `Kontrollfråga ${sequence}`,
            sequence,
            sourceItemFingerprint: `sha256:${itemId}`,
            status: 'attention',
            statusSymbol: 'ai_suggestion',
            title: `Fråga ${sequence}`,
            typeLabel: sequence === 1 ? 'Envalsfråga' : 'Flervalsfråga',
          });
          const projectionFor = (questions) => ({
            answerKeyCompletionReport: null,
            answerKeyReviewState: { items: [], schema_version: 'digiexam_answer_key_review_state_v1' },
            artifactSourceBinding: {
              effective_exam_schema_version: 'digiexam_effective_exam_v1',
              effective_exam_sha256: 'sha256:effective',
              source_ir_schema_version: 'digiexam_intermediate_exam_v1',
              source_ir_sha256: 'sha256:source-ir',
            },
            defaultMode: 'questions',
            effectiveAnswerKeysByItem: new Map(),
            effectivePointCorrectionsByItem: new Map(),
            files: [],
            questions,
            report: {
              aiSuggestionCount: questions.filter((entry) => entry.llmCandidate).length,
              aiSuggestionOutcomes: {
                acceptedUnchangedCount: 0,
                items: [],
                suppressedCount: 0,
                teacherEditedCount: 0,
                totalCount: questions.length,
                unresolvedCount: questions.filter(
                  (entry) => entry.answerKeyReviewState === 'review_required'
                ).length,
              },
              attentionQuestionCount: questions.filter(
                (entry) => entry.answerKeyReviewState === 'review_required'
              ).length,
              blockedTargetFileCount: 0,
              missingAnswerKeyCount: 0,
              missingPointsCount: 0,
              warningCount: 0,
            },
            sourceFilename: 'browser-proof.dxe',
            sourceFileSha256: 'sha256:browser-proof',
          });
          const resolved = (entry) => ({
            ...entry,
            answerKeyReviewOrigin: 'reviewed_advisory',
            answerKeyReviewReasons: ['reviewed_advisory_accepted'],
            answerKeyReviewState: 'review_complete',
            answerKeyReviewStateLabel: 'Facit granskat',
            currentAnswerKeyProvenance: 'reviewed',
            effectiveAnswerKey: {
              correct_alternative_ids: entry.llmCandidate.answerPayload.correctAlternativeIds,
              lineage: null,
              provenance: 'reviewed',
            },
            missingFields: [],
            status: 'complete',
            statusSymbol: 'complete',
          });
          const first = question('item-first', 1, [2]);
          const second = question('item-second', 2, [1, 3]);
          vue.createApp({
            setup() {
              const applying = vue.ref(false);
              const focusKey = vue.ref(0);
              const questions = vue.ref([first, second]);
              const apply = (selected) => {
                applying.value = true;
                window.setTimeout(() => {
                  questions.value = questions.value.map((entry) =>
                    entry.itemId === selected.itemId ? resolved(entry) : entry
                  );
                  applying.value = false;
                }, 0);
              };
              return () => vue.h('div', [
                vue.h('button', {
                  'data-test': 'browser-open-review',
                  onClick: () => { focusKey.value += 1; },
                  type: 'button',
                }, 'Granska frågor'),
                vue.h(component, {
                  aiSuggestionFocusKey: focusKey.value,
                  isCorrectionApplying: applying.value,
                  onApplyManualAnswerKey: apply,
                  onAiPrefillFocused: () => undefined,
                  onApplyItemTextPatch: () => undefined,
                  onApplyPointCorrection: () => undefined,
                  projection: projectionFor(questions.value),
                }),
              ]);
            },
          }).mount('#review-routing-proof');
        }""".replace("WORKTREE", str(Path.cwd()).replace("'", "\\'"))
    )
    page.set_viewport_size({"width": 390, "height": 844})
    page.locator('[data-test="browser-open-review"]').click()
    shell = page.locator('[data-test="exam-converter-question-review-shell"]')
    expect(shell).to_have_class(re.compile(r"\bis-compact-detail-open\b"))
    detail = page.locator('[data-test="exam-converter-selected-question-detail"]')
    expect(detail).to_have_attribute("data-selected-item-id", "item-first")
    page.locator('[data-test="exam-converter-accept-advisory-answer-key-action"]').click()
    expect(detail).to_have_attribute("data-selected-item-id", "item-second")
    expect(shell).to_have_class(re.compile(r"\bis-compact-detail-open\b"))
    page.locator('[data-test="exam-converter-edit-advisory-answer-key-action"]').click()
    page.locator('[data-test="exam-converter-apply-manual-answer-key-action"]').click()
    expect(shell).not_to_have_class(re.compile(r"\bis-compact-detail-open\b"))
    return capture(page, artifact_dir, "phone-review-routing-journey")


def run_exam_converter_design_proof() -> Path:
    """Run the retained PR-0408 design proof and return the artifact directory."""
    config = get_config(["--base-url", "http://127.0.0.1:5173", "--dotenv", ".env"])
    artifact_dir = run_dir()
    manifest: JsonObject = {
        "artifact_dir": str(artifact_dir),
        "base_url": config.base_url,
        "command": (
            "pdm run python "
            ".artifacts/pr-0408-exam-converter-design-proof/"
            "proof_pr0408_exam_converter_design.py"
        ),
        "fixture": FIXTURE_PATH,
        "status": "running",
        "timestamp_utc": datetime.now(UTC).isoformat(),
    }
    write_manifest(artifact_dir, manifest)

    with sync_playwright() as playwright:
        browser = launch_chromium(playwright)
        context = browser.new_context(base_url=config.base_url)
        page = context.new_page()
        page.set_default_timeout(60_000)
        try:
            open_fixture(
                page,
                artifact_dir=artifact_dir,
                base_url=config.base_url,
                email=config.email,
                password=config.password,
            )
            captures = prove_desktop(page, artifact_dir)
            captures.extend(prove_phone(page, artifact_dir))
            captures.append(prove_review_routing_journey(page, artifact_dir))
            manifest["captures"] = captures
            manifest["status"] = "ok"
            write_manifest(artifact_dir, manifest)
        except Exception as exc:
            manifest["error"] = f"{type(exc).__name__}: {exc}"
            manifest["status"] = "failed"
            write_manifest(artifact_dir, manifest)
            raise
        finally:
            context.close()
            browser.close()
    return artifact_dir


def _assert_symbolic_step_navigation(page: Page) -> None:
    previous_action = page.locator('[data-test="exam-converter-detail-previous-question"]')
    next_action = page.locator('[data-test="exam-converter-detail-next-question"]')
    if not previous_action.get_attribute("aria-label"):
        raise AssertionError("Previous-question action is missing an accessible label.")
    if not next_action.get_attribute("aria-label"):
        raise AssertionError("Next-question action is missing an accessible label.")
    step_nav_text = page.locator(".exam-converter-detail-step-nav").inner_text()
    if "Föregående" in step_nav_text or "Nästa" in step_nav_text:
        raise AssertionError(f"visible word labels in symbolic nav: {step_nav_text!r}")


def _assert_files_surface(page: Page) -> None:
    expect(page.locator('[data-test="exam-converter-files-readiness-list"]')).to_be_visible()
    expect(page.locator('[data-test="exam-converter-selected-question-detail"]')).to_have_count(0)
    expect(page.locator('[data-test="exam-converter-download-file-examnet_pdf"]')).to_be_visible()
    expect(page.locator('[data-test="exam-converter-save-file-examnet_pdf"]')).to_be_visible()


def _assert_report_surface(page: Page) -> None:
    expect(page.locator('[data-test="exam-converter-report-summary"]')).to_be_visible()
    expect(page.locator('[data-test="exam-converter-selected-question-detail"]')).to_have_count(0)


def main() -> int:
    """Run the Exam Converter design proof CLI."""
    artifact_dir = run_exam_converter_design_proof()
    print(f"exam-converter-design-proof: ok artifact_dir={artifact_dir}")
    return 0
