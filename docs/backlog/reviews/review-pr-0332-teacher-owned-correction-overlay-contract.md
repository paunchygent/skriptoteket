---
type: review
id: REV-PR-0332
title: "Review: Teacher-owned correction overlay contract"
status: approved
owners: "agents"
created: 2026-05-17
updated: 2026-05-18
reviewer: "Codex"
prs:
  - PR-0332
adrs:
  - ADR-0086
links:
  - EPIC-21
  - ST-21-03
  - REF-exam-converter-reviewed-ai-facit-contract-map-pr-0331
---

## TL;DR

`ADR-0086` now names an acceptable boundary: teacher corrections must go through
a source-bound Sir Convert overlay and returned effective IR/artifact evidence,
not browser-local state or parser mutation. The retained review approves the
corrected decision and backlog contract while keeping `PR-0332` implementation
blocked until Sir Convert Task 322 lands the points/scoring producer DTO and
proof.

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
| Corrections are overlays, not source IR mutation | Preserves parser provenance and keeps rendering authority in Sir Convert | [ ] |
| Browser-local edits never unlock downloads | Prevents fake success and stale local readiness | [ ] |
| Returned effective IR/artifact evidence is authoritative | Keeps UI state downstream of the producer bundle | [ ] |
| Teacher-edited AI suggestions use reviewed-completion lineage | Correct provenance split if source binding and item-shape rules are exact | [ ] |
| Teacher-authored corrections use non-advisory overlay fields | Correct separation, but needs explicit shape/support matrix before implementation | [ ] |

## Review Checklist

- [x] Scope is bounded and appropriate
- [ ] Acceptance criteria or proof obligations are reviewable
- [x] Risks and structural fault lines are called out explicitly
- [ ] Verification plan matches the claimed contract

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
