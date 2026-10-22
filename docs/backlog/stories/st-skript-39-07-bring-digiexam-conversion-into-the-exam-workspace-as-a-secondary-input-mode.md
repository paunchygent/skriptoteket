---
type: story
id: ST-SKRIPT-39-07
title: Bring DigiExam conversion into the exam workspace as a secondary input mode
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-12'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: user
  decided_at: '2026-10-22'
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: 'The user closed the story on 2026-10-22: TASK-SKRIPT-39-07-01, TASK-SKRIPT-39-07-02 and TASK-SKRIPT-39-07-03 are done; the Mac staging walk at 4b321fa1 proved the in-app DigiExam import and editing, and TASK-SKRIPT-39-07-03 passed B1 to B5 with the old routes redirecting to the workspace (Mac .artifacts/staging-walk-l1c-4b321fa1/walk-record.md).'
epic: EPIC-SKRIPT-39
acceptance_criteria:
  - A teacher opens a DigiExam export as a secondary input mode of the exam workspace, edits it in the same editor and exports QTI, PDF and DOCX, and the signed-in old converter views are gone
links:
  decisions: []
backlog_document_profile: contract-derived
---

## Slice Contract

The exam workspace is the main exam conversion and editing app (EPIC-SKRIPT-39
E16). Today a DigiExam `.dxe` export goes through a separate converter: the
parser builds a `DigiExamIntermediateExam`, the teacher corrects it in the
correction overlay and correction sessions, a token-leased AI pass completes
missing answer keys, and the result is an Exam.net bundle saved as Conversion
Hub artifacts. This story makes a DigiExam export a secondary input mode of the
workspace instead.

The story delivers:

- A `.dxe` export imports through the workspace API into a saved native exam
  document with a DigiExam origin. The teacher edits it in the same editor as
  a DOCX import and exports it through the existing QTI, PDF and DOCX export
  routes, so DigiExam exams leave in the same QTI 3.0 package shape as every
  other workspace exam (E13).
- Questions imported without an answer key get AI answer-key suggestions
  through the workspace's existing per-question suggestion lane, behind the
  same per-question review as DOCX imports (G21).
- The signed-in old converter retires: its routes, the correction overlay, the
  correction sessions, the old DigiExam answer-key lane and the old converter
  screens are removed (G21, E16). The public guest exam converter
  (ADR-SKRIPT-0085) stays with its routes and modules; a later decision covers
  it (G27). The later decision is made (user 2026-10-20): the old guest DigiExam converter is subsumed by the exam workspace, where DigiExam is one input; TASK-SKRIPT-41-02-03 removes it and the public workspace (TASK-SKRIPT-41-02-02) replaces it as the demo that leads guests to an account (EPIC-SKRIPT-41 E5).

Scope boundaries:

- Backend, data and API only (G2). The DigiExam entry in the `Öppna` drawer
  and every new workspace control are built by ST-SKRIPT-40-04
  (TASK-SKRIPT-40-04-03). The current workspace screens stay frozen except for
  bug fixes, and the old converter views get no layout work (E16).
- The story starts now as a backend lane; it does not wait for the PDF and
  Markdown input routes (G22).
- Unsupported DigiExam types keep E12: no new type handling and no importer
  research.
- The import box shows the original wording and short readable steps for
  DigiExam imports as for DOCX imports (G19). TASK-SKRIPT-39-04-06 builds that
  projection; this story supplies the DigiExam wording and steps to it and does
  not build a second one.
- Out of scope: new question kinds and parent or child editing
  (ST-SKRIPT-39-06), the PDF and Markdown input routes, and any workspace UI.

## Contract Inputs

- Epic terms E12, E13 and E16 in
  `docs/backlog/epics/epic-skript-39-skriptoteket-owned-exam-conversion.md`.
- User decisions G2, G19, G21, G22 and G27 (2026-10-17), retained in session
  `01a1495e-8398-75be-b2da-f0b08ba11afa`, `evidence/planning/decisions-2026-10-17.md`;
  verified repository facts in
  `evidence/discovery/planning-facts-2026-10-17.md` of the same session.
- DigiExam parsing:
  `src/skriptoteket/domain/curated_apps/exam_conversion/digiexam_ir_contracts.py`
  (`DigiExamIntermediateExam`, `DigiExamIrItem`, `DigiExamIrManualFollowUp`)
  and `parse_source_exam` in
  `src/skriptoteket/application/curated_apps/exam_conversion_producers.py`.
- Native document model:
  `src/skriptoteket/domain/curated_apps/exam_workspace/native_exam_document.py`
  (`NativeExamDocumentOrigin`, kinds `docx_import` and `created` today).
- Workspace import, job and suggestion lane:
  `src/skriptoteket/application/curated_apps/handlers/exam_workspace_documents.py`
  (`ImportExamWorkspaceDocumentHandler`),
  `src/skriptoteket/application/curated_apps/handlers/exam_workspace_enrichment.py`
  (`RequestExamWorkspaceAnswerKeySuggestionsHandler`) and
  `src/skriptoteket/web/api/v1/apps_conversion_hub_exam_workspace.py`.
- Old converter surfaces: `exam_converter_conversions.py`,
  `exam_converter_product.py` and `exam_converter_correction_sessions.py`
  under `src/skriptoteket/application/curated_apps/handlers/`; the kept public
  guest converter's `public_exam_converter_jobs.py` in the same directory;
  ADR-SKRIPT-0087
  (correction sessions) and ADR-SKRIPT-0085 (public conversion exception),
  both `accepted`.
- UI owner: ST-SKRIPT-40-04 and TASK-SKRIPT-40-04-03.

## Tasks

| Task                 | Delivers                                                                                                                                              | Depends on                                                                                         |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| TASK-SKRIPT-39-07-01 | Mapper from `DigiExamIntermediateExam` to `NativeExamDocument`, a DigiExam document origin, the workspace `.dxe` import route and its job             | None; starts now (G22). Supplies DigiExam wording and steps to the TASK-SKRIPT-39-04-06 projection |
| TASK-SKRIPT-39-07-02 | Answer-key suggestions for DigiExam-imported questions through the existing per-question suggestion lane                                              | TASK-SKRIPT-39-07-01                                                                               |
| TASK-SKRIPT-39-07-03 | Removal of the old converter routes, correction sessions, correction overlay, old DigiExam answer-key lane and screens of the signed-in old converter | TASK-SKRIPT-39-07-01, TASK-SKRIPT-39-07-02, and TASK-SKRIPT-40-04-03 shipping the DigiExam entry   |

## Progress

- 2026-10-21 (Hemma orchestrator), closure readiness: the Mac staging walk at `4b321fa1` proved the in-app DigiExam import (signed-in import 202, document opens with 7 questions) and editing a DigiExam-imported document in the workspace editor (document `ea09e8ec…` reached revision 2 and the edit survived a reload) (Mac `.artifacts/staging-walk-l1c-4b321fa1/walk-record.md`, B4 and the last addendum). Exports are proved by TASK-SKRIPT-39-07-01. Open: TASK-SKRIPT-39-07-03 (its tail review waits for the user's decision; its clause that the public guest converter stays is superseded by TASK-SKRIPT-41-02-03).
- 2026-10-22: done (user closure). TASK-SKRIPT-39-07-01, -02 and -03 are done; the open item above is closed. Mac walk at `4b321fa1` (`.artifacts/staging-walk-l1c-4b321fa1/walk-record.md`, B1-B5).

## Verification

- Each task's focused tests and API proof as named in its contract.
- Story proof once TASK-SKRIPT-40-04-03 has shipped the DigiExam entry: a
  Hemma staging browser walk where a teacher imports a real `.dxe` fixture from
  the `Öppna` drawer, edits a question, requests an answer-key suggestion for a
  keyless question, saves, and exports QTI, PDF and DOCX; `/apps/exam-converter`
  no longer opens a converter.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                               |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| S1  | The exam workspace is the main exam conversion and editing app; DigiExam conversion is a secondary input mode inside it, uses the same editor, and the separate DigiExam converter views get no layout work and retire when this story lands (EPIC-SKRIPT-39 E16, user 2026-10-12). |
| S2  | DigiExam exams export in the same QTI 3.0 package shape as other workspace exams (EPIC-SKRIPT-39 E13, user 2026-10-09, amended 2026-10-15).                                                                                                                                         |
| S3  | No unsupported DigiExam types and no new importer research are authorized (EPIC-SKRIPT-39 E12).                                                                                                                                                                                     |
| S4  | This story ships backend, data, export and API only; the DigiExam entry in the Öppna drawer and every new workspace control are built by ST-SKRIPT-40-04; current workspace screens are frozen except bug fixes (G2, user 2026-10-17).                                              |
| S5  | DigiExam imports use the workspace's per-question review and AI answer-key suggestions; the old correction overlay, correction sessions and their routes retire with the old converter; unsupported types keep E12 (G21, user 2026-10-17).                                          |
| S6  | The story starts now as a backend lane; the wait for the PDF and Markdown routes is dropped (G22, user 2026-10-17).                                                                                                                                                                 |
| S7  | The import box shows original wording and a few readable steps for DigiExam imports as for DOCX imports; TASK-SKRIPT-39-04-06 builds that projection (G19, user 2026-10-17).                                                                                                        |
| S8  | The public guest exam converter (ADR-SKRIPT-0085) stays with its routes and modules; this story retires only the signed-in old converter, its correction overlay and correction sessions; a later decision covers the guest converter (user 2026-10-17, G27). The later decision is made (user 2026-10-20): the old guest DigiExam converter is subsumed by the exam workspace, where DigiExam is one input; TASK-SKRIPT-41-02-03 removes it and the public workspace (TASK-SKRIPT-41-02-02) replaces it as the demo that leads guests to an account (EPIC-SKRIPT-41 E5).                       |
