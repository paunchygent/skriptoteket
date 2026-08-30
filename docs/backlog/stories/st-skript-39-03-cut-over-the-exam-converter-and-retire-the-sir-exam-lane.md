---
type: story
id: ST-SKRIPT-39-03
title: Cut over the Exam Converter and retire the Sir exam lane
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-08-30'
status: active
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-39
acceptance_criteria:
- Authenticated and public product workflows preserve their accepted behavior while
  running without Sir Convert exam-conversion calls, after which exam-specific Sir
  integration and the Qwen answer-key sidecar are removed without affecting generic
  heavy-document extraction or STT
links:
  decisions: []
backlog_document_profile: contract-derived
---

## Slice Contract

Switch both existing Exam Converter product lanes from Sir-backed execution to
Skriptoteket-owned execution without changing their accepted user behavior.

- The authenticated lane uses the completed local conversion, worker
  enrichment, provider lease, job, and artifact seams and ports the remaining
  Sir-owned source-state, review/correction replay, and result-projection
  surfaces required by the existing product workflow.
- The public lane keeps its current anonymous UI and API contract while its
  Sir-backed producer implementation is replaced with local execution. It gains
  no Luna, GLM, answer-key-completion, or other remote-provider behavior.
- After both production consumers move, exam-specific Sir clients, schemas,
  grants, leases, identifiers, settings, secrets, and fallback selection
  retire. Generic Sir heavy-document extraction and STT remain.
- The Hemma Qwen answer-key sidecar retires after its last exam consumer moves;
  the verified Luna-primary and GLM-failover line remains.

Out of scope: new source formats, changes to the public product contract,
narrowing current authenticated behavior, and retirement of generic Sir
document-extraction or STT capabilities.

## Contract Inputs

- `EPIC-SKRIPT-39` terms E2, E5, and E7; accepted `ADR-SKRIPT-0090`.
- The implemented and live-proven local conversion vertical from
  `ST-SKRIPT-39-01` and remote answer-key line from `ST-SKRIPT-39-02`.
- Existing authenticated SPA/Gateway behavior and the existing Skriptoteket
  public API/UI behavior are the product contracts preserved through cutover.
- Retained plan:
  `.orchestration/context/sessions/01a04d62-c71c-721c-a43a-76384e182429/evidence/planning/ST-SKRIPT-39-03/plan.md`.

## Tasks

1. `TASK-SKRIPT-39-03-01`: cut over the authenticated Exam Converter.
2. `TASK-SKRIPT-39-03-02`: cut over the public Exam Converter.
3. `TASK-SKRIPT-39-03-03`: retire the Sir Convert exam-specific integration
   after both product cutovers.
4. `TASK-SKRIPT-39-03-04`: retire the Hemma Qwen answer-key sidecar after its
   last consumer moves.

## Verification

- Each product cutover is exercised through its real product surface with real
  input appropriate to the behavior and preserves the accepted inputs,
  lifecycle, review/follow-up behavior, and outputs of that lane.
- Retirement begins only after the affected production consumer no longer
  reaches Sir. Both product workflows continue after exam-specific Sir code and
  configuration are absent.
- The authenticated answer-key workflow continues through Luna/GLM after the
  Qwen answer-key sidecar is absent.
- Frontend and route changes receive the repository-required live functional
  check; affected backend/frontend checks and docs gates pass.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| S1 | Both cutovers preserve their current product contracts; they reuse the completed conversion engine and implement any missing product-facing producer surfaces required for cutover without narrowing behavior. |
| S2 | The public lane receives no new remote-provider or answer-key-completion behavior. |
| S3 | Exam-specific Sir surfaces retire only after both production consumers move; generic heavy-document extraction and STT remain. |
| S4 | Qwen retires only after its last exam consumer moves; Luna-primary and GLM-failover remain. |
| S5 | Validation does not impose a particular fixture identity, item count, provider-call count, lease-row count, or evidence-package shape. |
