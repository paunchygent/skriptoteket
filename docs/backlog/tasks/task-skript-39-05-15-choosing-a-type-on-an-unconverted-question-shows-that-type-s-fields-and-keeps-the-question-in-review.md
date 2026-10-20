---
type: task
id: TASK-SKRIPT-39-05-15
title: Choosing a type on an unconverted question shows that type's fields and keeps the question in review
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-20'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - Choosing any type on an unconverted question shows that type's fields and gap tools at once, export stays blocked on that question until the teacher marks it reviewed, and one Ångra restores the kind and the unconverted state
story: ST-SKRIPT-39-05
backlog_document_profile: contract-derived
---

## Implementation Contract

### Resume here

- 2026-10-20: contract closed; design and copy approved by the orchestrator
  (Hemma session 944b5a5a). U1 (domain review flip, export blocker, undo test)
  returned green and is staged. U2 (frontend) running. D9 added after U2 found
  that a retype to Lucktext lands in the Kort svar shape; U3 (domain gap
  placement plus the shared case table) running; U4 (client spec on the same
  table plus the staging editor case) follows U3. Juniors do not commit; the
  lead commits each unit, regenerates `openapi.d.ts`, runs focused proof, then
  the domain-suite gate. Work orders under `evidence/work-orders/`.
- Evidence root: Skriptoteket session `01a156ae-7f31-7338-be23-b8b32352aa02`.

### Problem

On staging 99378586, exam 996a684f, Fråga 3a (item_006), choosing Lucktext on an
unconverted question stored `kind: gap_fill` but kept
`review: {state: review_required, parse_origin: source_fallback}`. The editor
treats `review_required` with `source_fallback` as unconverted and hides every
field, so the gap tools never appear. Two causes:

1. `change_item_type` (`native_exam_change_type.py`) never changes `review`.
2. The domain and `useExamWorkspaceStructure.changeType` both return early when
   the chosen kind equals the stored kind. Fallback items are stored as
   `free_text`, so choosing Fritext did nothing, and choosing Lucktext again on
   the staging item does nothing.
3. A retype from free text to Lucktext appended the gap as its own last
   paragraph, which the editor counts as Kort svar since TASK-SKRIPT-40-04-08,
   so the editor showed the Kort svar field and no gap tools.

### Change

- Domain: retyping a `source_fallback` item sets `parse_origin` to
  `teacher_created` and keeps `state` as it is. Choosing the stored kind on a
  `source_fallback` item changes only the origin. Items with any other origin
  keep their origin, and the same-kind no-op stays for them.
- Export rules: a new blocker reason `unreviewed_retyped_question` applies to
  `review_required` with `teacher_created`. `is_unbuilt_question` is unchanged.
- Frontend: `examWorkspaceItemReadiness` mirrors the new reason; the blocker
  list fixes it with the existing review action and focuses the existing review
  button; `changeType` sends the stored kind when the question is unconverted.
- Undo: the server undo step stores the full document, so one Ångra restores
  the kind and `source_fallback`. No history, document, lease or sync-gate file
  changes.

## Contract Inputs

- User decision 2026-10-19 (Hemma orchestrator): "Show fields, keep review".
- TASK-SKRIPT-39-05-07 D1 (review flags on converted items do not block export)
  and D2 (an unbuilt question blocks export until it is marked reviewed).
- Copy approved provisionally by the orchestrator 2026-10-20; copy review follows.

## Core Vertical And Performance

Byt frågetyp or the "Ej konverterad" dropdown → change-type endpoint →
`change_item_type` → undo step → editor readiness → export blockers. No
performance concern: one item is rebuilt per command.

## Validation

- Domain tests: retype of a `source_fallback` item leaves the unconverted state
  and stays `review_required`; same-kind retype flips only the origin; other
  origins keep their origin; the export blocker lists the retyped item until it
  is marked reviewed, and `llm_parsed`/`deterministic` review flags stay
  non-blocking.
- Handler test: one undo after the retype restores the previous kind and
  `source_fallback`.
- Frontend specs: the fields and gap tools appear after the switch; the new
  reason shows in the export panel and the question list until reviewed; the
  unconverted same-kind choice sends the command.
- `pdm run lint`, `pdm run typecheck`, `pdm run fe-type-check`, `pdm run fe-lint`, focused tests, and one domain suite at the end.
- Component-rendered screenshots (labelled as such) of the export line, the
  list label and the editor after the switch, with a string inventory.

## Stop Conditions

- The fix needs `useExamWorkspaceHistory*`, `useExamWorkspaceDocument*`, the edit
  lease or the sync gate.
- Undo does not restore the full prior document.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | Retyping a `source_fallback` item sets `parse_origin` to the existing `teacher_created` value and keeps `review_required`; no new origin value.                                                                                                                                                                                                                                                                                                                                                                  |
| D2  | Choosing the stored kind on a `source_fallback` item is a real change that flips only the origin; for any other origin it stays a no-op.                                                                                                                                                                                                                                                                                                                                                                         |
| D3  | Export blocks on the new reason `unreviewed_retyped_question`, keyed only on `review_required` with `teacher_created`; broader rules would block the review flags that 39-05-07 D1 keeps non-blocking.                                                                                                                                                                                                                                                                                                           |
| D4  | Only marking the question reviewed ends the block (39-05-07 D2); the fix action is the existing "Markera som granskad".                                                                                                                                                                                                                                                                                                                                                                                          |
| D5  | Undo uses the existing full-document server undo step; no history code changes.                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| D6  | Copy: export line "Frågan har fått en ny typ men är inte granskad. Kontrollera den och markera den som granskad."; list label "inte granskad"; the type-change notice is unchanged. Provisional until copy review.                                                                                                                                                                                                                                                                                               |
| D7  | An item that is unconverted only because of a missing picture keeps its current behaviour; out of scope.                                                                                                                                                                                                                                                                                                                                                                                                         |
| D8  | Skriptoteket is unreleased: no compatibility path for stored documents.                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| D9  | A domain retype to Lucktext places the new gap at the end of the last question paragraph by the client's `withGapTextShape` rule (trailing empty paragraphs drop; a space separates text without trailing whitespace; an empty question gives the gap paragraph then an empty paragraph), so Lucktext opens as Lucktext with the gap tools, not as Kort svar. One shared case table is asserted by both the pytest and the Vitest suites (orchestrator 2026-10-20). Dropdown retype keeps its own gap paragraph. |
