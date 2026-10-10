---
type: task
id: TASK-SKRIPT-39-04-03
title: AI item interpretation at DOCX import
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-10'
status: proposed
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- A DOCX exam whose items the rules cannot resolve imports with AI-interpreted items
  that show the student only source text, ask only what the item asks, and accept only
  facit-derived answers, so Exam.net scores a correct student answer as correct; when
  the AI fails, the teacher still gets a valid rule-based item marked for review
story: ST-SKRIPT-39-04
backlog_document_profile: contract-derived
---

## Implementation Contract

Build the confidence-gated LLM remainder that ST-SKRIPT-39-04 promised for
DOCX import. Today the import is rule-only: items the rules cannot resolve
are only marked for review, and a facit line with several labels becomes one
gap holding the whole line (walk finding W9 in TASK-SKRIPT-39-04-02). Whether
a labeled value is given to the student or asked of them depends on the
item's instruction, which rules cannot read in general. The fix must work for
DOCX exams in general, not for one fixture.

- **Rules do only format-general work.** The deterministic extractor
  segments the document into items and sub-items and reads headings, points,
  instructions, legends, and each sub-item's raw facit text. It stops
  deciding what is given or asked on lines it cannot resolve.
- **AI runs automatically at import, only for unresolved items.** An item is
  unresolved when a sub-item line carries several answer labels, a sub-item
  has no answer, or the rule confidence is below the review threshold. Items
  the rules resolve cost no tokens. Each call sends one item with its
  instruction and the legends that apply, not the whole document.
- **Tier 1, classification (OpenAI Decisions API, `gpt-6-luna`).** Code
  builds candidates format-generally: each sub-item's labeled values and the
  alternatives inside them (for example `predikativ/predikatsfyllnad`). The
  Decisions API answers typed questions about those candidates against the
  item's instruction and legends: whether each value is given or asked
  (`choice`), whether a separator marks alternative answers (`predicate`),
  and the item kind (`choice`). It cannot produce text, so every outcome is
  an option code built. Code assembles the item from the answers.
- **Tier 2, generation (existing Responses structured-output lane).** Used
  only when code cannot build candidates for an unresolved item, and for
  AI-suggested answer variants (spelling variants, synonyms). It returns a
  native item in a fixed schema: a kind from the Exam.net-supported set and
  per sub-item an ordered sequence of text and gap segments, each gap holding
  facit-derived answers and suggested variants.
- **Confidence gates both tiers.** A Decisions answer below the confidence
  threshold, or a `refusal`, leaves the rule-based item for teacher review.
  The Decisions API is in public beta; its unavailability never blocks
  import.
- **Code-enforced checks box the AI in.** A proposal is rejected unless:
  every student-visible text segment comes from the source item; every
  facit-derived answer comes from the item's facit text (splitting
  alternatives such as `predikativ/predikatsfyllnad` is allowed); points and
  item order are unchanged; the kind is Exam.net-supported; and the result
  passes the existing native export validation.
- **Failure never breaks an item.** Invalid, missing, or over-budget AI
  output is discarded and the rule-based item stays, marked review_required,
  as today. The import always creates and opens the document.
- **The teacher decides.** An AI interpretation arrives as a proposal in the
  Detaljer drawer, using the existing proposal and review path; export stays
  blocked until the teacher approves it. AI-suggested variants are listed
  separately and the teacher ticks each one; only facit-derived answers are
  accepted by default.
- **The teacher can correct a gap.** The gap popover gets a "Visa som text"
  action that turns a gap into fixed text.

## Contract Inputs

- ST-SKRIPT-39-04 (deterministic extraction with per-item confidence, LLM
  remainder and answer-key proposals), EPIC-SKRIPT-39, ADR-SKRIPT-0091.
- Rule extractor: `src/skriptoteket/domain/curated_apps/exam_workspace/docx_extraction.py`
  (`_split_answer_label`, `_build_item`, `multiple_answer_labels_detected`).
- Import handler: `src/skriptoteket/application/curated_apps/handlers/exam_workspace_documents.py`
  (lines 169-215); no LLM runs at import today.
- Existing answer-key proposal lane to reuse for provider, lease, schema
  validation, proposal storage, and review:
  `domain/curated_apps/exam_workspace/answer_key_prompts.py`,
  `answer_key_view.py`, `application/curated_apps/handlers/exam_answer_key_enrichment_jobs.py`,
  `infrastructure/llm/openai/answer_key_structured_provider.py`. That lane
  can only fill keys for existing gaps; it cannot change structure.
- Fixture `tests/fixtures/exam_conversion/real_inputs/grammatik_omprov_examnet_import_med_facit.docx`
  (Fråga 4, 6 and 7 are the known unresolved shapes).
- TASK-SKRIPT-39-04-02 walk finding W9.
- OpenAI Decisions API guide (`https://developers.openai.com/api/docs/guides/decisions`,
  public beta, `POST /v1/decisions`, `gpt-6-luna`, `predicate`/`choice`/`score`
  questions); fetch current docs through Context7 before implementation.

## Core Vertical And Performance

`DOCX import -> rules segment items -> unresolved items to AI, one call each
-> code checks accept or discard -> Redigera shows AI proposals in Detaljer
-> teacher approves, ticks variants, or uses Visa som text -> save -> QTI
export with one keyed text entry per asked slot`.

- Token use scales with unresolved items only; resolved items never reach
  the AI. Decisions and Responses calls both draw on the daily token lease
  and follow the provider policy; Decisions bills input tokens only.
- Import stays responsive: AI work runs as a job after the document is
  created, and proposals appear when ready.

## Validation

- Unit tests for the checks: invented student text, invented facit answers,
  changed points or order, unsupported kind, and invalid JSON are each
  rejected and leave the rule-based item.
- Varied DOCX layouts beyond the grammatik fixture: given-versus-asked
  labels, several asked labels, alternatives in the facit, unlabeled answers,
  and items the rules already resolve (no AI call).
- Fixture test on the grammatik DOCX with a recorded provider response:
  Fråga 4 asks only the satsdel, Fråga 6 asks type and satsdel, Fråga 7 asks
  both bisatser and both satsdelar, and `predikativ/predikatsfyllnad` is two
  accepted answers.
- QTI export passes the existing fail-closed validators.
- Backend gates per `AGENTS.md` (lint, typecheck, focused tests) and the
  frontend gates for the drawer and popover changes.
- Agent-driven browser walk on Hemma staging: import, review AI proposals,
  tick a variant, use Visa som text, save, export QTI and inspect it.

## Stop Conditions

- Stop if a check would have to be relaxed for the AI to succeed.
- Stop if an AI failure could block import or produce an item that fails
  export validation.
- Stop if rules start encoding one fixture's label vocabulary to decide
  given versus asked.
- Production acceptance remains user-owned.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| F1 | The merged facit value is fixed in its own task under ST-SKRIPT-39-04 (user decision 2026-10-10). |
| F2 | Rules may not decide given versus asked from one fixture's layout; DOCX import must work for exams in general, with AI interpretation for what rules cannot resolve (user decision 2026-10-10, replacing one gap per label). |
| F3 | A gap holds any number of accepted answers, never one answer per label (user decision 2026-10-10); the AI may split facit alternatives into separate accepted answers of one gap. |
| F4 | The gap popover gets "Visa som text", turning a gap into fixed text (user decision 2026-10-10). |
| F5 | AI interpretation runs automatically at import, only for items the rules could not resolve (user decision 2026-10-10). |
| F6 | AI-suggested answer variants are separate suggestions the teacher ticks; only facit-derived answers are accepted by default (user decision 2026-10-10). |
| F7 | The AI is boxed in by code-enforced checks; invalid output is discarded and the rule-based item stays, so AI failure never breaks import or an item (user decision 2026-10-10). |
| F8 | This task is rescoped from label splitting to AI item interpretation at import, including Visa som text (user decision 2026-10-10). |
| F9 | Decisions API first (`gpt-6-luna`, typed classification of code-built candidates), with the existing Responses structured-output lane only as fallback for items without buildable candidates and for variant suggestions (user decision 2026-10-10; Decisions API verified in OpenAI docs as public beta, input-only pricing, EU residency). |
