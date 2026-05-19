---
type: pr
id: PR-0335
title: "ST-21-04 Correction-session replay orchestration"
status: done
owners: "agents"
created: 2026-05-19
updated: 2026-05-19
stories:
  - "ST-21-04"
tags:
  - backend
  - huleedu
  - sir-convert
  - conversion-hub
  - exam-converter
  - replay
dependencies:
  - "ADR-0087"
  - "PR-0334"
acceptance_criteria:
  - "Given persisted active intents exist for a job, when replay is requested, then Skriptoteket issues fresh producer source state through the HuleEdu Gateway before applying corrections."
  - "Given persisted intent binding does not match the producer-issued source state, when replay runs, then Skriptoteket fails with stale-source behavior and never drops or rewrites the intent silently."
  - "Given replay proceeds, when Skriptoteket builds the Sir Convert request, then it submits the complete supported persisted active set in deterministic order through the unified corrections apply route."
  - "Given Sir Convert returns effective state, target readiness, and artifact availability, when Skriptoteket responds, then it returns only that replayed evidence as projection truth."
  - "Given Sir Convert or the Gateway is unavailable, when replay is requested, then Skriptoteket preserves saved-intent truth while marking projection/artifact freshness unavailable."
---

# PR-0335: ST-21-04 Correction-Session Replay Orchestration

## Problem

Persisted correction truth is not enough for teacher-facing projection or
export. `ADR-0087` requires Skriptoteket to replay the complete supported
persisted set through stateless Sir Convert apply and to display only the
returned effective state as projection truth.

## Scope

- Add replay orchestration over the correction-session aggregate.
- Issue producer source state through the HuleEdu Gateway unified source-state
  route.
- Validate persisted source binding and per-item fingerprints against fresh
  producer state.
- Submit the deterministic complete active set through the unified correction
  apply route.
- Return replayed effective state, target readiness, artifact availability, and
  unavailable/stale-source failure semantics.

## Non-Goals

- No frontend UI wiring.
- No durable state in Sir Convert.
- No matching answer-key support before Task 332 and a later approved slice.
- No browser proof.

## Test Plan

- Focused replay tests for complete-set submission, deterministic ordering,
  stale-source rejection, unsupported-kind rejection, unavailable Gateway/Sir
  Convert behavior, and returned effective-state projection.
- Gateway client tests proving the unified source-state/apply routes are used.
- Backend lint/typecheck and focused orchestration tests.

## Implementation Summary

- Added a non-UI correction-session replay service that loads Skriptoteket
  persisted active intents, issues fresh source state through the authenticated
  HuleEdu Sir Convert Gateway client, validates persisted source binding and
  item fingerprints, and submits the complete deterministic active set to the
  unified apply route.
- Added a typed correction-session API client over the PR-0334 generated
  Skriptoteket OpenAPI contract for read/upsert/revert consumption.
- Preserved saved-intent truth when source-state or apply replay is
  unavailable, while returning fresh projection fields only from Sir Convert's
  replayed effective-state/readiness/artifact evidence.
- Kept UI wiring, Sir Convert persistence, browser proof, and matching
  enablement out of scope.

## Verification

- `pdm run fe-test -- --run src/views/apps/ExamConverterCorrectionSessionReplay.spec.ts src/api/sirConvertGateway/client.spec.ts src/api/sirConvertGateway/correctionsContract.spec.ts`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run fe-build`
