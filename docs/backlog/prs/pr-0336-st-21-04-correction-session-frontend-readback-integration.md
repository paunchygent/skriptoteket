---
type: pr
id: PR-0336
title: "ST-21-04 Correction-session frontend readback integration"
status: done
owners: "agents"
created: 2026-05-19
updated: 2026-05-19
stories:
  - "ST-21-04"
tags:
  - frontend
  - vue
  - conversion-hub
  - exam-converter
  - teacher-corrections
dependencies:
  - "ADR-0087"
  - "PR-0335"
acceptance_criteria:
  - "Given a teacher commits a supported correction, when the frontend submits it, then it writes through Skriptoteket correction-session APIs rather than treating component-local state as persisted truth."
  - "Given the teacher navigates between items or reloads the route, when the item view renders, then selection, text, point, review-decision, and candidate-suppression state come from backend readback plus replayed effective state."
  - "Given a local draft has not been submitted, when file actions are evaluated, then the draft does not unlock downloads or claim artifact readiness."
  - "Given replay freshness is unavailable or stale-source validation fails, when the UI renders, then saved-intent state and projection/artifact freshness are visually distinct."
  - "Given matching correction is unavailable, when the UI renders matching affordances, then `manual_matching_answer_key` remains blocked until the later Task 332 slice."
---

# PR-0336: ST-21-04 Correction-Session Frontend Readback Integration

## Problem

The current `PR-0332` frontend can project transaction-returned state, but it
must not claim durable teacher-correction truth. After backend persistence and
replay exist, the UI needs to route commits through Skriptoteket, read back the
saved current set, and render replayed effective state without drifting into
browser-local truth.

## Scope

- Wire correction editors to the correction-session APIs and expected-version
  conflict behavior.
- Read back saved active intents when navigating, reloading, or returning to an
  item.
- Render replayed effective state for visible text, points, answer keys,
  review decisions, candidate suppression, counters, and readiness.
- Keep draft state visually and behaviorally separate from saved/replayed
  truth.
- Add focused Vitest coverage for construction, projection, stale/conflict
  states, and matching blockage.

## Non-Goals

- No backend persistence or replay changes beyond consuming the approved API.
- No matching answer-key enablement.
- No final browser/artifact proof; `PR-0337` owns retained live proof.

## Test Plan

- Focused Vitest for correction commit/readback, projection, conflict handling,
  stale/unavailable replay states, draft gating, and matching blockage.
- `fe-type-check`, `fe-lint`, and `fe-build`.

## Closeout

Implemented in PR-0336. The authenticated Exam Converter UI now:

- registers/recovers the local Conversion Hub job handle, reads persisted active
  intents from Skriptoteket after navigation/reload, and submits supported
  teacher changes through correction-session APIs with expected session version;
- persists points, text patches, manual answer keys, review decisions, accepted
  AI-facit choices/gap keys, and candidate suppression as source-bound intents;
- renders points, text, keys, review decisions, candidate suppression, counters,
  and file readiness from Skriptoteket readback plus Sir Convert replayed
  effective state;
- keeps local drafts visually separate and keeps matching blocked until the
  later governed Task 332 slice;
- uses teacher-facing Swedish copy that avoids internal terms such as
  projection/replay/session/Sir Convert and states only the user consequence.

Validation:

- `pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedReviewSlice.spec.ts src/views/apps/ExamConverterAuthenticatedAiPrefillDurableSlice.spec.ts src/views/apps/ExamConverterAuthenticatedCorrectionSlice.spec.ts src/views/apps/ExamConverterCorrectionSessionReplay.spec.ts`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run fe-build`
