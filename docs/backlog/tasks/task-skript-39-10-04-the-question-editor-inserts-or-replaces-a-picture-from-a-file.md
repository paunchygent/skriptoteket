---
type: task
id: TASK-SKRIPT-39-10-04
title: The question editor inserts or replaces a picture from a file
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-21'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - The question text and instruction editors have one picture control, Lägg till bild; choosing a picture file inserts it at the cursor, or replaces the selected picture, in every exam
  - Dropping or pasting a picture file onto the text inserts it the same way
  - A signed-in exam saves a new picture's bytes once, with the autosave that first references it, checked and stored together with the document
  - The control's look follows huleedu-ui-design and was approved by the user as a mock before the build
story: ST-SKRIPT-39-10
backlog_document_profile: contract-derived
---

## Implementation Contract

The question text and instruction editors gain one picture control, "Lägg till bild" (T3).

- With nothing selected, choosing a picture file inserts the picture at the cursor.
- With a picture selected, the chosen file replaces it.
- Dropping or pasting a picture file onto the text inserts it the same way (T4).
- It works in every exam, whatever its source, not only PDF imports.
- A signed-in exam's autosave carries a new picture's bytes once, checked and saved together with the document; no separate upload route (T5).

The task runs in two steps:

1. The lead designs the control under huleedu-ui-design and makes a mock. The mock covers placement in the editor toolbar, the glyph, the label and the replace state. The Mac orchestrator takes the mock to the user. Nothing is built before the user approves it.
2. After approval, the lead builds the control.

This task does not depend on TASK-SKRIPT-39-10-01 to 03.

Non-goals: picture resizing, cropping or re-cutting a figure from the original page.

## Contract Inputs

- ST-SKRIPT-39-10 P8 and P9. The Mac plan is in Mac retained root `01a1602d-173d-72ed-b3ac-83c6a24e9070`, `evidence/planning/ST-SKRIPT-39-10/plan.md`.
- The picture node in `examWorkspaceRichTextSchema.ts`, the question editor toolbar, and the existing picture storage and asset limits of the exam document.

## Core Vertical And Performance

A teacher places the cursor in a question, clicks "Lägg till bild", chooses a PNG or JPEG file, and the picture appears at the cursor and is saved with the exam. A teacher who selects a picture and does the same replaces it. The picture follows the exam's existing asset rules and limits.

## Validation

- The mock, approved by the user through the Mac orchestrator, recorded in Progress.
- Focused Vitest for insert at the cursor, replace of the selected picture, a refused file type or size, and saving with the exam, in a signed-in exam and in a guest exam. Backend tests if the build touches the backend.
- fe-type-check and fe-lint, plus backend lint and typecheck if touched.
- A staging walk by the Mac.

## Stop Conditions

- Stop after the mock and wait for the user's approval.
- Stop and report if pictures cannot be added through the existing picture node and asset rules without changing the exam document format.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                 |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T1  | ST-SKRIPT-39-10 P8 applies as written.                                                                                                                                                                                |
| T2  | Mock first. The user approves it through the Mac orchestrator before any build.                                                                                                                                       |
| T3  | The control is in the instruction editors as well as the question text editors (user decision 2026-10-22, relayed by the Hemma orchestrator).                                                                         |
| T4  | Dropping or pasting a picture file onto the text also inserts it, in this task (user decision 2026-10-22, relayed by the Hemma orchestrator).                                                                         |
| T5  | A signed-in exam's autosave carries a new picture's bytes once, checked and saved together with the document; the separate upload route stays rejected (user decision 2026-10-22, relayed by the Hemma orchestrator). |

## Progress

### 2026-10-21 (Hemma orchestrator)

- Scaffolded from the ST-SKRIPT-39-10 story terms. The story is `ready` by the user's grilling of 2026-10-21, relayed by the Mac orchestrator. This task is `ready` for its mock step, and a lead session is assigned.

### 2026-10-22 (lead)

- The user reviewed mock v1 and did not approve it: the picture sat at the end of the text line, and the mock showed no real output. Decisions T3-T5 recorded. Mock v2, with real editor screenshots and real renders of every export, is in retained root `01a1605d-5786-7434-9227-58fee29c2cc5`, `evidence/mock/picture-control-mock-v2.html`; it proposes that a picture always gets its own paragraph and waits for the user's approval.
- T2 met: the user approved mock v2 ("Approve, build it", 2026-10-22, relayed by the Hemma orchestrator). The build follows mock v2: each added picture gets its own paragraph. Accepted residuals: typing into a picture's paragraph puts the picture back into a text line, and imported inline pictures stay inline.
- Built on branch `codex/task-skript-39-10-04` (39a061e8b, c87ae4f49, 1176ef41e, 5e60a639f, 7911012f1): "Lägg till bild" / "Byt bild" in the question text (also Kort svar) and both instruction editors; drop and paste; each picture in its own paragraph (end, start, split at the caret, empty paragraph, replace in place); busy state and the refused-file inline notice; the signed-in autosave carries a new picture's bytes once (`new_assets_by_id`, verified by the server); guest pictures are stored with the draft. The 20 MB limit is one frontend constant, `EXAM_FILE_MAX_BYTES`, mirroring the backend's `VAULT_MAX_FILE_BYTES`, because the server sends no exam setting that carries it. Focused proof: backend handler pytest 1895 passed, 58 skipped; Vitest 178 files, 1100 tests passed; fe-type-check, fe-lint, lint, typecheck and docs-validate clean. Evidence: retained root `01a1605d-5786-7434-9227-58fee29c2cc5`, `evidence/build/proof/`. Waiting for independent review.
- User decision (2026-10-22, relayed by the Hemma orchestrator): when the picture size limit cannot be fetched from the server, the editor shows the inline notice "Bilden lades inte till. Försök igen." The user's words: "Yes, use "Bilden lades inte till. Försök igen." when the picture limit can't be fetched." This comes with the review F4 repair, which reads the limit from the backend setting `VAULT_MAX_FILE_BYTES` for both modes.
- Review repair (findings F1 and F3-F8; F2 was resolved at the host, no code change), commits ef4d2d9aa..2c2d31141:
  - F1: a picture counts as sent only while the working copy declares it, and a guest commit refuses a document that declares a picture whose bytes the draft does not hold.
  - F3: each picture intake is bound to the opening and live target it started in.
  - F4: the limit is read from `VAULT_MAX_FILE_BYTES` over a signed-in route and a public guest route, so the frontend holds no copy of the value.
  - F5: a replacement is sized by its resulting document.
  - F6: an unreadable file gets the type refusal.
  - F7: the editor's picture handling and the picture specs are split by responsibility.
  - F8: specs use coherent PNG/JPEG fixtures on complete documents.
  - Accepted residual: an add in a new exam while the previous exam's read is still pending is ignored, and the teacher adds the picture again.
  - Proof:
    - Vitest exam-workspace 315 files, 2358 tests passed; views+api 522 files, 3703 tests passed before the final spec split.
    - Backend limits and exam-workspace route pytest: 93 passed.
    - fe-type-check, fe-lint, lint and typecheck clean.
    - Evidence: retained root `01a1605d-5786-7434-9227-58fee29c2cc5`, `evidence/build/proof/`.
  - F1 waits for independent rereview.
