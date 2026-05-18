---
type: review
id: REV-ST-21-04
title: "Review: Exam Converter durable teacher correction sessions"
status: approved
owners: "agents"
created: 2026-05-18
updated: 2026-05-19
reviewer: "Codex"
stories:
  - ST-21-04
adrs:
  - ADR-0087
links:
  - EPIC-21
  - ST-21-03
  - PR-0332
  - REV-PR-0332
---

## TL;DR

`ADR-0087` has the right high-level ownership split and now supplies the missing
aggregate semantics needed before `ST-21-04` task creation: Skriptoteket owns
durable authenticated correction-session truth, Sir Convert remains a stateless
deterministic applicator, and `PR-0332` must not claim durable workflow
stability. The 2026-05-18 re-review approves the remediated ADR/story contract.

## Problem Statement

Authenticated Exam Converter corrections need to survive navigation, reload,
later projection, and export without relying on browser-local state or treating
a stateless Sir Convert apply response as persisted truth. This review checks
whether `ADR-0087` is precise enough to unblock `ST-21-04` implementation tasks.

## Proposed Solution

Persist source-bound correction intents in Skriptoteket for authenticated local
Conversion Hub jobs, then replay the complete supported persisted set through
the HuleEdu Gateway unified Sir Convert apply edge for projection and export.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/adr/adr-0087-exam-converter-durable-correction-sessions-with-stateless-apply.md` | Durable-session decision boundary | 15 min |
| `docs/backlog/stories/story-21-04-exam-converter-durable-teacher-correction-sessions.md` | Story gate and candidate task chain | 10 min |
| `docs/adr/adr-0086-exam-converter-teacher-owned-correction-overlay-boundary.md` | Existing source-bound correction invariant | 10 min |
| `docs/backlog/prs/pr-0332-st-21-03-exam-converter-teacher-owned-correction-overlay-contract.md` | Non-durable correction overlay slice boundary | 10 min |
| `frontend/apps/skriptoteket/src/api/sirConvertOpenapi.d.ts` | Current producer-issued correction source-state vocabulary | 10 min |

**Total estimated time:** ~55 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Skriptoteket owns durable authenticated correction-session truth | Correct product aggregate boundary for reload/navigation stability | [x] |
| Sir Convert remains stateless and applies submitted correction batches | Preserves producer/application separation and avoids hidden upstream persistence claims | [x] |
| Browser state is draft/focus only | Prevents local state from masquerading as applied or durable truth | [x] |
| Matching correction remains blocked until Sir Convert Task 332 and a later approved slice | Keeps unsupported matching producer state out of the current durable contract | [x] |
| The correction-session aggregate has complete active-set semantics | Required before implementation; now defined through current-set invariants | [x] |
| Review decisions and candidate suppression have explicit durable ownership | Required before reload/export can be trusted; now persisted in this aggregate | [x] |
| Persisted binding material matches the exact producer-issued source-state contract | Required to avoid replay safety drift; now tied to producer-issued `source_binding` fields | [x] |

## Review Checklist

- [x] Scope is bounded and appropriate
- [x] Acceptance criteria or proof obligations are reviewable
- [x] Risks and structural fault lines are called out explicitly
- [x] Verification plan matches the claimed contract

## Review Feedback

**Reviewer:** Codex
**Date:** 2026-05-18
**Verdict:** changes_requested

### Original Required Changes

1. `ADR-0087` must define current-set aggregate semantics before implementation
   tasks are unblocked. The ADR lists persisted kinds at
   `docs/adr/adr-0087-exam-converter-durable-correction-sessions-with-stateless-apply.md:63`,
   but does not define uniqueness, supersession, deletion/revert, replay order,
   or conflict behavior. Add explicit invariants for one active intent per
   correction target, deterministic replay ordering, replace/delete semantics,
   and session-level optimistic concurrency with `409` behavior.
2. `ADR-0087` must decide durable ownership for `review_decision` and
   `candidate_suppression`. The persisted intent list at
   `docs/adr/adr-0087-exam-converter-durable-correction-sessions-with-stateless-apply.md:65`
   includes point, choice, gap/open-cloze, and text patches, but excludes the
   source-bound review-decision and candidate-suppression shapes recognized by
   `ADR-0086` and the current unified apply contract. Either include them as
   durable session intents or explicitly assign them to a separate governed
   aggregate/story so reload cannot resurrect rejected suggestions or lose
   accepted-current-state export decisions.
3. `ADR-0087` must align binding terminology with the current producer-issued
   source-state contract. The binding list at
   `docs/adr/adr-0087-exam-converter-durable-correction-sessions-with-stateless-apply.md:75`
   says "source authoring-state SHA-256 or equivalent producer fingerprint",
   while the generated Sir Convert contract exposes `source_state_sha256`,
   `source_state_signature`, `source_authoring_schema_version`, optional
   `source_file_sha256`, and per-item source fingerprints. Persist the exact
   producer-issued `source_binding` fields plus item id, sequence, item type,
   and source item fingerprint, or explicitly justify any renamed durable field.
4. `ADR-0087` must update the stale `ST-21-04` creation wording. The consequence
   at
   `docs/adr/adr-0087-exam-converter-durable-correction-sessions-with-stateless-apply.md:105`
   says a new story is required, but `ST-21-04` already exists and is blocked.
   Reword this to say `ST-21-04` remains blocked until the ADR is accepted.

### Proof Requirements

- Backend aggregate tests for uniqueness, replace/delete, replay ordering, and
  optimistic-concurrency conflicts.
- Repository and migration tests proving owner-scoped durable correction-session
  persistence and active-intent constraints.
- API tests proving authenticated owner scoping, stale-source rejection, and
  `409` conflict behavior.
- Replay tests proving Skriptoteket submits the complete supported persisted set
  through HuleEdu Gateway and renders only Sir Convert replayed effective state.
- Browser proof showing multiple committed corrections survive navigation and
  reload from backend readback plus Sir Convert replay, not component-local
  state.

### Suggestions (Optional)

- Add a compact "Aggregate Invariants" subsection to `ADR-0087` before the
  replay algorithm.
- Add a short table that maps every unified correction entry kind to one of:
  persisted in this aggregate, blocked, or owned by a separate future story.

### Remediation Applied

2026-05-18 documentation remediation updated `ADR-0087` and `ST-21-04` to
address the retained findings without unblocking implementation before ADR
acceptance:

- `ADR-0087` now defines the correction session as a current-set aggregate with
  one active intent per correction target, deterministic replay ordering,
  replace/delete semantics, incompatible active-intent rejection, and
  session-version `409 Conflict` behavior.
- `ADR-0087` now includes `review_decision` and `candidate_suppression` as
  durable source-bound session intents, while keeping
  `manual_matching_answer_key` blocked until a later approved matching slice.
- `ADR-0087` now requires persisting the exact producer-issued
  `source_binding` fields: `source_authoring_schema_version`, optional
  `source_bundle_id`, optional `source_file_sha256`, `source_state_sha256`, and
  `source_state_signature`, plus per-item binding material.
- `ADR-0087` now states that `ST-21-04` remains blocked until ADR acceptance.
- `ST-21-04` now mirrors the aggregate invariants, durable review/candidate
  semantics, exact source-binding persistence, and candidate implementation
  proof obligations.

This remediation does not self-approve the review. A separate re-review should
decide whether `ADR-0087` is ready to accept and whether `ST-21-04`
implementation task creation may start.

### 2026-05-18 Re-review After Remediation

**Reviewer:** Codex
**Verdict:** approved

The retained blockers are resolved in the current `ADR-0087` and `ST-21-04`
documents:

1. Current-set aggregate semantics are now explicit. `ADR-0087` defines one
   active intent per correction target, duplicate active-target rejection,
   replace/delete behavior, deterministic replay ordering, incompatible
   active-intent rejection, and expected session-version `409 Conflict`
   behavior before implementation task creation.
2. `review_decision` and `candidate_suppression` now have durable ownership in
   the correction-session aggregate. The ADR also keeps
   `manual_matching_answer_key` blocked until Sir Convert Task 332 and a later
   accepted implementation slice.
3. Binding terminology now matches the producer-issued source-state boundary.
   The ADR requires persistence of the exact `source_binding` fields:
   `source_authoring_schema_version`, optional `source_bundle_id`, optional
   `source_file_sha256`, `source_state_sha256`, and
   `source_state_signature`, plus per-item binding material.
4. The stale story wording is fixed. The ADR now says `ST-21-04` remains blocked
   until ADR acceptance instead of saying the story still needs to be created.

`ST-21-04` mirrors the remediated decision in acceptance criteria, scope, and
candidate task chain. The review approval is for the governed ADR/story
contract. The user-lead accepted `ADR-0087` on 2026-05-19, so the implementation
task creation gate is now satisfied.

### Decision Approvals

- [x] Approve `ADR-0087` for user-lead acceptance.
- [x] Unblock `ST-21-04` implementation PR task creation after `ADR-0087` is
  accepted.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-ST-21-04` | Initial retained review created with `changes_requested`. |
| 2 | `ADR-0087` | Added current-set aggregate invariants, unified correction-kind ownership, exact source-binding persistence, and proof obligations. |
| 3 | `ST-21-04` | Aligned story scope, acceptance criteria, and candidate task chain with the ADR remediation. |
| 4 | `REV-ST-21-04` | Re-review approved the remediated ADR/story contract before later user-lead acceptance. |
| 5 | `ADR-0087`, `ST-21-04` | User-lead accepted `ADR-0087`, satisfying the gate for ordered `ST-21-04` implementation PR task creation. |
