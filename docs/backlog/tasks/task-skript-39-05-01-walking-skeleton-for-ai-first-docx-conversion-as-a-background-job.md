---
type: task
id: TASK-SKRIPT-39-05-01
title: Walking skeleton for AI-first DOCX conversion as a background job
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-10'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- Uploading the Chapter 4 poetry quiz DOCX returns at once, the workspace shows a
  converting status, and the exam opens with AI-built items that pass the native contract,
  where any chunk that fails after the retries is a review item holding its source
  text, and the QTI export passes the fail-closed validators
story: ST-SKRIPT-39-05
backlog_document_profile: contract-derived
---

## Implementation Contract

Build the thinnest end-to-end path of the AI-first converter
(ST-SKRIPT-39-05) on one corpus exam, the Chapter 4 poetry quiz. The current
rule extractor turns it into one empty free-text item. After this task the
quiz converts through the AI path into real items and exports to QTI.

- **Upload returns at once.** `POST /exam-workspace/documents` stores the
  uploaded DOCX and queues a conversion job instead of extracting in the
  request. The response tells the SPA the document is converting.
- **Converting status in the workspace.** While the job runs, the workspace
  shows "Konverterar provet …" and polls the job status. When the job
  succeeds the exam opens; when the job fails the teacher sees what happened
  in Swedish. The pattern follows the existing enrichment status route.
- **The DOCX is kept only until the job finishes** (story term A5). It is
  deleted when the job succeeds or fails.
- **The chunker only segments.** Code splits the DOCX into ordered chunks:
  headings, paragraphs with their `w:br` line breaks kept, tables, and facit
  lines, each with a stable source anchor. It decides nothing about what an
  item asks.
- **One batched build call.** One Responses structured-output call (strict
  JSON schema, no tools) receives all chunks and returns all items in the
  native item shape for the four current kinds. It uses the existing
  answer-key provider lane, profile and daily token lease. The Decisions API
  is not part of this task; it arrives in task 3.
- **Code validation and retries for failing items only.** Each returned item
  is checked against the native document contract. A check also requires
  that student-visible text and facit answers come from the source chunks,
  and that points match the source. Failing items alone are sent again, at
  most three rounds in total, each round drawing on the lease.
- **Nothing is lost** (A4). A chunk whose item still fails, or every chunk
  when the provider is disabled, out of lease, or unavailable, becomes a
  free-text item holding its source text, `review_required`, with a Swedish
  note naming why. The document always opens.
- **Provenance.** AI-built items carry parse origin `llm_parsed`. Facit
  answers taken from the source carry their existing source-provided key
  origin. The "Tolkad av AI" teacher surface is task 5.
- The rule extractor is no longer called from import. Remove it with its
  tests when nothing else uses it.

## Contract Inputs

- ST-SKRIPT-39-05 terms A2, A4 and A5; EPIC-SKRIPT-39; ADR-SKRIPT-0091.
- Fixture `tests/fixtures/exam_conversion/docx_corpus/chapter_4_poetry_and_lyrics_quiz_med_facit.docx`.
  Choice options are separated by `w:br` inside one paragraph.
- Import route `web/api/v1/apps_conversion_hub_exam_workspace.py:57` and handler
  `application/curated_apps/handlers/exam_workspace_documents.py:169-215`.
  The DOCX is not stored today.
- Native contract `domain/curated_apps/exam_workspace/native_exam_document.py`
  (`NativeParseOrigin.llm_parsed`, export blockers at 410-428).
- Provider lane `infrastructure/llm/openai/answer_key_structured_provider.py`.
  Strict `json_schema`, `max_output_tokens` 4096. The lease reserves input
  plus max output and never refunds a failed attempt.
- Job pattern: `exam_answer_key_enrichment_jobs` (SKIP LOCKED claim,
  heartbeat lease, worker loop `workers/execution_queue_worker.py`). The
  workspace status route is `web/api/v1/apps_conversion_hub_exam_workspace_enrichment.py`.
- QTI export `domain/curated_apps/exam_workspace/examnet_qti_export.py`. The
  validator is `domain/curated_apps/exam_conversion/examnet_qti_validation.py`.
- OpenAI Responses structured outputs. Fetch current docs through Context7
  before implementation.

## Core Vertical And Performance

`upload DOCX -> store DOCX, queue job, respond -> worker chunks the DOCX ->
one batched Responses build -> code validation -> failing items retried
(max 3 rounds) -> remaining failures become review items -> version 1 saved
-> DOCX deleted -> workspace leaves "Konverterar" and opens -> QTI export
passes validation`.

- One build call for the whole exam is the norm. Size `max_output_tokens`
  for a full exam rather than per item, and record the measured input and
  output tokens for the quiz.
- Retries carry only failing items and their chunks, never the whole exam.

## Validation

- Unit tests:
  - the chunker on the quiz (options kept as separate lines);
  - each validation rejection (invented student text, invented facit
    answer, changed points, schema mismatch);
  - the three-round retry bound;
  - the review-item fallback when the provider is disabled, out of lease,
    or failing.
- Integration test on the quiz with a recorded provider response: the
  expected items, kinds, points and answer keys, saved as version 1, the
  DOCX deleted, and the QTI export passing the fail-closed validators.
- Migration tests for any schema change.
- Backend gates per `AGENTS.md`: lint, typecheck, focused tests. Frontend
  gates for the converting status per `integrated-frontend-stack`.
- Agent-driven browser walk on Hemma staging with the live provider:
  1. Upload the quiz.
  2. See "Konverterar".
  3. The exam opens with its items.
  4. Export QTI and inspect it.

## Stop Conditions

- Stop if a validation check would have to be relaxed for the AI to pass.
- Stop if a provider or lease failure could leave a document that never
  opens.
- Stop if the build needs one call per item.
- Stop if rules start encoding the quiz's own wording.
- Production acceptance remains user-owned.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| S1 | The skeleton proves the AI path on the Chapter 4 poetry quiz from the corpus (implementation choice within ST-SKRIPT-39-05, 2026-10-10). |
| S2 | Import stores the DOCX and queues a conversion job; the workspace shows a converting status and opens when done; the DOCX is deleted when the job ends (ST-SKRIPT-39-05 A5, user decision 2026-10-10). |
| S3 | One batched Responses strict-JSON call builds all items; only failing items are retried, at most three rounds; the Decisions API joins in task 3 (ST-SKRIPT-39-05 A2, user direction 2026-10-10). |
| S4 | Every chunk that cannot be built, including when the provider is disabled, out of lease, or unavailable, becomes a free-text review item holding its source text with a Swedish note (ST-SKRIPT-39-05 A4, user decision 2026-10-10). |
| S5 | Import no longer calls the rule extractor; it is removed once unused (ST-SKRIPT-39-05 A2, user direction 2026-10-10). |
