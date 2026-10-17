---
type: task
id: TASK-SKRIPT-39-08-03
title: Central-content tags suggested by a Decisions classifier at import and from the drawer
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-16'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-reviewer
  decided_at: '2026-10-17'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'Implementation review approved (review-2, retained 01a149c9-5bc7-7713-ba64-12dee0470bdd evidence/reviews/39-08-03-review-2.md). Closeout review at main bd4d706d (Pi c2153ae4, evidence/reviews/TASK-SKRIPT-39-08-03/closeout-review.md) requested one medium change, F1: the catalog-builder test still expected the pre-tagging source URLs; repaired in 19ef5504. No high finding, so no rereview under the user ruling the closeout review cites. Focused selection rerun at main 44cd0c6b: 55 passed (retained 01a14b79-b714-7f76-bcba-845884716cae evidence/39-08-03-focused.log). No frontend tests and no staging walk by contract (G2/G4).'
task_kind: story
acceptance_criteria:
  - An exam whose course is known when the import runs is saved with central-content tags suggested in its header, each citing the questions that cover it; a GET route serves one course's content items; an enrichment job over a saved exam runs the same suggestion for its course and stores the result on the job row; the document save persists the header tags; a classifier failure never blocks a conversion; the tags checklist and Föreslå innehåll in the metadata drawer are built by ST-SKRIPT-40-04
story: ST-SKRIPT-39-08
backlog_document_profile: contract-derived
---

## Implementation Contract

Skolverket publishes central content per course (gymnasiet) and per year band
(grundskolan) as HTML text with bullet items and no identifiers. A saved exam
carries no statement of which central content it covers. The DOCX import
already classifies every question on the Decisions endpoint (cheap, no
reasoning, a probability per choice), and by that stage the course is known
whenever one was picked at import or the course hint matched uniquely.

This task delivers:

- Snapshot: the catalog generator also fetches the central content for every
  catalog entry (per course for gymnasiet, per subject and band for
  grundskolan), splits the HTML into bullet items, and commits them as a
  second snapshot file keyed by catalog key. A tag id is the catalog key plus
  the normalized item text; the item text is stored with it. A
  `GET .../exam-workspace/courses/{key}/content` route serves one course's
  items for the drawer to load when a course is set.
- Classifier: one domain function builds, per question, one Decisions choice
  over the course's content items plus `Inget av dessa`, using the question
  text the item labeler already sends. A protocol
  `ExamContentTagClassifierProtocol` is implemented on the existing Decisions
  adapter. Aggregation is one rule: an item becomes a suggested tag when at
  least one question's top choice is that item with probability at or above
  one threshold constant (start 0.9); those questions are the tag's citation.
  No per-course or per-subject rules.
- Trigger 1, import: in the labeling stage of the DOCX pipeline, when the job
  carries a picked course or the header course from the unique hint match,
  the classifier runs beside the first labeling pass, metered on the same
  daily token lease. The suggested tags land in the header at assembly. A
  classifier failure is logged, leaves tags empty and never fails or delays
  the conversion.
- Trigger 2, enrichment job: a job on the existing enrichment queue with a new
  source kind over the saved head document suggests tags for the exam's
  course. The job stores its result on the job row. The drawer wiring that
  enqueues it when the course is picked or changed, the `Föreslå innehåll`
  rerun, and applying the suggestions to the draft like answer-key suggestions
  are built by ST-SKRIPT-40-04 (user 2026-10-17, G2/G4).
- Header: `NativeExamHeader` gains `tags`, a list of
  `{id, text, origin: suggested | teacher, question_ids}`, and the document
  save persists them. A course change clears tags of the old course. The
  drawer checklist of the course's content items, with suggested items
  preselected and their citing question labels, is built by ST-SKRIPT-40-04
  (user 2026-10-17, G2/G4).
- No model course suggestion: with no picked course and no unique hint match
  the teacher picks the course in the drawer and the hint stays visible.

Out of scope: exporting tags, searching or filtering exams by tag, any class
label, tags for exams imported through other converters, and every new
control inside the exam workspace (user 2026-10-17, G2/G4).

## Contract Inputs

- Pipeline and endpoint facts: retained session
  `01a145b6-c404-761f-aeef-39de058ba7ca`,
  `evidence/discovery/t3-suggestion-stages-2026-10-16.md`.
- Decisions adapter and labeling composer:
  `src/skriptoteket/infrastructure/llm/openai/decisions_item_labeler.py`,
  `src/skriptoteket/application/curated_apps/item_type_labeling.py`,
  `src/skriptoteket/protocols/item_type_labeler.py`.
- Enrichment queue and the teacher-requested lane pattern:
  `src/skriptoteket/application/curated_apps/handlers/exam_workspace_enrichment.py`,
  `exam_answer_key_enrichment_workspace_lane.py`,
  `frontend/apps/skriptoteket/src/views/apps/exam-workspace/useExamWorkspaceEnrichment.ts`
  and `useExamWorkspaceSaveArrivals.ts`.
- Header model after TASK-SKRIPT-39-05-14 and the course field after
  TASK-SKRIPT-39-08-01 unit U6:
  `src/skriptoteket/domain/curated_apps/exam_workspace/native_exam_document.py`.
- Catalog generator and drawer from TASK-SKRIPT-39-08-01:
  `scripts/build_exam_course_catalog.py`, `ExamWorkspaceMetadataDrawer.vue`.
- Skolverket Syllabus API: `/v1/subjects/{code}` `centralContents[]` (text,
  year, typeOfCentralContent); gymnasiet per-course central content on the
  course detail (verify the endpoint first; not in the recorded probes).
- Retained plan: `evidence/planning/TASK-SKRIPT-39-08-03/plan.md`.

## Core Vertical And Performance

The teacher picks Svenska 2 at import and drops the DOCX; conversion runs
grouping, labeling with the classifier beside it, and build; the saved
document header holds three suggested Svenska 2 tags, each citing its
questions. An enrichment job over the saved exam with course Svenska 3
stores suggested Svenska 3 tags on the job row. The classifier adds one
Decisions request per 200 questions with the course's items as choices,
input tokens only, and no model call when the course is unknown.

## Validation

- Focused backend tests: generator splitting of recorded central-content HTML
  into items with stable ids; classifier payload per question (items plus
  none) and the aggregation rule (threshold, citations, none when all below);
  pipeline test that a classifier failure leaves tags empty and the conversion
  succeeds; job lane test for the tag-suggestion job storing suggestions on
  the job row; header model with tags.
- No frontend tests and no staging walk: this task ships no UI (user
  2026-10-17, G2/G4).

## Stop Conditions

- TASK-SKRIPT-39-05-14 and TASK-SKRIPT-39-08-01 unit U6 have not landed on
  main: do not start.
- The Skolverket course detail carries no central content for gymnasiet
  courses: report to the user before choosing another source.
- The Decisions endpoint rejects the number of choices a course's items
  require: report to the user before splitting or truncating item lists.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Q1  | One classifier on the Decisions endpoint assigns each question a central-content item or none; a tag is suggested when some question reaches the threshold and those questions are its citation; trigger 1 runs in the labeling stage of the import when the course is known, trigger 2 is a background enrichment job over the saved exam; the drawer wiring that runs it when the course is picked or changed is built by ST-SKRIPT-40-04 (user 2026-10-16; amended user 2026-10-17, G2/G4). |
| Q2  | No model course suggestion; with no picked course and no unique hint match the teacher picks in the drawer and the hint stays visible (user 2026-10-16).                                                                                                                                                                                                                                                                                                                                       |
| Q3  | One tag per bullet item of the Skolverket central content; tag id is the catalog key plus the normalized item text and the text snapshot is stored with the tag; the generator commits central content per course and per band (user 2026-10-16).                                                                                                                                                                                                                                              |
| Q5  | A course change clears the old course's tags before the new suggestion runs; a small GET route serves one course's content items for the drawer to load on demand; the drawer is built by ST-SKRIPT-40-04 (user 2026-10-16; amended user 2026-10-17, G2/G4).                                                                                                                                                                                                                                   |
| Q4  | Tags live in the document header next to the course with origin and citing questions; one threshold constant decides preselection; a classifier failure never blocks conversion; the drawer checklist with suggested items preselected is built by ST-SKRIPT-40-04 (user 2026-10-16; amended user 2026-10-17, G2/G4).                                                                                                                                                                          |
