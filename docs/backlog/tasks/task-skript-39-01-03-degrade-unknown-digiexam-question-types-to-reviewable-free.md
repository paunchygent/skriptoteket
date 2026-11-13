---
type: task
id: TASK-SKRIPT-39-01-03
title: Degrade unknown DigiExam question types to reviewable free text
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-09-04'
status: canceled
closeout_review:
  record: inline
  status: not_required
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: User agreed to cancel this task as unnecessary after real-export discovery found only the four supported DigiExam types and the user confirmed those are the existing types. Future development should verify real-export correctness and repair demonstrated defects rather than invent unsupported types.
task_kind: story
acceptance_criteria:
- Unknown DigiExam question types remain in the converted exam as reviewable free-text
  items with their prompt and points preserved, an explicit item-bound warning, and
  valid export artifacts instead of blocking the whole conversion
story: ST-SKRIPT-39-01
backlog_document_profile: contract-derived
---

## Implementation Contract

Fulfil `EPIC-SKRIPT-39` term E3 for DigiExam ingestion. A question whose
numeric source type is unknown remains in the neutral exam and both export
targets as a free-text, manually evaluated item instead of blocking the exam.
Preserve its prompt, title or deterministic title fallback, valid point value,
and usable embedded images. Retain the original type code for audit.

Emit one item-bound, non-blocking warning from a reusable Swedish message
template. The message explains that the source question type was not
recognized, that the item was converted to free text, and that the teacher
must review or recreate its response interaction before use. Show it in the
authenticated question view and summarize affected questions in the existing
report.

Do not infer unknown response semantics. Alternatives, gaps, or other
source-only structures may remain in the neutral artifact for audit but do not
become guessed target interactions. Do not add an LLM repair or answer-key
request for the degraded item.

## Contract Inputs

- `EPIC-SKRIPT-39` term E3 and the active `ST-SKRIPT-39-01` conversion slice.
- Existing `DigiExamItemType.UNKNOWN`, type-code retention, neutral IR,
  manual free-text evaluation, Exam.net QTI free-text interaction, and
  Exam.net-profile PDF open-response strategy.
- `TASK-SKRIPT-39-01-02` supplies fractional-point, missing-title, and
  missing-image behavior consumed by this slice; this task does not redefine
  those policies.
- Retained plan:
  `.orchestration/context/sessions/01a06bde-e127-7042-912b-d492fb6c00de/evidence/planning/TASK-SKRIPT-39-01-03/plan.md`.

## Core Vertical And Performance

1. The parser retains the unknown source type code and emits an item-bound
   non-blocking warning, leaving the exam renderer-ready.
2. Neutral/effective IR, fingerprints, manifests, correction replay, and stored
   artifacts preserve the unknown provenance and warning.
3. PDF adapts the item to the existing open-response strategy; QTI adapts it to
   the existing free-text/manual-evaluation interaction. Both preserve prompt,
   title, points, and usable images.
4. Readiness and artifact generation retain the item and remain successful;
   the authenticated question and report views expose the review action.

The degradation is deterministic and linear in existing item traversal. It
makes no provider call and adds no material performance concern.

## Validation

- Establish the unsupported-type case in an unchanged real DigiExam export
  before implementing its handling. Record the source hash, observed numeric
  type code, relevant source structure, and current conversion failure in
  retained evidence without exposing teacher content.
- Derive the minimal regression fixture from that observed real question,
  preserving its actual type code and response structure. Sanitize private
  content and record every reduction or substitution; do not commit teacher
  files. An invented type code or altered known-type question is only a
  defensive test and cannot establish the real-world issue.
- If no real unsupported-type example is available, stop and request one from
  the user rather than inventing an implementation-driving fixture.
- Focused parser, IR, overlay/replay, fingerprint, and artifact tests prove the
  type code and warning survive while parse and target readiness remain usable.
- Focused PDF and QTI tests prove the item is present as open/free text, is
  manually evaluated, preserves prompt/title/points/usable images, and produces
  valid export artifacts without guessed choice or gap interactions.
- Focused frontend tests assert the reusable Swedish item message and report
  summary through visible text rather than snapshots.
- Run affected backend tests, `pdm run lint`, and `pdm run typecheck`.
- Run affected frontend tests, `pdm run fe-type-check`, `pdm run fe-lint`, and
  `pdm run fe-build`.
- Exercise the authenticated HuleEdu browser-session path with the sanitized
  real-export-derived fixture and validate the generated QTI before any user-coordinated Exam.net
  import check.
- Close with `pdm run handoff-validate`, `pdm run docs-validate`, and
  `git diff --check`.

## Evidence Gate — 2026-09-05

Read-only discovery found no unsupported numeric question type in the two
user-supplied exports or the four repository `.dxe` fixtures. The supplied
Privatekonomi export contains 10 questions with types 0–3; Näringslära contains
14 questions with types 0 and 2. Both parse successfully and are renderer-ready.
The existing type-99 unit test is artificial defensive coverage, not evidence
of a real unsupported question.

The user confirmed that types 0–3 are the existing DigiExam types and approved
cancellation of this speculative task. No implementation or derived fixture
was created. The next development goal is real-export correctness across those
four types, including PDF output and user-coordinated Exam.net QTI import
checks; new implementation requires demonstrated defects. Discovery report:
Pi scout run `e7824daa-450a-43ff-b8a2-96405024dd49`, retained context
`01a06bde-e127-7042-912b-d492fb6c00de`.

## Stop Conditions

- Stop if an unknown source type still blocks or removes the whole exam or the
  affected item.
- Stop if conversion guesses choice, gap, matching, scoring, or answer-key
  semantics absent from the recognized contract.
- Stop if prompt, title, valid points, or usable images are lost, or if either
  export becomes invalid.
- Stop if the item enters answer-key enrichment or causes another provider
  call.
- Stop for user direction if the source requires more than one neutral
  free-text response to preserve visible content.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| T1 | An unknown DigiExam question type becomes one free-text, manually evaluated item and does not block the exam. |
| T2 | Preserve the source prompt, title or deterministic fallback, valid point value, usable images, and original source type code. |
| T3 | Emit item-bound non-blocking Swedish information explaining the degradation and requiring teacher review or recreation before use. |
| T4 | Unknown response structures are not interpreted as choice, gap, matching, scoring, or answer-key semantics. |
| T5 | The degraded item remains present in valid PDF and QTI artifacts and in authenticated question/report review surfaces. |
| T6 | The path is deterministic and provider-free; it never enters answer-key enrichment or adds an LLM call. |
