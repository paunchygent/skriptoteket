---
type: task
id: TASK-SKRIPT-40-04-26
title: The question-type switch shows as a compact button in the question head
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-28'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - 'At rest the question-type switch in the question head shows the built xw-btn xw-btn--compact frame, fill and text; hover, open, unbuilt (red) and converting (disabled) keep their meaning, and the row height stays 28 px'
  - 'The question-text toolbar ends with one AI group after a separator: Föreslå facit for this question, undo the AI key (new Eraser glyph) and Gör om till [typ] when the labeler suggests another type; the question head and the key line no longer hold these buttons'
  - 'After the teacher undoes an AI key, the suggest control reads Föreslå igen once; the used retry is saved with the question, survives reload and reopening, and the server refuses a second retry for that question'
  - 'A re-suggested key reads Facit föreslaget av AI on the key line, and undo removes any AI key, interpreted or suggested'
  - 'Desktop without a side panel shows the suggested type name; an open side panel and mouse tablets show glyphs only; an overflowing toolbar keeps the AI group pinned at its right edge; phones and touch devices show the three AI controls with words at the top of the Fler åtgärder menu; nothing changes while the teacher drags a column, and the toolbar reserves its scrollbar space'
story: ST-SKRIPT-40-04
backlog_document_profile: contract-derived
---

## Implementation Contract

The type switch in the question head becomes a compact button so teachers find it. The three per-question AI
controls move into the question-text toolbar as one group, so every AI action on a question sits in one place.

- Actors: a signed-in teacher editing one question in the exam workspace; guests see no AI controls, as today.
- Input: the open question, its answer-key origin, its labeler `suggested_kind`, and its saved retry state.
- Output: the head row with the compact type switch; the toolbar AI group in the state the question and band call
  for; a single-question answer-key suggestion through the existing `item_id` request; a saved retry flag.
- Behaviour per state, from mock v3: at rest with an AI key (Föreslå facit disabled, undo enabled); after an undo
  (Föreslå igen enabled once); retry used (disabled, title says the retry is used); busy (built spinner, Gör om till
  disabled while the suggestion runs); the daily AI limit reached (the suggest control disabled with the built limit
  note; undo and Gör om till stay enabled because they make no AI call).
- Width behaviour follows the v3 responsive plan: composition is keyed only to the viewport bands (< 768, 768-1279,
  > = 1280), `data-side` and `(pointer)`; the AI group pins with `position: sticky` while the bar overflows.
- Non-goals: the question list stays plain; the header Facit suggest-all, the import-box type select, Exportera,
  the phone strip and the instruction disclosure stay as built; no change to the AI models or the daily limit.

## Contract Inputs

- Story ST-SKRIPT-40-04.
- User decisions of 2026-10-28 and mocks v1-v3 with `responsive-plan.md` and `similar-triggers.md`, in Hemma
  retained root `01a183c8-9e2b-738a-a25d-f21e6c8f04f0` (`evidence/mock/`); retained plan
  `evidence/planning/TASK-SKRIPT-40-04-26/plan.md`, ledger D1-D9 closed.
- Existing single-question suggestion: `requestSuggestionForItem` and POST `.../answer-key-suggestions` with
  `item_id` (`exam_workspace_enrichment.py`); undo: `examWorkspaceItemEdits.ts` `withoutInterpretedKey`.
- `huleedu-ui-design` (dense workspaces, interaction design, glyph catalogue).

## Core Vertical And Performance

The core vertical is one question: the teacher undoes its AI key, asks once more from the toolbar, gets a new
AI key through the existing single-question job, and the saved retry flag makes the control spent after a reload.
The retry flag is one field on the saved question, checked by the existing suggestion handler; the item format
changes without a compatibility path. No new request per keystroke and no new polling.

Units, each for one junior:

1. Backend: the saved retry flag on the question, set when a single-question suggestion follows an undo, and the
   handler's refusal of a second retry; undo of `machine_proposed` keys in the shared item-edit rules where they
   live on the backend side, if any.
2. Frontend head: `.qhead__type` onto `xw-btn xw-btn--compact`; `Gör om till` leaves `.qhead__tools`.
3. Frontend toolbar: the AI group in the question-text toolbar with its states, the Eraser glyph meaning, the
   key-line text for suggested keys, and undo for any AI key.
4. Frontend bands: the per-band composition, the sticky pin, the touch and phone rows in Fler åtgärder, and the
   reserved scrollbar space.
5. Copy: one ui-copy review of the new titles and labels; the lead applies the accepted wording.

## Validation

- Vitest: the head button's classes and states; the AI group in each state (at rest, after undo, retry used, busy,
  daily limit); undo of an `ai_interpreted` and of a `machine_proposed` key; the band and pointer composition.
- Backend: a unit test that the retry flag is saved and a second single-question retry is refused.
- One staging walk of the exam workspace on the Mac at desktop with and without the PDF preview and at phone width.

## Stop Conditions

- The single-question suggestion cannot run through the existing `item_id` request without a new endpoint.
- The Eraser glyph cannot be added to the shared glyph catalogue from this repository.
- A band rule would change the toolbar during a column drag.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | The question-type switch uses `xw-btn xw-btn--compact`; its states keep their meaning and the row stays 28 px.                                                                                                                                                                                                       |
| D2  | The question-text toolbar ends with one AI group after a separator: Föreslå facit, undo the AI key, Gör om till [typ]; the key line stays as information.                                                                                                                                                            |
| D3  | Föreslå facit asks for this one question's key through the existing `item_id` request and is enabled only when the question has no key; the header suggest-all stays.                                                                                                                                                |
| D4  | One retry per question: after an undo the control reads Föreslå igen once; the used retry is saved with the question and the server refuses a second one.                                                                                                                                                            |
| D5  | A re-suggested key reads Facit föreslaget av AI in AI teal, and undo removes any AI key; the retry stays spent.                                                                                                                                                                                                      |
| D6  | Föreslå facit and undo are glyph-only frameless tools with title and aria-label; undo uses a new Eraser glyph meaning.                                                                                                                                                                                               |
| D7  | Desktop without a side panel shows the type name; open side panel and mouse tablets show glyphs; an overflowing bar pins the AI group; phones and touch devices show the AI controls with words at the top of Fler åtgärder; keyed only to bands, `data-side` and pointer; the toolbar reserves its scrollbar space. |
| D8  | Glyph only while a drawer is open; no AI indicator on a closed menu; the narrowest-column case and the small gap-question scroll are accepted; new copy gets one ui-copy review.                                                                                                                                     |
| D9  | Proof is focused Vitest and backend tests and one Mac staging walk at desktop with and without the preview and at phone width; one independent review at most, no rereviews.                                                                                                                                         |
