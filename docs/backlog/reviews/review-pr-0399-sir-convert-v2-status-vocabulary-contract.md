---
type: review
id: REV-PR-0399
title: "Review: PR-0399 Sir Convert v2 status vocabulary contract"
status: approved
owners: "agents"
created: 2026-06-27
updated: 2026-06-27
reviewer: "codex-independent-reviewer-a"
prs:
  - "PR-0399"
links:
  - "ST-37-04"
  - "EPIC-37"
  - "PR-0398"
---

# Review: PR-0399 Sir Convert v2 Status Vocabulary Contract

## TL;DR

Focused backend review completed for the PR-0399 status-vocabulary slice only.
Within that scope, I did not find a remaining tolerant alias, fail-open status
parse path, or unproved adjacent consumer. The typed Sir Convert v2 vocabulary
is propagated consistently through the shared protocol, infrastructure clients,
application mappings, and the scoped behavioral tests.

## Problem Statement

`PR-0399` repairs the cross-service status vocabulary defect behind the
Document Converter production failure: upstream Sir Convert v2 returned
`running`, while Skriptoteket still depended on free-form string handling.
This review checks whether the backend contract now fails closed on unknown
upstream values, keeps one canonical typed vocabulary, and removes local
string normalization from adjacent consumers.

## Proposed Solution

Define one typed Sir Convert v2 upstream enum, parse it at the shared client
boundary, map it exhaustively into product-owned lifecycles for Conversion Hub
and public Exam Converter, remove route-local status normalization, and prove
the contract with retained fixture plus focused boundary/consumer tests.

## Artifacts to Review

### Governing docs

- `docs/backlog/prs/pr-0399-st-37-04-sir-convert-v2-status-vocabulary-contract.md`
- `docs/backlog/prs/pr-0398-st-37-04-document-converter-production-conversion-and-preview-zoom-remediation.md`
- `docs/index.md`
- `.codex/handoff.md`

### Backend contract files

- `src/skriptoteket/protocols/sir_convert_a_lot_v2.py`
- `src/skriptoteket/protocols/conversion_hub.py`
- `src/skriptoteket/protocols/public_exam_converter.py`
- `src/skriptoteket/application/curated_apps/conversion_hub.py`
- `src/skriptoteket/application/curated_apps/public_exam_converter.py`
- `src/skriptoteket/application/curated_apps/handlers/conversion_hub_jobs.py`
- `src/skriptoteket/application/curated_apps/handlers/conversion_hub_document_converter.py`
- `src/skriptoteket/application/curated_apps/handlers/document_converter_jobs.py`
- `src/skriptoteket/application/curated_apps/handlers/public_exam_converter_jobs.py`
- `src/skriptoteket/application/curated_apps/handlers/conversion_hub_transcript_formatter_export_support.py`
- `src/skriptoteket/application/curated_apps/handlers/conversion_hub_transcript_formatter_exports.py`
- `src/skriptoteket/infrastructure/curated_apps/apps/conversion_hub/sir_convert_client_v2.py`
- `src/skriptoteket/infrastructure/curated_apps/apps/conversion_hub/public_exam_converter_sir_convert_client_v2.py`
- `src/skriptoteket/infrastructure/curated_apps/apps/conversion_hub/sir_convert_transcript_formatter_producer.py`

### Contract and regression tests

- `tests/fixtures/sir_convert_a_lot_v2_job_status_contract.json`
- `tests/unit/application/curated_apps/test_conversion_hub_status_mapping.py`
- `tests/unit/application/curated_apps/handlers/test_conversion_hub_jobs.py`
- `tests/unit/application/curated_apps/handlers/test_document_converter_artifact_saves.py`
- `tests/unit/application/curated_apps/handlers/test_document_converter_producer_routing.py`
- `tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_exports.py`
- `tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_sir_convert_client_v2.py`
- `tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_public_exam_converter_upstream_clients.py`
- `tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_sir_convert_transcript_formatter_producer.py`
- `tests/unit/web/test_public_apps_exam_converter_runtime.py`

### Public contracts checked

- Sir Convert v2 upstream job-status vocabulary at the shared protocol/client boundary.
- Conversion Hub local job-status mapping.
- Public Exam Converter local job-status mapping.
- Transcript formatter producer result status contract.
- Unknown-status fail-closed behavior for generic, public, and transcript producer clients.

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Parse upstream job status into a typed enum at the shared client boundary | Prevents app-local aliases and catches vocabulary drift before product mapping | [x] |
| Keep `RUNNING -> PROCESSING` only as an explicit product mapping | Preserves local UX vocabulary without accepting free-form upstream synonyms | [x] |
| Use a retained fixture plus focused tests as the drift gate | Gives a commit-time proof path for enum-vs-contract alignment | [x] |
| Scope this review to PR-0399 backend contract work only | Avoids mixing unrelated PR-0398 frontend/browser concerns into the verdict | [x] |

## Review Checklist

- [x] Scope is bounded to PR-0399 backend contract work.
- [x] No tolerant aliases or free-form string normalization remain at the app boundary in scope.
- [x] Unknown upstream statuses fail closed with bounded details.
- [x] Upstream enum values match the retained contract fixture.
- [x] Conversion Hub, public Exam Converter, and transcript formatter consumers use typed vocabulary.
- [x] Focused tests prove parser, mapping, and adjacent-consumer behavior.
- [x] Retained PR doc claims for the focused test commands matched local reruns.

## Review Feedback

**Reviewer:** `codex-independent-reviewer-a`
**Date:** `2026-06-27`
**Verdict:** `approved`

### Findings

No findings.

### Review Notes

- `src/skriptoteket/protocols/sir_convert_a_lot_v2.py` now defines the
  canonical upstream enum and a single fail-closed parser that returns
  `SERVICE_UNAVAILABLE` with bounded details for unknown values.
- `src/skriptoteket/application/curated_apps/conversion_hub.py` and
  `src/skriptoteket/application/curated_apps/public_exam_converter.py` use
  exhaustive typed mappings from `SirConvertJobStatusV2` into product-facing
  lifecycles, with `RUNNING -> PROCESSING` expressed only in that owned mapping
  layer.
- The route-local transcript formatter string helper was removed, and
  `src/skriptoteket/application/curated_apps/handlers/conversion_hub_transcript_formatter_exports.py`
  now consumes typed producer status directly.
- `tests/fixtures/sir_convert_a_lot_v2_job_status_contract.json` plus
  `tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_sir_convert_client_v2.py`
  provide the retained drift check for enum-vs-contract alignment.
- The scoped behavioral tests would fail on future vocabulary drift in the
  three important places: parser boundary, application mapping, and adjacent
  consumer refresh paths.

## Verification

- `rg -n "PR-0399|Sir Convert v2|status vocabulary|sir_convert" /Users/olofs_mba/.codex/memories/MEMORY.md`
- `git status --short`
- `git diff --name-only`
- `git diff -- src/skriptoteket/protocols/sir_convert_a_lot_v2.py src/skriptoteket/infrastructure/curated_apps/apps/conversion_hub/sir_convert_client_v2.py src/skriptoteket/protocols/conversion_hub.py src/skriptoteket/protocols/public_exam_converter.py src/skriptoteket/application/curated_apps/conversion_hub.py src/skriptoteket/application/curated_apps/public_exam_converter.py src/skriptoteket/application/curated_apps/handlers/conversion_hub_jobs.py src/skriptoteket/application/curated_apps/handlers/document_converter_jobs.py src/skriptoteket/application/curated_apps/handlers/public_exam_converter_jobs.py src/skriptoteket/application/curated_apps/handlers/conversion_hub_document_converter.py src/skriptoteket/application/curated_apps/handlers/conversion_hub_transcript_formatter_export_support.py src/skriptoteket/application/curated_apps/handlers/conversion_hub_transcript_formatter_exports.py src/skriptoteket/infrastructure/curated_apps/apps/conversion_hub/sir_convert_transcript_formatter_producer.py tests/fixtures/sir_convert_a_lot_v2_job_status_contract.json tests/unit/application/curated_apps/test_conversion_hub_status_mapping.py tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_sir_convert_client_v2.py tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_public_exam_converter_upstream_clients.py tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_sir_convert_transcript_formatter_producer.py tests/unit/application/curated_apps/handlers/test_conversion_hub_jobs.py tests/unit/application/curated_apps/handlers/test_document_converter_artifact_saves.py tests/unit/application/curated_apps/handlers/test_document_converter_producer_routing.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_exports.py tests/unit/web/test_public_apps_exam_converter_runtime.py docs/backlog/prs/pr-0399-st-37-04-sir-convert-v2-status-vocabulary-contract.md docs/index.md .codex/handoff.md`
- `rg -n "status\\.strip\\(|lower\\(\\)|cancelled|processing|from_upstream\\(|from_sir_convert_status\\(|parse_sir_convert_job_status_v2|reason_code|SirConvertJobStatusV2" src/skriptoteket/application/curated_apps src/skriptoteket/infrastructure/curated_apps/apps/conversion_hub src/skriptoteket/protocols`
- `rg -n "from_upstream\\(|status\\.strip\\(|normalized = status|cancelled|processing\\\"\\)|running -> processing|running\\s*->\\s*processing|Unsupported Conversion Hub upstream status" src/skriptoteket/application/curated_apps src/skriptoteket/infrastructure/curated_apps/apps/conversion_hub src/skriptoteket/protocols tests/unit/application/curated_apps tests/unit/infrastructure/curated_apps/apps/conversion_hub tests/unit/web/test_public_apps_exam_converter_runtime.py docs/backlog/prs/pr-0399-st-37-04-sir-convert-v2-status-vocabulary-contract.md`
- `/opt/homebrew/bin/pdm run test tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_sir_convert_client_v2.py tests/unit/application/curated_apps/test_conversion_hub_status_mapping.py` -> `12 passed in 0.54s`
- `/opt/homebrew/bin/pdm run test tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_sir_convert_transcript_formatter_producer.py tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_public_exam_converter_upstream_clients.py` -> `6 passed in 0.45s`
- `/opt/homebrew/bin/pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_jobs.py tests/unit/application/curated_apps/handlers/test_document_converter_artifact_saves.py tests/unit/application/curated_apps/handlers/test_document_converter_producer_routing.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_exports.py tests/unit/web/test_public_apps_exam_converter_runtime.py` -> `40 passed in 1.51s`

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0399` | Created the retained PR-0399 backend contract review record. |
| 2 | `REV-PR-0399` | Recorded the scoped contract review, focused verification evidence, and final verdict. |

## Residual Risks

- I did not rerun `pdm run lint`, `pdm run typecheck`, `pdm run handoff-validate`,
  or the PR-0398/frontend/browser-proof commands during this scoped backend
  review.
- The retained contract fixture is only as strong as its upstream refresh
  discipline. The current tests prove local drift against the committed fixture,
  not live Sir Convert service truth.
