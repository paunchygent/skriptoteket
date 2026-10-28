---
type: task
id: TASK-SKRIPT-39-06-09
title: Exam.net probe of an ordering question inside a part
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: "2026-10-18"
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: orchestrator
  decided_at: '2026-10-28'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'Probe package built from the 39-06-08 QTI writer with no writer change (branch codex/task-skript-39-06-09, 6fee3cfdd; Hemma .artifacts/probe-39-06-09/PROBE.md, SHA-256 c367f3c7). Imported by the Mac thread in the user''s Edge 2026-10-28 as Exam.net exam 5395644 (Mac ~/Repos/Skriptoteket/.artifacts/probe-39-06-09/walk-record.md, screenshots in evidence/). Import passes; one task with the shared instruction once, a) ordering and b) Lucktext, no blank question. The ordering child imports as Matcha ihop with position numbers and the correct pairs, and the student draws pairing lines (no reorder control; numbers reshuffle per load). Grading is all-or-nothing (2 of 4 pairs right gives 0) and the children score independently. Points: the ordering child''s 3 points import as the rule Alla rätt 1p, so the exam totals 2p, not 4.'
task_kind: story
acceptance_criteria:
  - An exported exam with an ordering question inside a part is imported into Exam.net, and its student view and all-or-nothing grading are recorded
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

## Progress

### User decision 2026-10-28 after the probe

- Ordering is built inside parts. Inside a part an ordering child is always worth 1 point, and the editor shows that, so the export matches what Exam.net imports. Standalone ordering keeps its editable points (story P21). This supersedes the standalone-only rule in story P3 for parts; the build task is planned from it.
