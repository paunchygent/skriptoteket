---
type: review
id: REV-PR-0400
title: "Review: PR-0400 Document Converter artifact content hygiene contract"
status: approved
owners: "agents"
created: 2026-06-28
updated: 2026-06-28
reviewer: "codex-independent-ruthless-reviewer"
prs:
  - "PR-0400"
links:
  - "ST-37-04"
  - "EPIC-37"
  - "PR-0382"
  - "PR-0385"
  - "PR-0398"
  - "PR-0399"
  - "PR-0401"
  - "PR-0403"
---

# Review: PR-0400 Document Converter Artifact Content Hygiene Contract

## TL;DR

`approved`. The Skriptoteket side of the artifact hygiene contract is narrow and
fail-closed: missing declared local project images no longer become fabricated
placeholder PDFs, real uploaded image bytes still render, and terminal
Document Converter artifacts are rejected before download/save when known dirty
markers are present.

## Findings

No blocking findings.

## Decision

`approved`

## Problem Statement

`PR-0400` tightens the Document Converter artifact-content boundary so teacher-facing
preview, download, and save surfaces do not expose generated missing-resource
placeholders, internal producer/checkpoint markers, raw ids, or private paths.
The review checked both sides of that contract: local HTML/CSS project preview
rendering must fail closed for missing declared local images while still using
real uploaded image bytes, and terminal artifact consumption must reject known
dirty markers instead of silently scrubbing them.

## Proposed Solution

Keep Sir Convert upstream cleanliness visible as a separate ownership boundary,
while Skriptoteket rejects known dirty terminal artifacts at the application
handlers that expose bytes to teacher-facing preview, download, and save
surfaces. For local HTML/CSS project previews, remove generated fallback image
bytes and fail closed when a declared local image resource has no uploaded bytes.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0400-st-37-04-document-converter-artifact-content-hygiene-contract.md` | Accepted policy decisions, scope, proof claims | 20 min |
| `docs/backlog/stories/story-37-04-app-presentation-decomposition-and-naming-reset.md` plus dependency reviews for `PR-0385`, `PR-0398`, `PR-0399`, `PR-0403` | Parent story and adjacent approved behavior | 25 min |
| `src/skriptoteket/application/curated_apps/document_converter_artifact_hygiene.py` | Narrow fail-closed artifact marker guard | 20 min |
| `src/skriptoteket/application/curated_apps/handlers/conversion_hub_document_converter.py` and `src/skriptoteket/application/curated_apps/handlers/document_converter_project_previews.py` | Download/save guard placement | 25 min |
| `src/skriptoteket/infrastructure/documents/document_converter_project_previews.py` | Missing-image policy and real uploaded asset fetch behavior | 30 min |
| Focused backend tests under `tests/unit/application/curated_apps/handlers/`, `tests/unit/infrastructure/documents/`, and `tests/unit/web/conversion_hub/` | Behavioral proof quality and coverage | 30 min |

**Total estimated time:** ~2.5 hours

- Governing docs:
  `docs/backlog/prs/pr-0400-st-37-04-document-converter-artifact-content-hygiene-contract.md`,
  `docs/backlog/stories/story-37-04-app-presentation-decomposition-and-naming-reset.md`,
  `docs/backlog/prs/pr-0401-st-37-04-document-converter-pdf-image-recovery-planning.md`,
  retained reviews for `PR-0385`, `PR-0398`, `PR-0399`, and `PR-0403`,
  `docs/index.md`, `.codex/handoff.md`, and routed repo rules.
- Implementation:
  `src/skriptoteket/application/curated_apps/document_converter_artifact_hygiene.py`,
  `src/skriptoteket/application/curated_apps/handlers/conversion_hub_document_converter.py`,
  `src/skriptoteket/application/curated_apps/handlers/document_converter_project_previews.py`,
  and `src/skriptoteket/infrastructure/documents/document_converter_project_previews.py`.
- Tests:
  focused artifact hygiene, project-preview handler, renderer, producer-routing,
  and web API unit tests listed below.

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Missing declared local HTML/CSS project images fail closed. | Prevents fabricated placeholder content from becoming source-looking artifact content. | [x] |
| Undeclared uploaded image bytes are not used. | Preserves the `PR-0382` manifest-declared project contract. | [x] |
| Skriptoteket rejects known dirty terminal markers instead of scrubbing them. | Keeps upstream Sir Convert cleanliness visible and avoids a broad tolerant sanitizer. | [x] |
| `/artifact/partial` stays non-teacher-facing in Skriptoteket. | Partial/checkpoint artifacts are diagnostic unless a future sanitized export contract exists. | [x] |
| PDF image recovery remains out of scope and planned under `PR-0401`. | Real image recovery needs a governed recovery manifest/byte contract. | [x] |

## Review Checklist

- [x] Governing PR and story authority are present.
- [x] Accepted policy choices are recorded in `PR-0400`.
- [x] Missing declared local images fail closed without generated placeholder bytes.
- [x] Real uploaded image bytes still resolve through the project asset fetcher.
- [x] Undeclared upload bytes remain rejected by manifest validation.
- [x] Dirty terminal artifacts fail before Document Converter download/save and
      project-preview download/save.
- [x] The guard is narrow and fail-closed, not a broad scrubber.
- [x] `PR-0401` carries the PDF image-recovery follow-up.
- [x] Tests prove behavior at renderer, application-handler, and API boundaries.
- [x] File sizes remain below the repo limit.

## Review Notes

- Missing declared local project images now fail closed through the WeasyPrint
  fetch boundary and are mapped to `DomainError` at the renderer boundary.
- Undeclared image bytes remain rejected by the manifest/file-set contract; the
  implementation did not add bundle discovery or fallback byte selection.
- Blocked external, private, nested, or malformed image/style/font references no
  longer generate `project:///__missing_asset__...` URLs or visible Swedish
  placeholder PNGs.
- The new application-layer guard is narrow and fail-closed: it rejects known
  dirty markers in filenames, content types, decoded artifact bytes, and text-like
  ZIP members before Document Converter download/save and project-preview
  download/save expose bytes to teachers.
- `/artifact/partial` is not exposed as a Skriptoteket teacher-facing Document
  Converter route in this repo.
- `PR-0401` correctly keeps PDF image recovery out of this implementation slice.
- The docs distinguish Skriptoteket's fail-closed consumer boundary from Sir
  Convert's upstream responsibility for source-derived or blank title/core
  properties and checkpoint-free final artifacts.

## Review Feedback

**Reviewer:** `codex-independent-ruthless-reviewer`
**Date:** `2026-06-28`
**Verdict:** `approved`

### Required Changes

None.

### Suggestions (Optional)

- Keep upstream Sir Convert title/core-property cleanup tracked outside this
  repo's fail-closed consumer boundary. The current Skriptoteket proof does not
  and should not pretend to sanitize upstream terminal artifacts.

### Decision Approvals

- [x] Missing declared local images fail closed.
- [x] Manifest-declared project image bytes remain the only local image bytes used.
- [x] No synthesized document title fallback is accepted in the upstream policy.
- [x] Partial artifacts stay diagnostic/operator-facing only.
- [x] PDF image recovery remains a planned follow-up under `PR-0401`.

## Verification Commands

- `sed -n '1,260p' AGENTS.md`
- `sed -n '1,260p' /Users/olofs_mba/Documents/Repos/skill-repository/skills/agent-docs-governance/SKILL.md`
- `sed -n '1,320p' /Users/olofs_mba/Documents/Repos/skill-repository/skills/testing/SKILL.md`
- `sed -n '1,320p' /Users/olofs_mba/Documents/Repos/skill-repository/skills/ruthless-code-review/SKILL.md`
- `sed -n '1,280p' .codex/skills/skriptoteket-testing/SKILL.md`
- `sed -n '1,260p' /Users/olofs_mba/Documents/Repos/skill-repository/skills/agent-docs-governance/references/skriptoteket.md`
- `sed -n '1,260p' /Users/olofs_mba/Documents/Repos/skill-repository/skills/ruthless-code-review/references/forbidden-patterns.md`
- `sed -n '1,260p' .codex/skills/skriptoteket-testing/references/backend-pytest.md`
- `sed -n '1,240p' docs/index.md`
- `sed -n '1,220p' .codex/handoff.md`
- `sed -n '1,260p' docs/backlog/prs/pr-0400-st-37-04-document-converter-artifact-content-hygiene-contract.md`
- `sed -n '1,300p' docs/backlog/stories/story-37-04-app-presentation-decomposition-and-naming-reset.md`
- `sed -n '1,260p' .codex/rules/000-rule-index.md`
- `sed -n '1,260p' .codex/skills/skriptoteket-backend-dev/SKILL.md`
- `sed -n '1,260p' .codex/rules/020-monolith-architecture.md`
- `sed -n '1,260p' .codex/rules/025-curated-apps.md`
- `sed -n '1,260p' .codex/rules/040-fastapi-blueprint.md`
- `sed -n '1,260p' .codex/rules/042-async-di-patterns.md`
- `sed -n '1,260p' .codex/rules/048-error-handling.md`
- `sed -n '1,280p' .codex/rules/050-python-standards.md`
- `sed -n '1,280p' .codex/rules/070-testing-standards.md`
- `sed -n '1,240p' .codex/rules/096-review-workflow.md`
- `sed -n '1,280p' docs/runbooks/runbook-testing.md`
- `git status --short`
- `git diff --stat`
- `git diff -- src/skriptoteket/application/curated_apps/handlers/conversion_hub_document_converter.py`
- `git diff -- src/skriptoteket/application/curated_apps/handlers/document_converter_project_previews.py`
- `git diff -- src/skriptoteket/infrastructure/documents/document_converter_project_previews.py`
- `nl -ba src/skriptoteket/application/curated_apps/document_converter_artifact_hygiene.py | sed -n '1,260p'`
- `nl -ba tests/unit/application/curated_apps/handlers/test_document_converter_artifact_hygiene.py | sed -n '1,320p'`
- `nl -ba tests/unit/application/curated_apps/handlers/test_document_converter_project_preview_hygiene.py | sed -n '1,320p'`
- `wc -l src/skriptoteket/application/curated_apps/document_converter_artifact_hygiene.py src/skriptoteket/application/curated_apps/handlers/conversion_hub_document_converter.py src/skriptoteket/application/curated_apps/handlers/document_converter_project_previews.py src/skriptoteket/infrastructure/documents/document_converter_project_previews.py tests/unit/application/curated_apps/handlers/test_document_converter_artifact_hygiene.py tests/unit/application/curated_apps/handlers/test_document_converter_project_preview_hygiene.py tests/unit/infrastructure/documents/test_document_converter_project_previews.py tests/unit/infrastructure/documents/test_document_converter_project_renderer_best_effort.py`
- `pdm run test tests/unit/infrastructure/documents/test_document_converter_project_previews.py tests/unit/infrastructure/documents/test_document_converter_project_renderer_best_effort.py`
  passed: `28 passed`.
- `pdm run test tests/unit/application/curated_apps/handlers/test_document_converter_artifact_saves.py tests/unit/application/curated_apps/handlers/test_document_converter_artifact_hygiene.py tests/unit/application/curated_apps/handlers/test_document_converter_project_previews.py tests/unit/application/curated_apps/handlers/test_document_converter_project_preview_hygiene.py`
  passed: `20 passed`.
- `pdm run test tests/unit/web/conversion_hub/test_apps_document_converter_api.py tests/unit/application/curated_apps/handlers/test_document_converter_producer_routing.py tests/unit/application/curated_apps/handlers/test_document_converter_project_previews.py tests/unit/application/curated_apps/handlers/test_document_converter_project_preview_hygiene.py tests/unit/application/curated_apps/handlers/test_document_converter_artifact_saves.py tests/unit/application/curated_apps/handlers/test_document_converter_artifact_hygiene.py`
  passed: `39 passed`.
- `pdm run lint` passed.
- `pdm run typecheck` passed.
- `pdm run docs-validate` passed.
- `pdm run handoff-validate` passed.
- `git diff --check` passed.

## Residual Risks

- This review did not run live authenticated browser proof because the PR-0400
  patch is backend/application/infrastructure plus docs/tests, and no frontend
  source changed.
- The guard proves Skriptoteket rejects known dirty raw/text/ZIP markers before
  teacher-facing exposure. It does not prove upstream Sir Convert has already
  implemented blank-title/core-properties cleanup for source documents with no
  YAML title or H1; that remains a service-owned cleanliness follow-up.
- The focused PDF marker guard is intentionally narrow and is not a general
  semantic PDF text extractor. That matches the PR's "no broad scrubber" policy.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0400` | Created the retained independent review record for PR-0400. |
