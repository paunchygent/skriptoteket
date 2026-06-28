---
type: pr
id: PR-0399
title: "ST-37-04 Sir Convert v2 status vocabulary contract"
status: done
owners: "agents"
created: 2026-06-27
updated: 2026-06-28
stories:
  - "ST-37-04"
tags:
  - backend
  - contracts
  - sir-convert
  - observability
dependencies:
  - "PR-0381"
  - "PR-0376"
acceptance_criteria:
  - "Given Skriptoteket consumes Sir Convert v2 job state, when code is committed, then the boundary uses an explicit Sir Convert v2 status vocabulary instead of free-form status strings."
  - "Given Sir Convert v2 exposes the canonical job statuses `queued`, `running`, `succeeded`, `failed`, and `canceled`, when Skriptoteket translates upstream state, then every upstream status is exhaustively mapped to a local product state."
  - "Given Sir Convert changes or emits an unknown job status, when Skriptoteket parses that response, then parsing fails closed with redacted operator evidence instead of silently accepting vocabulary drift."
  - "Given deploy or proof checks run, when the retained Sir Convert v2 status contract differs from the committed/canonical vocabulary, then the drift check fails before the app can claim conversion readiness."
  - "Given adjacent Sir Convert consumers exist in Skriptoteket, when they poll or receive upstream jobs, then they consume the same typed vocabulary rather than reintroducing route-local string handling."
---

# PR-0399: ST-37-04 Sir Convert v2 Status Vocabulary Contract

## Problem

`PR-0398` production evidence showed Skriptoteket rejected Sir Convert's
upstream `running` job status during Document Converter polling. A tolerant
string alias such as `running -> processing` fixes the symptom but accepts
cross-service vocabulary drift. The boundary needs an enforceable shared
vocabulary so drift is caught at commit and deploy/proof time.

## Goal

Persist and enforce the Sir Convert v2 job-status vocabulary at the
Skriptoteket/Sir Convert boundary:

- Sir Convert upstream vocabulary: `queued`, `running`, `succeeded`, `failed`,
  `canceled`.
- Skriptoteket product vocabulary may remain `submitted`, `queued`,
  `processing`, `succeeded`, `failed`, `canceled`.
- Translation from upstream to product state is explicit and exhaustive.
- Unknown upstream values fail closed with operator-safe evidence.

## Non-goals

- No broad Sir Convert API client rewrite.
- No change to Sir Convert itself unless a separate Sir Convert task is created.
- No tolerant synonyms or compatibility aliases for unknown status strings.
- No production deploy in this slice unless explicitly requested after review.
- No frontend preview or layout work; `PR-0398` owns Document Converter UX.

## Implementation Plan

1. Add a typed Sir Convert v2 upstream job-status enum at the protocol/client
   boundary.
2. Parse Sir Convert HTTP responses into the typed enum immediately; unknown
   values raise `DomainError(ErrorCode.SERVICE_UNAVAILABLE)` with redacted
   details.
3. Replace application-layer free-form status parsing with an exhaustive
   upstream-to-local mapping function.
4. Update adjacent Sir Convert consumers and tests so they use the typed
   upstream vocabulary instead of route-local strings.
5. Add a retained contract fixture or schema-derived proof that the local enum
   matches Sir Convert v2's committed/canonical status vocabulary.
6. Add a deploy/proof-friendly drift check command or test path that can be run
   before conversion readiness is claimed.

## Test Plan

- Red-first boundary test proving unknown upstream job status fails closed at
  parse/client boundary.
- Focused tests proving every Sir Convert v2 upstream status maps to one local
  product state and the mapping covers all enum values.
- Contract fixture/schema drift test for the Sir Convert v2 status vocabulary.
- Focused tests for Document Converter, public Exam Converter, and transcript
  formatter paths that poll or consume Sir Convert job status.
- `pdm run lint`
- `pdm run typecheck`
- Relevant focused backend tests.
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Progress

- Created after the first `PR-0398` remediation pass exposed a real
  cross-service vocabulary defect and the user rejected tolerant aliasing as the
  durable architecture.
- Implemented typed Sir Convert v2 job-status propagation through the protocol,
  generic v2 client, public Exam Converter client, transcript formatter
  producer, and application consumers.
- Replaced application-layer free-form status parsing with explicit
  enum-to-enum mappings; `running` now maps to local `processing` only through
  typed Sir Convert status translation.
- Added retained fixture coverage for the Sir Convert v2 status vocabulary and
  focused unknown-status fail-closed coverage for generic, public Exam Converter,
  and transcript formatter clients.

## Verification Notes

- Pre-existing redirection evidence from `PR-0398`: the rejected alias-removal
  pass failed collection for the focused contract tests because
  `SirConvertJobStatusV2` did not exist yet.
- This implementation subagent inherited a partially green worktree; the first
  focused status-contract run already passed before the final compliance repair.
- Green local contract evidence:
  `pdm run test tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_sir_convert_client_v2.py tests/unit/application/curated_apps/test_conversion_hub_status_mapping.py`
  passed with `12 passed`.
- Green adjacent client evidence:
  `pdm run test tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_sir_convert_transcript_formatter_producer.py tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_public_exam_converter_upstream_clients.py`
  passed with `6 passed`.
- Green application-consumer evidence:
  `pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_jobs.py tests/unit/application/curated_apps/handlers/test_document_converter_artifact_saves.py tests/unit/application/curated_apps/handlers/test_document_converter_producer_routing.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_exports.py tests/unit/web/test_public_apps_exam_converter_runtime.py`
  passed with `40 passed`.

## Rollback Plan

Revert the contract enum, mapping, and drift-check changes to restore the prior
free-form status parsing. This reopens the production conversion failure and is
not acceptable as a final product state.
