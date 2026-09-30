---
type: task
id: TASK-SKRIPT-39-03-03
title: Retire the Sir Convert exam-specific integration
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-08-30'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-reviewer
  decided_at: '2026-09-30T19:50:24+02:00'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'Independent ruthless-reviewer (Pi invocation 81328779) approved retirement 4225e62f/0bae2fe1 and cleanup 9c26b1bc/9dc63d4d with no findings. Linked Sir TASK-SIRCON-07-04-01 and HuleEdu TASK-HULE-01-04-13 closed approved. Authenticated path proven by staging click-through; public path proven by review and tests only, closed on that evidence by user decision 2026-09-30; generic Sir runtime is offline by user decision, so its health is proven by Sir service/speech/operations checks at ee14c6da. Retained session 01a0f34a-1687-7480-a408-a0daee5f1d73 evidence/reviews/TASK-SKRIPT-39-03-03-independent-review.md.'
task_kind: story
acceptance_criteria:
  - After both product lanes cut over, exam-specific Sir clients, schemas, grants, leases, identifiers, settings, secrets, and fallback selection are removed while generic heavy-document extraction and STT remain operational
story: ST-SKRIPT-39-03
backlog_document_profile: contract-derived
---

## Implementation Contract

After Tasks 01 and 02 have switched their production consumers, remove the
exam-specific Sir integration without affecting generic Sir capabilities.

- Remove authenticated and public Sir exam clients, protocols, mappings,
  mirrored exam schemas, exam-only grants and artifact leases, upstream job
  identifiers, environment settings, secrets, and fallback selection.
- Remove the `sir_convert` Exam Converter lane and its operator switch so
  Skriptoteket-owned execution is the single exam-conversion path.
- Retire corresponding exam-specific producer and grant surfaces through
  repository-owned linked authorities wherever Sir Convert or HuleEdu owns the
  code or deployment state.
- Preserve Sir generic heavy-document extraction, OCR, STT, and every remaining
  non-exam consumer.
- Leave no compatibility adapter, dormant fallback, or deprecated alias.

## Contract Inputs

- Completed and live-confirmed Tasks 01 and 02.
- `ST-SKRIPT-39-03` terms S1-S5 and `ADR-SKRIPT-0090` boundary.
- Current cross-repository exam-specific clients, schemas, grants, leases,
  configuration, secrets, deployment declarations, and consumer inventory.

## Core Vertical And Performance

Authenticated and public Exam Converter workflows continue to operate after
all exam-specific Sir code and runtime configuration are removed. The change
eliminates one cross-service hop from each lane and does not modify generic Sir
workloads.

## Validation

- Both product paths remain functional after retirement.
- Repository and deployed-runtime inspection find no remaining production exam
  conversion dependency on Sir.
- Generic Sir document-extraction and STT consumers and their focused checks
  remain healthy.
- Each affected repository uses its own docs authority and required gates.

## Stop Conditions

- Do not begin before both product consumers have completed cutover.
- Do not remove a surface with a remaining production consumer.
- Stop if a proposed removal crosses into generic extraction, document
  conversion, OCR, or STT behavior.

## Decided Contract Terms

| ID  | Decided contract term                                                                                              |
| --- | ------------------------------------------------------------------------------------------------------------------ |
| T1  | Retirement begins only after authenticated and public production consumers no longer use Sir exam conversion.      |
| T2  | All exam-specific clients, schemas, grants, leases, identifiers, settings, secrets, and fallback selection retire. |
| T3  | Generic heavy-document extraction, OCR, STT, and non-exam consumers remain.                                        |
| T4  | Cross-repository mutations require linked authority in the repository that owns each retiring surface.             |
