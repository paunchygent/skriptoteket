---
type: task
id: TASK-SKRIPT-39-06-09
title: Exam.net probe of an ordering question inside a part
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: "2026-10-18"
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - An exported exam with an ordering question inside a part is imported into Exam.net,
    and its student view and all-or-nothing grading are recorded
story: ST-SKRIPT-39-06
backlog_document_profile: contract-derived
---

## Implementation Contract

TASK-SKRIPT-39-06-08 builds standalone ordering questions (P3), proven in Exam.net only as a standalone item (probe TASK-SKRIPT-39-06-02). Before ordering inside parts is built, this probe exports one exam that holds a part with an ordering child and a Lucktext child (D1). The QTI writer gets only the probe change needed for it. The user imports the exam into Exam.net in Edge, and the probe records the student view and whether grading is all-or-nothing. The build task is planned from that result.

Non-goals: allowing ordering inside parts in the editor; any production behaviour change.

## Contract Inputs

- ST-SKRIPT-39-06 P3 and P21.
- The TASK-SKRIPT-39-06-02 probe method and PROBE.md.
- TASK-SKRIPT-39-06-08 (the ordering kind and `qti-order-interaction`).
- `examnet_qti_export.py:129-207` (a part as one composite item with child interactions).

## Core Vertical And Performance

A disposable probe package is built from the 39-06-08 writers with a part holding an ordering child. It is imported by the user in Exam.net, and the findings are retained in evidence. Performance is not material.

## Validation

- The Exam.net import in the user's Edge.
- Retained screenshots of the teacher preview and student preview.
- Grading checks with all lines correct and with some lines correct.

## Stop Conditions

Stop and report to the parent when Exam.net refuses the package, or when the probe would need a production behaviour change.

## Decided Contract Terms

| ID  | Decided contract term                                                                                       |
| --- | ----------------------------------------------------------------------------------------------------------- |
| D1  | Ordering inside parts is probed in Exam.net before any build; the build is planned from what Exam.net does. |
