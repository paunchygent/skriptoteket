---
type: review
id: REV-PR-0332
title: "Review: Teacher-owned correction overlay contract"
status: approved
owners: "agents"
created: 2026-05-17
updated: 2026-05-19
reviewer: "Codex"
prs:
  - PR-0332
adrs:
  - ADR-0086
  - ADR-0087
links:
  - EPIC-21
  - ST-21-03
  - ST-21-04
  - REF-exam-converter-reviewed-ai-facit-contract-map-pr-0331
---

## TL;DR

`ADR-0086` names an acceptable overlay boundary: teacher corrections must go
through source-bound Sir Convert apply and returned effective IR/artifact
evidence, not browser-local state or parser mutation. This retained review no
longer treats `PR-0332` as owner of durable correction-session persistence.
Accepted `ADR-0087` and ready `ST-21-04` now own the architecture where
Skriptoteket persists source-bound correction intents and replays the complete
supported set through stateless Sir Convert apply.

## Problem Statement

Teachers need to correct prompts, stems, points, choice keys, matching keys, and
gapped/open-cloze accepted values before generating final PDF/QTI artifacts.
This review checks whether `ADR-0086` is strong enough to govern that product
boundary before implementation begins.

## Proposed Solution

Use a teacher-owned, source-bound overlay submitted by Skriptoteket and applied
by Sir Convert into effective renderer input. Keep parser-owned source IR
immutable, and derive readiness/download state only from the returned Sir Convert
bundle.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/adr/adr-0086-exam-converter-teacher-owned-correction-overlay-boundary.md` | Decision boundary | 10 min |
| `docs/backlog/prs/pr-0332-st-21-03-exam-converter-teacher-owned-correction-overlay-contract.md` | Implementation authority | 10 min |
| `docs/backlog/stories/story-21-03-exam-converter-public-and-authenticated-artifact-lanes.md` | Parent story scope | 5 min |
| `docs/reference/ref-exam-converter-reviewed-ai-facit-contract-map-pr-0331.md` | Adjacent contract map | 10 min |
| `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/converters/digiexam-migration-service-api-artifact-contract.md` | Upstream overlay contract | 10 min |

**Total estimated time:** ~45 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Corrections are overlays, not source IR mutation | Preserves parser provenance and keeps rendering authority in Sir Convert | [x] |
| Browser-local edits never unlock downloads | Prevents fake success and stale local readiness | [x] |
| Returned effective IR/artifact evidence is authoritative | Keeps UI state downstream of the producer bundle | [x] |
| Teacher-edited AI suggestions use reviewed-completion lineage | Correct provenance split when source binding and item-shape rules are exact | [x] |
| Teacher-authored corrections use non-advisory overlay fields | Correct separation for Task 333-supported non-matching correction families | [x] |

## Review Checklist

- [x] Scope is bounded and appropriate
- [x] Acceptance criteria or proof obligations are reviewable
- [x] Risks and structural fault lines are called out explicitly
- [x] Verification plan matches the claimed contract

## Review Feedback

**Reviewer:** Codex
**Date:** 2026-05-17
**Verdict:** changes_requested

### Required Changes

1. `ADR-0086` must define the source-binding invariant, not only say
   "source-bound overlay". The decision needs to require at least
   `source_file_sha256`, `source_ir_schema_version`, `source_ir_sha256`, item ID,
   sequence, item type, and `source_item_fingerprint` binding, with stale or
   mismatched overlays failing before rendering.
2. `ADR-0086` must replace conditional support wording with an explicit overlay
   capability matrix for the first implementable slice: `effective_item_patch`,
   `manual_answer_key`, `reviewed_completion_answer_key`, and
   `review_decision`, including which item types are supported now, which require
   upstream Sir Convert tasks, and which UI controls must stay absent/blocked.
3. `ADR-0086` must decide rejection/global-rejection semantics. It cannot merely
   say rejection must be explicit before artifact generation; it must say whether
   rejection means candidate-only suppression, manual-unkeyed accepted-current
   state, a blocked target, or a separate review-decision overlay result.
4. `ADR-0086` must define the proof contract for effective IR, PDF, and QTI per
   correction shape. The proof must verify that corrected values reach generated
   artifacts, and that internal diagnostics, raw overlay JSON, provider prompts,
   student-result data, scores, and identity markers are not emitted.
5. `ADR-0086` must link to `PR-0332` and the retained review record so the
   proposed decision and implementation authority cannot drift apart.

### Suggestions (Optional)

- Add a short "Minimum accepted implementation slice" section to `ADR-0086`.
  This would make it clear whether `PR-0332` starts with AI-lineage edits,
  teacher-authored manual keys, visible-content patches, or a smaller supported
  subset.
- Add a "Still upstream" section naming exact Sir Convert tasks or contracts
  when matching/open-cloze behavior is source-neutral rather than DigiExam
  adapter-local.

### Decision Approvals

- [ ] Accept `ADR-0086` as written.
- [ ] Unblock `PR-0332` implementation.

### 2026-05-17 Re-review After Changes

**Reviewer:** Codex
**Verdict:** changes_requested

The remediation resolves the original binding, capability-matrix,
rejection-semantics, artifact-proof, and review-link blockers in principle.
`ADR-0086` now defines the binding invariant, source-bound failure behavior, a
four-field overlay capability matrix, candidate-only rejection semantics, and
PDF/QTI plus forbidden-leakage proof obligations.

One blocker remains:

1. `ADR-0086` and `PR-0332` still promise point correction as part of the
   teacher-owned workflow, but the capability matrix blocks `scoring policy` in
   `effective_item_patch` and does not classify points under any other overlay
   field or upstream-required lane. Decide this explicitly before approval:
   either remove points from the accepted first correction boundary, classify
   point correction as an upstream-required contract with a named follow-up
   dependency, or define the exact supported overlay field/proof contract for
   point changes. Until then, implementers can either build a local points UI
   with no valid producer contract or silently drop a promised correction target.

Decision approvals remain blocked:

- [ ] Accept `ADR-0086` as written.
- [ ] Unblock `PR-0332` implementation.

### 2026-05-18 Producer Prerequisite Clarification

**Reviewer:** Codex
**Verdict:** changes_requested

User clarification: points/scoring must not be absorbed into `PR-0332` as a
Skriptoteket-owned implementation detail. It must be a small Sir Convert
producer-owned task immediately before `PR-0332`.

The retained blocker is therefore narrowed to this prerequisite sequence:

1. Sir Convert Task 322 must add the dedicated source-bound points/scoring
   correction DTO, validation, effective IR/report projection, regenerated
   consumer contract, target readiness behavior, and PDF/QTI proof.
2. `ADR-0086` and `PR-0332` may then describe point correction as part of the
   full teacher correction workflow consumed by Skriptoteket.
3. `PR-0332` remains blocked from exposing point-editing UI until Task 322 has
   landed and its producer proof is available.

Decision approvals remain blocked pending that producer prerequisite:

- [ ] Accept `ADR-0086` as written.
- [ ] Unblock `PR-0332` implementation.

### 2026-05-18 Re-review After Task 322 Linkage

**Reviewer:** Codex
**Verdict:** approved

The remaining point/scoring blocker is resolved as a documentation and
governance issue. `ADR-0086` now classifies points/scoring correction as a
producer-owned prerequisite, explicitly blocks local point edits through the
existing overlay fields, and requires Sir Convert Task 322 to land before
Skriptoteket exposes point editing. `PR-0332` now removes points from the
currently supported edit promise, adds Task 322 as a dependency, requires a
producer-contract preflight, and keeps point editing blocked until the generated
consumer contract includes the dedicated source-bound DTO.

The referenced upstream task exists:
`/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/tasks/task-322-add-points-scoring-correction-producer-dto-before-pr-0332.md`.
It is scoped to the producer DTO, binding validation, effective IR/report,
target readiness, OpenAPI/consumer impact, and PDF/QTI artifact proof needed by
`PR-0332`.

The initial approval was for the corrected decision and backlog contract, not
for starting `PR-0332` implementation before Task 322 landed. The Task 322
producer and consumer-type prerequisite is now complete.

Decision approvals:

- [x] Accept `ADR-0086` as written.
- [x] Unblock `PR-0332` implementation; Sir Convert Task 322 and the
  Skriptoteket generated consumer-type preflight are complete.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0332` | Initial retained review created with `changes_requested`. |
| 2 | `ADR-0086` | Remediation added the source-binding invariant, fail-before-rendering rule, overlay capability matrix, rejection semantics, and artifact proof/leakage contract. |
| 3 | `PR-0332` | Remediation added acceptance criteria for binding, candidate rejection semantics, capability-matrix inheritance, artifact proof, and forbidden leakage. |
| 4 | `ADR-0086`, `PR-0332` | Re-review remediation classified points/scoring correction as upstream-required and removed points from the implementable correction promise until a dedicated source-bound points/scoring overlay exists. |
| 5 | `REV-PR-0332` | Re-review retained `changes_requested` because point correction remains promised but not classified as supported, blocked, or upstream-required. |
| 6 | `ADR-0086`, `PR-0332`, `REV-PR-0332` | User clarification recorded points/scoring as a small Sir Convert producer-owned Task 322 immediately before `PR-0332`, with Skriptoteket point editing blocked until the producer DTO and proof land. |
| 7 | `REV-PR-0332` | Re-review approved the corrected ADR/PR contract while keeping `PR-0332` implementation blocked until Sir Convert Task 322 lands. |
| 8 | `PR-0332`, `REV-PR-0332`, `sirConvertOpenapi.d.ts` | Sir Convert Task 322 landed, Skriptoteket regenerated the generated Sir Convert DTOs, and the consumer preflight now proves `point_correction` plus `effective_point_correction` are present before point-editing implementation starts. |
| 9 | `ADR-0087`, `ST-21-04`, `PR-0332`, `REV-PR-0332` | Durable correction-session persistence was moved out of `PR-0332` into `ADR-0087` and `ST-21-04`. `PR-0332` must not implement or claim persisted teacher-correction truth. |
| 10 | `PR-0332`, `REV-PR-0332` | Closeout re-review approved the non-durable unified-correction consumer/projection slice. |
| 11 | `ADR-0087`, `ST-21-04` | User-lead accepted `ADR-0087`; ordered durable-session implementation now belongs to `PR-0333` through `PR-0337`. |

### 2026-05-18 Implementation-Contract Audit

**Reviewer:** Codex
**Verdict:** `changes_requested`

This audit evaluates whether the `PR-0332` contract document remains authoritative after significant implementation work. The approved decision boundary (REV-PR-0332 2026-05-18) is not being reopened. This audit targets the PR document itself: its structure, acceptance criteria, and claimed verification burden against the current code surface.

#### Required Changes (Implementation Audit)

1. **Strip the implementation journal from the PR contract.**
   The `Implementation Progress` section is ~250 lines of developer log. A PR contract must define scope, boundaries, and proof obligations, not replay commit history. Move the chronological progress notes to `.codex/handoff.md` or a transient tracking note. Keep only: what the PR implements, what is explicitly out of scope, and what verification closes it.

2. **Replace temporal/process acceptance criteria with testable outcomes.**
   AC #1 ("when this PR starts implementation, then..."), AC #4 ("when PR-0332 starts implementation, then..."), and AC #10 ("when this PR maps the gap, then...") are process gates, not verifiable acceptance criteria. Now that implementation has started, these are either moot or unverifiable. Replace them with concrete testable outcomes: e.g., "Given a point correction is submitted, when the Gateway request is inspected, then it carries `source_file_sha256`, `source_ir_sha256`, item id, sequence, and `source_item_fingerprint`."

3. **Add the missing unified-route producer-contract preflight.**
   The Test Plan claims: "Producer-contract preflight proving the generated Sir Convert consumer types include the unified source-state issue/apply routes and the non-matching correction entries implemented by Task 333." No such preflight exists in the current code surface. `frontend/apps/skriptoteket/src/api/sirConvertGateway/completionContract.spec.ts` guards the old DigiExam ingestion overlay types (`DigiExamOverlayPointCorrection`, `DigiExamEffectivePointCorrection`) but does not exercise the new unified v2 types (`ExamAuthoringCorrectionSourceStateIssueResult`, `ExamAuthoringCorrectionsApplyRequest`, `ExamAuthoringNonMatchingCorrectionEntry`). Add a dedicated `correctionsContract.spec.ts` or extend the existing contract spec to prove the generated unified route types are present and structurally sound before the UI consumes them.

4. **Reconcile AC #8 with the still-open live-proof item.**
   AC #8 requires: "Given corrected artifacts are inspected, when PDF/QTI proof is retained, then it verifies corrected point, choice, text, and gapped/open-cloze semantics..." The `Still open` section lists "Add live internal-browser proof" as pending. A PR cannot simultaneously claim an acceptance criterion is satisfied and list its proof as still open. Either move AC #8 to a follow-up PR, downgrade it to a stretch goal, or complete the live Playwright proof before updating the PR status toward `done`.

5. **Fix the catch-silent-failure fault line in `useExamConverterUnifiedCorrections.ts`.**
   `useExamConverterUnifiedCorrections.ts:240` contains `catch { options.failConversion(); }`. This swallows the underlying error without logging, correlation, or teacher-facing feedback. The PR does not describe error-handling behavior for correction apply failures. Add either: (a) explicit error classification and teacher-visible retry/dismiss behavior in the PR contract, or (b) a direct fix that preserves the error for diagnostics while still resetting UI state.

#### Suggestions (Optional) — Implementation Audit

- **Shrink the document.** At 345 lines, `PR-0332` is larger than many implementation modules. The contract sections (Problem, Goal, Non-goals, Implementation Plan, Test Plan, Rollback) should fit in ~120 lines. The prerequisite status addenda, superseded route archaeology, and source-neutral realignment are valuable historical context but belong in the ADR or a reference doc, not a PR contract.
- **Clarify the `effectiveMaxScore === question.pointsValue` logic.** In `useExamConverterUnifiedCorrections.ts:158`, if a teacher explicitly corrects a point value back to the original source value, no `effectivePointCorrection` is recorded. This is a subtle behavioral choice that should be either documented in the PR or normalized so any submitted point correction is always retained as an effective correction.
- **Name the dependency on `PR-0331` explicitly.** PR-0332 says "No reviewed AI-facit artifact-preservation cleanup; PR-0331 owns that." If PR-0332 assumes PR-0331 is merged or its projection fixes are present, add a dependency line so the ordering is explicit in the backlog.

#### Decision Approvals — Implementation Audit

- [x] PR-0332 contract document is refocused as scope/proof authority, not a developer journal.
- [x] All acceptance criteria are testable outcomes, not process/temporal gates.
- [x] Unified-route producer-contract preflight exists and passes.
- [x] Live Playwright proof is completed or scoped out of this PR before status moves to `done`.
- [x] Silent correction-failure fault line is addressed in contract or code.

### 2026-05-18 Implementation-Audit Remediation

**Reviewer:** Codex
**Verdict:** `addressed`

The previous implementation-audit findings are now addressed:

- `PR-0332` was refocused to an implementation scope and test plan instead of a
  chronological implementation journal.
- The acceptance criteria now describe testable outcomes for unified-route
  transport, Task 333 correction families, matching blockage, projection, draft
  gating, error diagnostics, and durable-session exclusion.
- `frontend/apps/skriptoteket/src/api/sirConvertGateway/correctionsContract.spec.ts`
  now proves generated source-state issue/apply types and Task 333
  non-matching correction entries are present while matching stays absent from
  this slice.
- PDF/QTI and durable readback proof are explicitly scoped out of `PR-0332` and
  moved to the later `ST-21-04` chain after `ADR-0087` acceptance.
- `useExamConverterUnifiedCorrections.ts` now logs the caught correction-apply
  error before failing the UI state, preserving diagnostics instead of silently
  swallowing the failure.

### 2026-05-18 Durable-Session Ownership Correction

**Reviewer:** Codex
**Verdict:** `addressed`

The implementation audit above is addressed. One additional architecture
correction is now explicit and accepted: `PR-0332` must not own durable
correction-session persistence, replay APIs, or any claim that a stateless Sir
Convert apply response is persisted truth.

The sound ownership split is:

- `PR-0332` may consume the unified non-matching source-state/apply route and
  project returned transaction-effective state.
- Accepted `ADR-0087` decides the durable workflow: Skriptoteket persists
  source-bound correction intents; Sir Convert remains stateless and applies
  the full persisted set during replay/projection/export.
- Ready `ST-21-04` owns the ordered implementation task chain after user-lead
  acceptance of `ADR-0087`.
- No implementation PR task for correction-session persistence should be
  created or marked ready from this review alone.

#### Required Changes (Durable-Session Audit)

1. Remove or reword any `PR-0332` claim that teacher corrections are persisted
   after submit. In this PR, corrected state is transaction-returned effective
   state only.
2. Keep all Skriptoteket DB persistence, correction-session aggregate design,
   replay API design, and reload/readback proof out of `PR-0332`.
3. Add `ADR-0087` and `ST-21-04` as the governing future architecture surfaces.
4. Block implementation tasks for `ST-21-04` until `ADR-0087` is accepted.

#### Decision Approvals — Durable-Session Audit

- [x] `PR-0332` no longer claims durable correction persistence.
- [x] `ADR-0087` was reviewed and accepted before `ST-21-04` implementation
  tasks were created.

### 2026-05-18 Closeout Re-review

**Reviewer:** Codex
**Verdict:** approved

`PR-0332` is approved as a non-durable unified-correction consumer/projection
slice. The retained blockers are resolved:

1. The PR contract is refocused as scope/proof authority and no longer carries
   the implementation journal.
2. Acceptance criteria are testable outcomes for unified-route usage,
   source-bound request construction, non-advisory correction fields, matching
   blockage, returned-effective-state projection, local-draft gating, error
   diagnostics, and durable-session exclusion.
3. The generated-type preflight proves the unified source-state/apply types and
   Task 333 non-matching correction entries are present.
4. PDF/QTI artifact semantics and durable reload/readback proof are explicitly
   out of scope for `PR-0332` and move to the `ST-21-04` chain authorized by
   accepted `ADR-0087`.
5. Correction apply failures preserve diagnostics before resetting UI state.
6. The retired Task 324 matching route is not retained as a compatibility path,
   and `manual_matching_answer_key` remains blocked until Task 332.

This approval does not claim persisted correction truth for `PR-0332`. It
closes only the `PR-0332` consumer/projection slice; durable correction
workflow implementation is owned by `PR-0333` through `PR-0337`.
