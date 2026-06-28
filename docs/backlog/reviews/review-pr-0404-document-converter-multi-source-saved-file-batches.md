---
type: review
id: REV-PR-0404
title: "Review: PR-0404 Document Converter multi-source saved-file batches"
status: approved
owners: "agents"
created: 2026-06-28
updated: 2026-06-28
reviewer: "codex-independent-ruthless-reviewer"
prs:
  - "PR-0404"
links:
  - "ST-37-04"
  - "PR-0385"
  - "PR-0396"
  - "PR-0400"
---

# Review: PR-0404 Document Converter Multi-Source Saved-File Batches

## TL;DR

`approved`. The prior teacher-facing raw-job-id fallback and premature docs
closeout blockers have both been remediated. The ordered `source_refs` API
contract, backend validation, refs-only retained proof, focused tests, lint,
typecheck, build, docs, handoff, and diff hygiene gates are green for this
rereview.

## Findings

### Resolved: Missing result filenames now fail closed without job-id fallback

- `frontend/apps/skriptoteket/src/views/apps/document-converter/documentConverterSingleFileSubmission.ts:130`
- `frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts:578`
- `frontend/apps/skriptoteket/src/api/openapi.d.ts:4028`

`DocumentConverterResultArtifact.filename` remains nullable/optional in the
generated OpenAPI type, but the frontend no longer maps a missing filename to
`result.job_id`. It now trims `result_artifact.filename` and drops the artifact
when the filename is null, missing, or blank, which routes the outcome into the
generic Swedish failure state instead of rendering a backend identifier.

The new visible-behavior Vitest table covers both `filename: null` and missing
`filename`, asserting that `Konverteringen kunde inte slutföras.` is shown and
neither the submitted job id nor artifact id appears in the rendered text.

### Resolved: Docs no longer pre-close PR-0404 before independent acceptance

- `docs/backlog/prs/pr-0404-st-37-04-document-converter-multi-source-saved-file-batches.md:5`
- `docs/backlog/stories/story-37-04-app-presentation-decomposition-and-naming-reset.md:70`
- `docs/backlog/stories/story-37-04-app-presentation-decomposition-and-naming-reset.md:166`
- `.codex/handoff.md:13`
- `.codex/handoff.md:14`
- `.codex/handoff.md:149`
- `.codex/handoff.md:194`

The PR frontmatter is back to `status: in_progress`, the story checklist is
unchecked, the story note says `PR-0404` is implemented locally but not closed,
and handoff says `PR-0404` is not closed while `REV-PR-0404` awaits
rereview. With this review now approved, the overseer should re-close the PR
doc, story checklist/note, and handoff in a follow-up docs-state pass.

No blocker remains in the current docs state.

### Verified: Ordered `source_refs` replaced public `source_ref`

### Resolved: Ungoverned `source_ref` compatibility was removed

- `src/skriptoteket/application/curated_apps/document_converter.py:225`
- `src/skriptoteket/application/curated_apps/document_converter.py:231`
- `frontend/apps/skriptoteket/src/api/openapi.d.ts:7473`
- `frontend/apps/skriptoteket/src/api/openapi.d.ts:7476`
- `tests/unit/web/conversion_hub/test_apps_document_converter_saved_file_contract.py:29`

The public request DTO now requires `source_refs` and no longer defines
`source_ref`. The generated OpenAPI type exposes `source_refs` only, and the
focused contract test rejects a retired `source_ref`-only payload while
accepting an ordered two-ref batch.

### Resolved: Retained shared-auth browser proof is present

- `docs/backlog/prs/pr-0404-st-37-04-document-converter-multi-source-saved-file-batches.md:162`
- `docs/backlog/prs/pr-0404-st-37-04-document-converter-multi-source-saved-file-batches.md:204`
- `.codex/handoff.md:166`
- `.artifacts/authenticated-home-work-apps/20260628T173523Z/manifest.redacted.json`

The retained proof manifest has `status: ok` and records the compact
shared-auth route selecting two compatible saved PDFs from `Mina filer`,
reordering them to source B before source A, submitting a refs-only ordered
batch, receiving two separate Markdown outputs, downloading one Markdown
artifact, saving one result with HTTP `200`, and finding no forbidden marker
hits.

## Decision

`approved`

## Problem Statement

`PR-0385` added owner-scoped single saved-file conversion for Document
Converter. `PR-0404` deepens that surface so teachers can select multiple
compatible `Mina filer` sources, preserve visible order, and get one separate
Document Converter output per source without browser-uploading saved bytes or
promising combined output/project restore.

## Proposed Solution

The implementation extends the saved-file submission path from a single ref to
ordered refs, validates the whole batch before job creation, reads Vault bytes
server-side, reuses `CreateDocumentConverterJobsHandler`, updates the frontend
source picker to append/order/remove saved files, and keeps outputs in the
existing result/artifact selector.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0404-st-37-04-document-converter-multi-source-saved-file-batches.md` | Governing contract, remediation evidence, proof honesty | 15 min |
| `docs/backlog/stories/story-37-04-app-presentation-decomposition-and-naming-reset.md` and `PR-0385` | Parent/prior scope boundaries | 10 min |
| `src/skriptoteket/application/curated_apps/document_converter.py` and saved-source handler/API route | Backend request contract, validation, all-or-nothing behavior | 30 min |
| `frontend/apps/skriptoteket/src/views/apps/document-converter/` | UI selection/order/removal, refs-only submission, visible language | 35 min |
| Focused backend/frontend specs and retained proof manifest | Behavioral proof quality and shared-auth browser evidence | 30 min |

**Total estimated time:** ~2 hours

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Saved-file batch submission should use ordered `source_refs` only. | Prevents competing active payload shapes and keeps the batch contract clean. | [x] |
| Saved-file validation should fail the whole request before job creation. | Prevents partial conversion and preserves teacher trust in batch action semantics. | [x] |
| Each saved source should produce one separate output artifact. | Matches the PR non-goal that there is no combined/concatenated general file-conversion output. | [x] |
| Browser proof must exercise the protected shared-auth route. | Vitest/API tests cannot prove the authenticated teacher path or artifact hygiene checks. | [x] |

## Review Checklist

- [x] Governing PR, parent story, prior `PR-0385`, review workflow, routed skills, and named rules were read.
- [x] Backend reads saved bytes server-side from owner-scoped Vault refs and does not accept browser bytes for saved-file submission.
- [x] Backend validates empty, duplicate, non-Vault, cross-owner, deleted, missing-on-disk, unsupported, mixed-source-format, and over-10 batches before job creation in focused unit coverage.
- [x] Selected order is preserved into created jobs and frontend submission order.
- [x] UI supports append selection, ordering, and removal without rendering raw refs/job ids/artifact ids/producer names/paths/history/project-restore language in the inspected route.
- [x] Protected API exposes only the governed `source_refs` request contract.
- [x] Retained shared-auth browser proof for a real multi-file `Mina filer` batch exists.
- [x] Focused backend and frontend tests passed in this review.

## Review Feedback

**Reviewer:** `codex-independent-ruthless-reviewer`
**Date:** `2026-06-28`
**Verdict:** `approved`

### Required Changes

None. The prior required changes were remediated and accepted in this
rereview.

### Suggestions (Optional)

None.

### Decision Approvals

- [x] Saved-file batch submission should use ordered `source_refs` only.
- [x] Saved-file validation should fail the whole request before job creation.
- [x] Each saved source should produce one separate output artifact.
- [x] Browser proof must exercise the protected shared-auth route.

## Rereview Evidence

- `src/skriptoteket/application/curated_apps/document_converter.py:225-232`
  defines `SubmitDocumentConverterSavedFileRequest` with `source_refs` only.
- `frontend/apps/skriptoteket/src/api/openapi.d.ts:7473-7478` exposes the
  generated saved-file request type with `source_refs` only.
- `tests/unit/web/conversion_hub/test_apps_document_converter_saved_file_contract.py:29-53`
  rejects the retired `source_ref`-only request and accepts an ordered
  two-ref request.
- `.artifacts/authenticated-home-work-apps/20260628T173523Z/manifest.redacted.json`
  records the live compact shared-auth proof with two saved PDF sources,
  refs-only ordered submission, two Markdown outputs, one download, one save,
  and no forbidden marker hits.
- `.artifacts/authenticated-home-work-apps/20260628T173523Z/saved-file-batch-pr-0404-source-b-3---Markdown---20260628.md`
  exists, contains the expected seeded source-B Markdown text, and has no hits
  for the forbidden UI/artifact terms checked in rereview.

## Independent GPT-5.5 XHigh Full Worktree Review Addendum

**Reviewer:** `gpt-5.5-xhigh-ruthless-reviewer`
**Date:** `2026-06-28`
**Scope:** full dirty PR-0404 worktree, including tracked and untracked files.
**Decision:** `approved`

The full worktree review verified the main PR-0404 implementation path:

- Backend request DTO and generated OpenAPI expose ordered `source_refs` only.
- The saved-file handler validates count, duplicates, non-Vault refs,
  owner/deleted/missing metadata, missing storage bytes, unsupported types,
  mixed formats, and source-format mismatch before invoking job creation.
- Saved-file bytes are read server-side from owner-scoped Vault storage and
  handed to `CreateDocumentConverterJobsHandler` as ordered uploads.
- The frontend appends, orders, removes, and submits `Mina filer` refs in
  visible order, and the retained compact shared-auth proof records two
  separate Markdown outputs with save/download and no forbidden marker hits.

The remediation rereview accepts closeout. The UI now fails closed when a
succeeded result lacks a usable filename, and the docs/handoff state no longer
pre-closes `PR-0404` before independent review acceptance.

### Commands Run In This Addendum

- `git status --short`: showed the expected PR-0404 tracked changes and
  untracked PR/review/spec/helper files; no staging was performed.
- `git diff --stat`: inspected the tracked dirty diff scope.
- `wc -l ...`: confirmed the touched production/test modules remain inside the
  repo's rough 400-500 line budget after decomposition.
- `jq . .artifacts/authenticated-home-work-apps/20260628T173523Z/manifest.redacted.json`:
  manifest status is `ok`, with compact shared-auth saved-file batch facts.
- `sed -n '1,160p' .artifacts/authenticated-home-work-apps/20260628T173523Z/saved-file-batch-pr-0404-source-b-3---Markdown---20260628.md`:
  downloaded Markdown contains the expected source-B content.
- `rg -n "document_converter|source_ref|source_refs|artifact|producer|vault:|historik|Historik|återställ|Återställ|document-converter:|job[_:-]|/tmp|tmp|converted_document|PR-0400|Traceback|FileNotFound" .artifacts/authenticated-home-work-apps/20260628T173523Z/saved-file-batch-pr-0404-source-b-3---Markdown---20260628.md`:
  no matches.
- `/opt/homebrew/bin/pdm run test tests/unit/application/curated_apps/handlers/test_document_converter_saved_sources.py tests/unit/web/conversion_hub/test_apps_document_converter_api.py tests/unit/web/conversion_hub/test_apps_document_converter_saved_file_contract.py tests/unit/scripts/test_playwright_script_surface.py`:
  `23 passed`.
- `/opt/homebrew/bin/pdm run fe-test -- --run src/views/apps/document-converter/documentConverterFileApi.spec.ts src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts src/views/apps/document-converter/DocumentConverterView.spec.ts src/views/apps/document-converter/DocumentConverterLayoutOwnership.spec.ts src/views/apps/document-converter/DocumentConverterSavedFileBatch.spec.ts`:
  `5` files passed, `25` tests passed.
- `/opt/homebrew/bin/pdm run lint`: passed.
- `/opt/homebrew/bin/pdm run typecheck`: passed with `Success: no issues found
  in 1166 source files`.
- `/opt/homebrew/bin/pdm run fe-type-check`: passed.
- `/opt/homebrew/bin/pdm run fe-lint`: passed.
- `/opt/homebrew/bin/pdm run fe-build`: passed; existing Vite chunk-size and
  mixed dynamic/static import warnings were non-fatal.
- `/opt/homebrew/bin/pdm run docs-validate`: passed after this review update.
- `/opt/homebrew/bin/pdm run handoff-validate`: passed after this review update.
- `git diff --check`: passed after this review update.

### Commands Run In The Remediation Rereview

- `git status --short`: showed the expected dirty/untracked PR-0404 worktree;
  no staging was performed.
- `git diff -- frontend/apps/skriptoteket/src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts`:
  inspected the added null/missing filename visible-behavior coverage.
- `nl -ba frontend/apps/skriptoteket/src/views/apps/document-converter/documentConverterSingleFileSubmission.ts`:
  verified the filename is trimmed and missing/blank filenames do not fall back
  to `job_id`.
- `rg -n "source_ref|source_refs" ...`: verified active backend, OpenAPI, and
  frontend client surfaces expose `source_refs` only; `source_ref` remains only
  in tests and historical/red-first PR text.
- `jq . .artifacts/authenticated-home-work-apps/20260628T173523Z/manifest.redacted.json`:
  retained proof manifest still has `status: ok`, refs-only ordered saved-file
  batch facts, two separate outputs, save/download, and no forbidden marker
  hits.
- `rg -n "document_converter|source_ref|source_refs|artifact|producer|vault:|historik|Historik|återställ|Återställ|restore|Restore|document-converter:|job[_:-]|/tmp|tmp|converted_document|PR-0400|Traceback|FileNotFound" .artifacts/authenticated-home-work-apps/20260628T173523Z/saved-file-batch-pr-0404-source-b-3---Markdown---20260628.md`:
  returned no matches.
- `/opt/homebrew/bin/pdm run test tests/unit/application/curated_apps/handlers/test_document_converter_saved_sources.py tests/unit/web/conversion_hub/test_apps_document_converter_api.py tests/unit/web/conversion_hub/test_apps_document_converter_saved_file_contract.py tests/unit/scripts/test_playwright_script_surface.py`:
  `23 passed`.
- `/opt/homebrew/bin/pdm run fe-test -- --run src/views/apps/document-converter/documentConverterFileApi.spec.ts src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts src/views/apps/document-converter/DocumentConverterView.spec.ts src/views/apps/document-converter/DocumentConverterLayoutOwnership.spec.ts src/views/apps/document-converter/DocumentConverterSavedFileBatch.spec.ts`:
  `5` files passed, `27` tests passed.
- `/opt/homebrew/bin/pdm run lint`: passed with `All checks passed!`,
  migration-test coverage ok, and hazard shortcard guard pass.
- `/opt/homebrew/bin/pdm run typecheck`: passed with `Success: no issues found
  in 1166 source files`.
- `/opt/homebrew/bin/pdm run fe-type-check`: passed.
- `/opt/homebrew/bin/pdm run fe-lint`: passed.
- `/opt/homebrew/bin/pdm run fe-build`: passed; existing Vite chunk-size and
  mixed dynamic/static import warnings were non-fatal.
- `/opt/homebrew/bin/pdm run docs-validate`: passed after the approved review
  artifact update.
- `/opt/homebrew/bin/pdm run handoff-validate`: passed after the approved
  review artifact update.
- `git diff --check`: passed after the approved review artifact update.

## Post-Approval SRP Decomposition Rereview

- `frontend/apps/skriptoteket/src/views/apps/document-converter/useDocumentConverterSingleFile.ts`
  is now 343 lines and focuses on source-selection state, route/source loading,
  request construction, retry restoration, and route-facing refs/outcomes.
- `frontend/apps/skriptoteket/src/views/apps/document-converter/documentConverterSingleFileSubmission.ts`
  is 227 lines with a domain-purpose module header. It owns upload versus
  saved-file API submission, ordered `sourceRefs` projection, job polling,
  pending-state reporting, ready/failed outcome construction, and failed-start
  fallback outcome construction.
- `frontend/apps/skriptoteket/src/views/apps/document-converter/documentConverterSingleFileSelection.ts`
  remains 124 lines and owns source/output format helpers, labels, and generic
  list movement/removal.
- The prior line-count-only cleanup addendum is superseded. This rereview
  treats the meaningful closeout as responsibility decomposition, not shaving a
  local wrapper. Focused behavior tests, `vue-tsc`, and ESLint passed after the
  refactor, so the approval remains open.

## Verification Commands

- `sed -n '1,260p' AGENTS.md`
- `sed -n '1,260p' docs/reference/ref-review-workflow.md`
- `sed -n '1,260p' .codex/rules/096-review-workflow.md`
- `sed -n '1,260p' docs/backlog/prs/pr-0404-st-37-04-document-converter-multi-source-saved-file-batches.md`
- `sed -n '1,300p' docs/backlog/stories/story-37-04-app-presentation-decomposition-and-naming-reset.md`
- `sed -n '1,280p' docs/backlog/prs/pr-0385-st-37-04-document-converter-files-and-history-follow-up.md`
- `sed -n '1,260p' /Users/olofs_mba/Documents/Repos/skill-repository/skills/ruthless-code-review/SKILL.md`
- `sed -n '1,260p' /Users/olofs_mba/Documents/Repos/skill-repository/skills/testing/SKILL.md`
- `sed -n '1,260p' .codex/skills/skriptoteket-testing/SKILL.md`
- `sed -n '1,260p' .codex/skills/skriptoteket-backend-dev/SKILL.md`
- `sed -n '1,260p' /Users/olofs_mba/Documents/Repos/skill-repository/skills/integrated-frontend-stack/SKILL.md`
- `sed -n '1,260p' /Users/olofs_mba/Documents/Repos/skill-repository/skills/playwright-testing/SKILL.md`
- `sed -n '1,280p' /Users/olofs_mba/Documents/Repos/skill-repository/skills/ruthless-code-review/references/forbidden-patterns.md`
- `sed -n '1,260p' .codex/rules/000-rule-index.md`
- `sed -n '1,260p' .codex/rules/010-foundational-principles.md`
- `sed -n '1,280p' .codex/rules/020-monolith-architecture.md`
- `sed -n '1,260p' .codex/rules/025-curated-apps.md`
- `sed -n '1,280p' .codex/rules/040-fastapi-blueprint.md`
- `sed -n '1,260p' .codex/rules/042-async-di-patterns.md`
- `sed -n '1,260p' .codex/rules/048-error-handling.md`
- `sed -n '1,260p' .codex/rules/050-python-standards.md`
- `sed -n '1,280p' .codex/rules/070-testing-standards.md`
- `sed -n '1,260p' .codex/rules/075-browser-automation.md`
- `sed -n '1,260p' docs/runbooks/runbook-testing.md`
- `git status --short`
- `git diff --stat`
- `jq . .artifacts/authenticated-home-work-apps/20260628T173523Z/manifest.redacted.json`
- `sed -n '1,120p' .artifacts/authenticated-home-work-apps/20260628T173523Z/saved-file-batch-pr-0404-source-b-3---Markdown---20260628.md`
- `rg -n "document_converter|source_ref|source_refs|artifact|producer|vault:|historik|återställ|document-converter:" .artifacts/authenticated-home-work-apps/20260628T173523Z/saved-file-batch-pr-0404-source-b-3---Markdown---20260628.md`
  returned no matches.
- `/opt/homebrew/bin/pdm run test tests/unit/application/curated_apps/handlers/test_document_converter_saved_sources.py tests/unit/web/conversion_hub/test_apps_document_converter_api.py tests/unit/web/conversion_hub/test_apps_document_converter_saved_file_contract.py tests/unit/scripts/test_playwright_script_surface.py`
  passed: `23 passed`.
- `/opt/homebrew/bin/pdm run fe-test -- --run src/views/apps/document-converter/documentConverterFileApi.spec.ts src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts src/views/apps/document-converter/DocumentConverterView.spec.ts src/views/apps/document-converter/DocumentConverterLayoutOwnership.spec.ts src/views/apps/document-converter/DocumentConverterSavedFileBatch.spec.ts`
  passed: `5` files, `25` tests.
- `wc -l frontend/apps/skriptoteket/src/views/apps/document-converter/useDocumentConverterSingleFile.ts frontend/apps/skriptoteket/src/views/apps/document-converter/documentConverterSingleFileSubmission.ts frontend/apps/skriptoteket/src/views/apps/document-converter/documentConverterSingleFileSelection.ts`
  returned `343`, `227`, and `124`.
- `/opt/homebrew/bin/pdm run fe-test -- --run src/views/apps/document-converter/DocumentConverterSingleFileView.spec.ts src/views/apps/document-converter/DocumentConverterSavedFileBatch.spec.ts src/views/apps/document-converter/documentConverterFileApi.spec.ts`
  passed: `3` files, `15` tests.
- `/opt/homebrew/bin/pdm run fe-type-check` passed.
- `/opt/homebrew/bin/pdm run fe-lint` passed.
- `/opt/homebrew/bin/pdm run docs-validate` passed after this review update.
- `git diff --check` passed after this review update.

## Residual Risks

- The retained live proof covers the compact shared-auth viewport. Desktop and
  tablet behavior remain covered by focused frontend tests and earlier route
  proof lanes, not by this specific PR-0404 saved-file batch proof artifact.
- This rereview did not rerun a fresh live browser session; it inspected the
  retained live proof manifest and downloaded batch output, then reran focused
  backend/API/script tests, focused frontend tests, lint, typecheck, frontend
  typecheck/lint/build, docs validation, handoff validation, and diff hygiene.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0404` | Created the retained independent review record for PR-0404 with `changes_requested`. |
| 2 | `REV-PR-0404` | Updated the retained review to `approved` after verifying remediation of the public request contract and retained shared-auth proof blockers. |
| 3 | `REV-PR-0404` | Recorded a now-superseded post-approval cleanup check. |
| 4 | `REV-PR-0404` | Replaced the superseded cleanup note with SRP decomposition rereview evidence and kept the decision `approved`. |
| 5 | `REV-PR-0404` | Approved the post-remediation rereview after verifying the filename fail-closed repair, docs-state reversal, retained proof artifact, and focused gates. |
