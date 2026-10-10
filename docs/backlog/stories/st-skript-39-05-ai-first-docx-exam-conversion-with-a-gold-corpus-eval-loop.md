---
type: story
id: ST-SKRIPT-39-05
title: AI-first DOCX exam conversion with a gold-corpus eval loop
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-10'
status: ready
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-39
acceptance_criteria:
- Every item of every exam in the eight-exam DOCX corpus converts to its hand-checked
  gold item on each eval run, and anything that cannot be converted becomes a review
  item holding its source text
links:
  decisions: []
backlog_document_profile: contract-derived
---

## Slice Contract

A teacher uploads a DOCX exam in any reasonable layout and gets a native
exam document whose items are ready to edit and export, without deciding
what the app can resolve itself. The rule extractor of ST-SKRIPT-39-04
converts only 3 of the 8 corpus exams; this story replaces rule-first
extraction with an AI-first converter and proves it against a hand-checked
gold corpus.

- **The parser only prepares chunks.** Code segments the DOCX into solid
  chunks (headings, instructions, prompts, options with their line breaks,
  tables, facit text, points). It does not decide what an item asks.
- **AI produces contract-ready items.** The Decisions API and the Responses
  API work in combination with strict JSON and no tools. Calls are batched
  across items, never one call per item. Code validates every item against
  the native document contract; only failing items are sent again, at most
  three rounds. The target is success on the first call.
- **Rules stay minimal and general.** Rules know input types, never one
  exam's wording or labels. A rule is added only when the eval loop shows a
  need.
- **Nothing is lost.** Input that still fails after the retries becomes a
  free-text item holding its source text, marked for review with a Swedish
  note that names why. Export stays blocked until the teacher fixes it.
- **Conversion runs in the background.** Upload returns at once, the
  document shows a converting status and opens when done. The uploaded DOCX
  is kept until the job finishes.
- **Item shapes.** The four current kinds plus a new matching kind. A word
  bank becomes gap text where each gap accepts its own facit word. Any other
  shape becomes a review item.
- **The teacher is asked only about what the app cannot resolve.**
  Check-passing interpretation of the teacher's own facit is applied and
  export-eligible, marked "Tolkad av AI" with undo. Answer keys the AI
  invents without a facit keep the teacher check. The app adds obvious
  misspellings of facit answers within a code-enforced edit distance, never
  synonyms. The gap popover gets "Visa som text".

Out of scope: digital PDF (story 6), QTI import (story 7), exporter
convergence (story 8), and carrying answer-key proposals across saves
(TASK-SKRIPT-39-04-04). This story supersedes TASK-SKRIPT-39-04-03.

## Contract Inputs

- EPIC-SKRIPT-39 (story 5), ST-SKRIPT-39-04, ADR-SKRIPT-0091.
- Corpus: `tests/fixtures/exam_conversion/docx_corpus/` (eight exams with
  facit, `144d6333`) and the current-importer probe in retained session
  `01a1263d-5783-74c7-823d-9b4475c85915`.
- Import handler `application/curated_apps/handlers/exam_workspace_documents.py`
  (169-215); rule extractor `domain/curated_apps/exam_workspace/docx_extraction.py`.
- Native contract and export blockers
  `domain/curated_apps/exam_workspace/native_exam_document.py`; QTI mapping
  `examnet_qti_export.py`; planner and fail-closed validator
  `domain/curated_apps/exam_conversion/examnet_qti_package.py` and
  `examnet_qti_validation.py` (matching rules already present).
- LLM lane: `infrastructure/llm/openai/answer_key_structured_provider.py`,
  daily token lease `infrastructure/repositories/exam_answer_key_token_leases.py`,
  job pattern `exam_answer_key_enrichment_jobs`.
- OpenAI Decisions API (public beta, `gpt-6-luna`) and Responses structured
  outputs; fetch current docs through Context7 before implementation.
- HuleEduOS `examnet-qti-import` empirical observations (2026-08-28):
  matchInteraction directedPair import is proven.

## Tasks

Planned order; each task is scaffolded and contracted before work starts.

1. `TASK-SKRIPT-39-05-01` walking skeleton: one corpus exam runs upload -> stored DOCX ->
   background job -> chunker -> batched AI build -> validation -> review-item
   fallback -> workspace opens -> QTI export passes validation.
2. Gold corpus and eval loop: a gold file per corpus exam confirmed by the
   user, and an eval runner that reports every item mismatch.
3. Corpus breadth: Decisions classification, retries for failing items
   only, and general rules added only where the eval loop shows a need,
   until every corpus item matches its gold.
4. Matching kind: native model, editor, and QTI export.
5. Teacher surface: "Tolkad av AI" with undo, automatic misspellings, and
   "Visa som text".

## Verification

- Eval loop: every item of every corpus exam matches its gold file on each
  run; a change is one change followed by a full corpus rerun.
- Unit tests for chunking, contract validation, the retry bound, and the
  review-item fallback.
- QTI export of every converted corpus exam passes the fail-closed
  validators.
- Backend and frontend gates per `AGENTS.md`.
- Agent-driven browser walk on Hemma staging: upload, wait for conversion,
  review, undo one AI interpretation, save, export QTI.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| A1 | The AI-first converter is this story under EPIC-SKRIPT-39; TASK-SKRIPT-39-04-03 is superseded with a pointer and ST-SKRIPT-39-04 stays as delivered (user decision 2026-10-10). |
| A2 | The parser only segments; AI produces contract-ready items using the Decisions and Responses APIs in combination, strict JSON, no tools, batched across items; only failing items are retried, at most three rounds; first-call success is the target (user direction 2026-10-10). |
| A3 | Rules know input types, never one exam's wording; rules are added only where the eval loop shows a need, one change per full corpus rerun (user direction 2026-10-10). |
| A4 | Unconvertible input becomes a free-text review item holding its source text with a Swedish note; export stays blocked until fixed (user decision 2026-10-10). |
| A5 | Conversion runs as a background job with a visible status; the uploaded DOCX is kept until the job finishes (user decision 2026-10-10). |
| A6 | A matching kind is added; a word bank becomes gap text where each gap accepts its own facit word; other shapes become review items (user decision 2026-10-10). |
| A7 | The pass bar is a user-confirmed gold file per corpus exam; every item must match on every run (user decision 2026-10-10). |
| A8 | Check-passing AI interpretation of the teacher's facit is applied and export-eligible as "Tolkad av AI" with undo (user decision 2026-10-10, carried from 39-04-03 F10). |
| A9 | AI-invented answer keys without a facit keep the teacher check before export (user decision 2026-10-10, carried from F11). |
| A10 | The app adds obvious misspellings of facit answers within a code-enforced edit distance, never synonyms (user decision 2026-10-10, carried from F6). |
| A11 | The gap popover gets "Visa som text" (user decision 2026-10-10, carried from F4). |
| A12 | The app resolves what AI and code can reasonably resolve; the teacher is asked only about the rest (user direction 2026-10-10). |
