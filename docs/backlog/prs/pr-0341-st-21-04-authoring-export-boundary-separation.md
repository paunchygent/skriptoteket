---
type: pr
id: PR-0341
title: "ST-21-04 Authoring/export boundary separation"
status: done
owners: "agents"
created: 2026-05-19
updated: 2026-05-20
stories:
  - "ST-21-04"
tags:
  - frontend
  - backend
  - conversion-hub
  - exam-converter
  - teacher-corrections
  - export-boundary
dependencies:
  - "ADR-0086"
  - "ADR-0087"
  - "PR-0338"
  - "PR-0339"
  - "PR-0340"
  - "Sir Convert Task 337"
acceptance_criteria:
  - "Given teacher authoring state is persisted, when the correction-session aggregate validates supported kinds, then it persists only source-bound authoring/candidate-review intents and no longer accepts `review_decision` or `accept_current_state_for_export` as durable authoring state."
  - "Given a teacher has not supplied required facit or poäng, when the UI renders files or actions, then missing authoring data remains a blocker and no `Skapa filer`, accepted-current-state, or manual-unkeyed export gate is offered."
  - "Given persisted correction intents are replayed, when Skriptoteket builds the Sir Convert apply request, then it sends only authoring/candidate-review correction kinds supported by the upstream contract and never sends `review_decision`."
  - "Given corrected artifacts are available, when the teacher downloads or saves PDF/QTI, then the action uses only Sir Convert replay artifact references produced from authoring corrections; export policy never mutates or masquerades as correction state."
  - "Given legacy accepted-current-state code, fixtures, docs, or tests remain in Skriptoteket, when this slice closes, then they are deleted or rewritten without shims, aliases, wrappers, or fallback compatibility paths."
  - "Given existing local correction sessions contain `review_decision` intents, when the migration/cleanup runs, then those intents are removed or deactivated so stale export policy cannot be replayed as authoring state."
---

# PR-0341: ST-21-04 Authoring/Export Boundary Separation

## Problem

`ST-21-04` made correction sessions durable, but it carried forward
`review_decision` / `accept_current_state_for_export` from the earlier
accepted-current-state workflow. That decision is an export policy choice, not
teacher-authored exam content. Persisting it beside item text, points, and
answer keys couples two concerns that must remain separate:

- authoring state: what the teacher has changed, supplied, or confirmed as exam
  content; and
- export state: what target artifacts can be produced from the current
  effective exam state.

This coupling creates a false escape hatch for incomplete authoring state:
missing keys can be treated as an export permission instead of remaining
missing until the teacher supplies real authoring data.

## Product Decision

Authoring and export are separate lanes.

- Authoring corrections may change effective exam state.
- Export requests may consume effective exam state and produce artifacts.
- Export policy must never be persisted as teacher authoring state.
- Missing answer keys remain missing until the teacher supplies keys.
- Incomplete/best-effort export is not part of the active workflow. If it is
  reintroduced later, it needs a separate export-only contract and product
  approval.

## Scope

- Remove `review_decision` / `accept_current_state_for_export` from
  Skriptoteket durable correction-session kinds, replay request building, UI
  gates, fixtures, and tests.
- Remove the accepted-current-state overlay projection path from authenticated
  Exam Converter review projection.
- Update backend aggregate conflict families, replay ordering, API types, and
  migrations/cleanup so `review_decision` cannot survive as active correction
  truth.
- Keep candidate suppression if still needed as advisory-candidate UI state; it
  is not an export policy and must not unlock artifacts.
- Keep corrected file actions gated on replay artifact references from Sir
  Convert `PR-0339`/Task 336 authority.
- Amend `ADR-0086`, `ADR-0087`, `ST-21-04`, and relevant UI/reference docs so
  accepted-current-state is no longer documented as active teacher authoring
  state.
- Coordinate with Sir Convert Task 337, which removes the upstream correction
  apply/overlay export-policy coupling.

## Non-Goals

- No new incomplete-export or best-effort export mode in this slice.
- No compatibility shim, adapter, alias, wrapper, or fallback for
  `review_decision`.
- No local Skriptoteket artifact storage.
- No fallback to original Sir Convert job artifacts after corrections.
- No matching answer-key enablement before the separate upstream matching lane.

## Implementation Plan

1. Update the correction-session domain model:
   remove `REVIEW_DECISION`, remove review-decision replay ordering, remove
   answer-key/review-decision conflict-family rules, and add a cleanup
   migration or repository-level deletion path for any existing active
   `review_decision` rows.
2. Update API/OpenAPI/frontend generated types after backend schema changes.
3. Remove accepted-current-state UI state and event flow:
   `acceptedCurrentState`, `ExamConverterReviewDecisionGate`,
   `handleAcceptCurrentState`, `applyReviewDecision`,
   `reviewDecisionIntents`, and accepted-state overlay builders/projections.
4. Update correction replay request building so the submitted set excludes
   `review_decision` and fails tests if that kind appears.
5. Rewrite file-readiness/report copy so missing facit/poäng remains a teacher
   authoring task rather than an export decision.
6. Delete or rewrite tests/fixtures that prove accepted-current-state export as
   active behavior. Keep tests that prove corrected downloads use replay
   artifact references after real authoring corrections.
7. Update docs and handoff so `PR-0337` proof runs after this separation and
   proves the clean authoring-to-replay-to-export path.

## Open Questions Closed

1. Should incomplete export remain available in the current UI?
   - Decision: no. The active workflow requires teacher-supplied facit/poäng
     before corrected PDF/QTI downloads are enabled.
2. Should `accept_current_state_for_export` remain a correction intent?
   - Decision: no. It is export policy, not authoring state.
3. Should old `review_decision` rows be interpreted for compatibility?
   - Decision: no. Clean them up or deactivate them; do not replay them.
4. Should a future best-effort/manual export mode be forbidden forever?
   - Decision: no. It may return later as an explicit export-only contract, but
     that is a separate product slice.

## Test Plan

- Backend unit tests for supported correction kinds, cleanup/migration behavior,
  deterministic replay ordering, and rejection/absence of `review_decision`.
- Frontend tests proving:
  - no accepted-current-state gate or `Skapa filer` export shortcut appears;
  - missing facit/poäng keeps file actions blocked;
  - replay requests contain only supported authoring/candidate-review kinds;
  - corrected downloads enable only from replay artifact references after real
    authoring corrections.
- Focused UI/browser proof after `PR-0337` is updated.
- Closeout gates:
  - `pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedReviewSlice.spec.ts src/views/apps/ExamConverterCorrectionSessionReplay.spec.ts src/views/apps/ExamConverterAuthenticatedFilesActionSlice.spec.ts`
  - `pdm run fe-type-check`
  - `pdm run fe-lint`
  - `pdm run fe-build`
  - `pdm run docs-validate`
  - `pdm run handoff-validate`
  - `git diff --check`

## Implementation Summary

- Removed `review_decision` from Skriptoteket correction-session domain/API
  support and regenerated Skriptoteket OpenAPI/frontend types.
- Removed the correction-intent conflict-family model because the only
  cross-kind family existed to let export decisions supersede answer keys.
- Added migration `b3e7a1c9d4f2` to deactivate active legacy
  `review_decision` rows and drop the `conflict_family` column/index.
- Deleted the accepted-current-state overlay builder and UI gate, then rewrote
  replay/file-action tests around real authoring corrections and Sir
  Convert-owned replay artifact references.
- Kept target-level export blockers in the export/file lane only; they do not
  create authoring intents or unlock downloads.

## Verification

- `pdm run openapi-export-v1`
- `pdm run fe-gen-api-types`
- `pdm run pytest tests/unit/domain/curated_apps/test_exam_converter_correction_sessions.py`
- `pdm run pytest tests/integration/infrastructure/repositories/test_exam_converter_correction_session_repository.py`
- `pdm run pytest 'tests/integration/test_migration_revision_coverage_idempotent.py::test_uncovered_migration_revision_is_idempotent[b3e7a1c9d4f2]' --override-ini addopts=''`
- `pdm run db-upgrade`
- `pdm run alembic current` reported `b3e7a1c9d4f2 (head)`.
- `pdm run fe-test -- src/views/apps/ExamConverterCorrectionSessionReplay.spec.ts src/views/apps/ExamConverterAuthenticatedFilesActionSlice.spec.ts src/views/apps/ExamConverterAuthenticatedReviewSlice.spec.ts src/views/apps/ExamConverterAuthenticatedCorrectionSlice.spec.ts src/api/sirConvertGateway/completionContract.spec.ts`
- `pdm run fe-type-check`

## Rollback Plan

Revert this PR before any follow-up proof or runtime deployment. Do not restore
accepted-current-state via a shim; if incomplete export is desired, create the
separate export-only contract task first.
