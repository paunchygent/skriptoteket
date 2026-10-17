---
type: task
id: TASK-SKRIPT-39-07-02
title: Answer keys for DigiExam imports through the workspace's per-question suggestions
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-17'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - Questions imported from DigiExam without keys get answer-key suggestions through the same per-question suggestion lane as DOCX imports
story: ST-SKRIPT-39-07
backlog_document_profile: contract-derived
---

## Implementation Contract

The old converter completes missing DigiExam answer keys in its own lane: a
token-leased AI pass at conversion time (`ExamAnswerKeyEnrichmentDxeLane`,
source kind `dxe`) whose proposals the teacher corrects in the correction
overlay. Under G21 a DigiExam import instead uses the workspace's per-question
review and AI answer-key suggestions, the same lane DOCX imports use.

The workspace lane is source-neutral today: `answer_key_item_views` selects
every keyed item whose answer key origin is `absent`, and
`RequestExamWorkspaceAnswerKeySuggestionsHandler` enqueues one suggestion job
for the whole document or for one item. The teacher requests suggestions; a
DOCX import does not request them on its own. A DigiExam import follows the
same rule.

This task delivers:

- DigiExam-imported questions without a key (`absent` after
  TASK-SKRIPT-39-07-01) get suggestions through the existing
  `POST /exam-workspace/documents/{lineage_id}/answer-key-suggestions` route,
  for the whole document and for one question, with no DigiExam-specific
  lane, trigger or prompt.
- Suggestions on DigiExam questions land and are reviewed exactly as on DOCX
  questions: each suggestion stays on its question, AI-invented keys stay
  behind teacher review (EPIC-SKRIPT-39 E4), and keys present in the `.dxe`
  (`source_provided`) are never offered for suggestion.
- Any gap the DigiExam document shape exposes in the lane (for example an
  item view or prompt that assumes DOCX-only data) is fixed in the shared lane,
  not in a DigiExam copy.

Out of scope: any workspace UI (G2), the old `dxe` lane and its removal
(TASK-SKRIPT-39-07-03), and automatic suggestion requests after import.

## Contract Inputs

- Story ST-SKRIPT-39-07 terms S1-S7; TASK-SKRIPT-39-07-01 (the DigiExam
  import and its key provenance mapping).
- Suggestion lane:
  `src/skriptoteket/application/curated_apps/handlers/exam_workspace_enrichment.py`,
  `src/skriptoteket/application/curated_apps/handlers/exam_answer_key_enrichment_workspace_lane.py`,
  `src/skriptoteket/domain/curated_apps/exam_workspace/answer_key_view.py`
  (`answer_key_item_views`), `answer_key_prompts.py` and
  `native_exam_suggestions.py`;
  `src/skriptoteket/web/api/v1/apps_conversion_hub_exam_workspace_enrichment.py`.
- Old lane for comparison only:
  `src/skriptoteket/application/curated_apps/handlers/exam_answer_key_enrichment_dxe_lane.py`.
- Epic terms E4 and E7 (token lease carries over through the shared lane).

## Core Vertical And Performance

A teacher imports a `.dxe` with keyless choice and gap questions, then
requests suggestions for the document and for one question. The existing route
queues one job per saved version and question set, the worker answers within
the daily token lease, and the suggestions appear on their questions for
review. A key already in the `.dxe` is not sent to the model.

## Validation

- Focused tests: a document imported from a DigiExam fixture yields item views
  for exactly its keyless keyed questions; a whole-document and a one-question
  request on it each queue one job; the stored suggestions attach to their
  questions with the same review state as on a DOCX import; a
  `source_provided` key is never in the request.
- API proof against the running app: import the real fixture, request
  suggestions for the document, poll the job and read the suggestions; the
  responses are retained in the task's evidence.

## Stop Conditions

- The shared lane needs a DigiExam-specific prompt or schema to give usable
  suggestions: report to the user before adding one.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                          |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| K1  | DigiExam imports use the workspace's per-question review and AI answer-key suggestions; the old correction overlay, correction sessions and their routes retire with the old converter (G21, user 2026-10-17). |
| K2  | AI-invented answer keys (no facit) stay behind teacher review (EPIC-SKRIPT-39 E4, amended 2026-10-10).                                                                                                         |
| K3  | Answer-key completion is remote-API-first under the daily token lease (EPIC-SKRIPT-39 E7).                                                                                                                     |
| K4  | This task ships backend and API only; new workspace controls are built by ST-SKRIPT-40-04 (G2, user 2026-10-17).                                                                                               |
| K5  | The task is part of the backend lane that starts now (G22, user 2026-10-17).                                                                                                                                   |
