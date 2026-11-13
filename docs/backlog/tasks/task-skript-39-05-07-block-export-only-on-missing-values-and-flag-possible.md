---
type: task
id: TASK-SKRIPT-39-05-07
title: Block export only on missing values and flag possible parsing issues only where
  wording is lost
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-13'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-reviewer
  decided_at: '2026-10-13'
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: User closed 39-05-07 on 2026-10-13 and kept both export copy strings as implemented. Independent review approved 58dabe3f (retained evidence/reviews/TASK-SKRIPT-39-05-07/rereview-58dabe3f.md); D9 eval evidence/task-skript-39-05-07-d9-eval/README.md; staging walk on main ebc2a9c7 evidence/staging-walk-ebc2a9c7/README.md, all in session 01a13274-4a76-75e2-a17f-2e05fa66bd3a.
task_kind: story
acceptance_criteria:
- An imported exam blocks export only on missing points, a missing answer key, an
  unapproved AI key, the save rules or an unbuilt question, and printed (N p) markers
  become points
story: ST-SKRIPT-39-05
backlog_document_profile: contract-derived
---

## Implementation Contract

A DOCX import marks too many questions "Behöver granskas", and every such mark
blocks export. Points printed as "(1 p)" are not read in, and the left-out
check reports text the question already holds. This task changes the
conversion and the export gate so that only missing values and unbuilt
questions block export, and parsing doubts become rare signals that do not
block export.

- Export gate (`native_export_blockers`, `native_exam_document.py`, and its
  frontend mirror `examWorkspaceItemReadiness.ts`): blockers are missing
  points, a missing answer key, an unapproved AI key, the save rules, and an
  unbuilt question. An unbuilt question is an item printed from source
  (`review_source_item`) that the teacher has not marked reviewed.
  `review_required` alone no longer blocks export.
- Points: when the reply gives an item no points and the question's own
  paragraphs print exactly one `POINT_LABEL`, the item takes those points and
  the marker is removed from its stem and title.
- Left-out check (`_with_left_out`, `return_misplaced_own_chunks`): a
  paragraph counts as left out only when its wording, without points markers,
  numbering and answer or facit lines, is missing from the item.
- Possible parsing issues: only the model's review outcome, a type conflict
  without a kind, gapped material and the wording-based left-out check set
  `review_required`. They do not block export.
- Points split from a section total are marked on the item as estimated, not
  as a review reason.
- `review.confidence` is below the acceptance threshold only for a kept type
  conflict, so "Kontrollera frågetypen" shows only there.
- Import notes hold document-level notes only (facit paragraphs, paragraphs
  that are not questions); item reasons are not copied into them.

Out of scope: how the editor shows blockers, parsing issues, the unbuilt
blocker and the estimated-points hint. TASK-SKRIPT-39-04-05 owns that
presentation.

## Contract Inputs

- Retained plan for TASK-SKRIPT-39-04-05, session
  `01a13061-ff38-7099-aa3d-e23f6e5bba43`, rows D47-D58 (user decisions
  2026-10-13), and discovery evidence
  `evidence/import-signal-discovery-2026-10-13/signals.md` in that session.
- User product rule 2026-10-13: an export blocker is shown at the field where
  it is fixed; possible parsing issues are a separate, much rarer signal.

## Core Vertical And Performance

DOCX chunks, reply admission, build state, assembled native document, export
gate and its frontend mirror, from one DOCX import through a saved document to
export. The points and wording checks are linear in the question's paragraphs.
No new model call.

## Validation

- Baseline before the change and the same run after it: `pdm run
  exam-conversion-eval` over the 8 gold exams plus the 3 synthetic exams that
  print "(N p)". Record, per exam, how many items are `review_required`, by
  reason, and how many have no points. Needs the answer-key API key.
- Adversarial unit tests: a choice question whose stem ends in "(1 p)" and a
  reply with no points gets 1 point and a stem without the marker; a reply that
  leaves out the stem's anchor but copies its wording is not flagged; a reply
  that drops a stem sentence is flagged; an unbuilt item with a section-split
  points share still blocks export until it is marked reviewed; a
  `review_required` item with points and a key does not block export.
- Ruff, mypy and focused pytest on changed backend files; Vitest and typecheck
  for the readiness mirror.
- Staging walk: import one synthetic "(1 p)" exam and one gold exam, then
  export QTI without marking parsing issues reviewed. Walked 2026-10-13 on main
  ebc2a9c7: retained-root `evidence/staging-walk-ebc2a9c7/README.md`.

## Stop Conditions

- The after-change eval loses gold matches that the baseline had.
- The wording check misses an omission that the anchor check caught in the
  eval.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D1  | Export is blocked only by missing points, a missing answer key, an unapproved AI key, the save rules, and an unbuilt question; `review_required` alone does not block export (plan D47). |
| D2  | An unbuilt question (an item printed from source) blocks export until the teacher marks it reviewed (plan D47, D57). |
| D3  | When the reply gives no points and the question's own text prints exactly one points marker, the import uses it as the points and removes the marker from the stem and title (plan D48). |
| D4  | The left-out check flags a paragraph only when its wording, without points markers, numbering and answer or facit lines, is missing from the item (plan D49). |
| D5  | Only the model's review outcome, a type conflict without a kind, gapped material and the wording-based left-out check are possible parsing issues; they set `review_required` and do not block export (plan D50, D56). |
| D6  | Points split from a section total are marked on the item as estimated, not as a review reason (plan D58). |
| D7  | Type confidence is below the threshold only on a kept type conflict (plan D51). |
| D8  | Import notes hold document-level notes only; item reasons are not copied into them (plan D52). |
| D9  | The current-version eval over the gold and synthetic "(N p)" exams is this task's baseline and after-change check (plan D55). |
