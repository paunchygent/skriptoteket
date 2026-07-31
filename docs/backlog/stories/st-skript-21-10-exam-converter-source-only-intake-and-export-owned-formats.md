---
type: story
id: ST-SKRIPT-21-10
title: Exam Converter source-only intake and export-owned formats
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-21
acceptance_criteria:
- Given a teacher starts an Exam Converter job, when intake renders or submits, then
  the active product flow requires only one governed source exam file and no optional
  marked, graded, result, or supporting exam upload is shown, accepted as current
  product intent, or included in the job spec unless a future accepted contract reintroduces
  it.
- Given the answer-key enrichment stage is available, when the source exam lacks machine-readable
  facit, then Skriptoteket uses the configured LLM enrichment plus teacher review/editor
  workflow instead of asking the teacher to supply a marked exam file.
- Given target files are artifacts of the converted/replayed exam, when the teacher
  starts conversion, then the product requests the currently supported target artifacts
  by default and defers the visible choice of download/save format to the `Filer`
  surface after conversion and review.
- Given a help or question-mark icon is visible in the intake rail or file surface,
  when the teacher hovers, focuses, or activates it, then it opens accessible teacher-facing
  help; orphaned icons without a tooltip/popover are removed.
- Given DOCX is added later, when the target contract exists, then DOCX appears as
  another post-conversion file action using the same source-neutral exam state as
  PDF/QTI, not as a separate early target-selection step.
- Given the future QTI/editor direction lands, when a converted test is saved, then
  Skriptoteket treats the source-neutral exam representation as editable, shareable
  product state that can feed PDF, DOCX, QTI, and later question-pool workflows.
- Given Conversion Hub remains the heavy conversion boundary, when teachers edit,
  share, or assemble tests later, then lightweight test editing and question-pool
  work happens in Skriptoteket while Sir Convert remains responsible for heavy source
  import, LLM enrichment, OCR/PDF, and model-backed conversions.
retired_ids:
- ST-21-10
---

## Context

### Source: Context

The authenticated Exam Converter still reflects an older migration model:
teachers can provide an optional marked/result PDF and choose PDF/QTI target
files before the test has been converted. That flow no longer matches product
direction. Teachers should provide the source exam file only; missing
machine-marked facit is handled by the LLM answer-key enrichment and
teacher-review workflow.

The current code and Sir Convert consumer contract use DigiExam `.dxe`
(`digiexam_dxe`) as the governed source. If product copy or an upstream contract
introduces different DXC/DXE naming, a PR must resolve that naming against the
producer contract before changing accepted suffixes or source format literals.

Target formats are also being reframed. PDF, QTI, and future DOCX are not
meaningful early choices for many teachers. They are export/download/save
decisions after the teacher can inspect the converted test, answer-key state,
and file readiness. The product should request the currently supported target
artifacts by default and let the teacher decide what to download or save later.

This story also captures the longer direction: converted tests should become a
source-neutral editable representation in Skriptoteket. That state can later
support a QTI-oriented editor, DOCX/PDF output, sharing between teachers, and a
taggable question pool. Sir Convert remains the heavy conversion service for
import, LLM enrichment, OCR/PDF, STT, and other model-backed work; simple
authoring and assembly belongs in Skriptoteket.

## Epic Contract Slice

### Source: Scope

- Remove optional marked/result/supporting exam upload from active Exam
  Converter intake and request construction.
- Treat the LLM key-enrichment plus teacher review/editor workflow as the
  supported route for missing machine-marked answer keys.
- Remove visible early target selection from the intake rail; keep current
  supported targets requested by default until the producer/export contract
  changes.
- Move teacher-visible file-format choice to post-conversion `Filer` actions:
  download and save to Mina filer.
- Make any remaining help/question-mark affordance accessible, or remove it if
  the early selector disappears.
- Plan future DOCX as a first-class target artifact over the same source-neutral
  exam state used for PDF/QTI.
- Keep the future QTI editor, exam-state persistence, sharing, tagging, and
  question-pool assembly as follow-up slices instead of coupling them to the
  immediate intake simplification.

## ADR Coverage

The source does not provide a separate adr coverage section; no additional adr coverage is recorded.

## Contract Inputs

The source does not provide a separate contract inputs section; no additional contract inputs is recorded.

## Live Verification Plan

### Source: Implementation Slices

1. `PR-0356` handles the immediate source-only intake and export-owned format
   UX: remove optional supporting upload, remove visible early target selection,
   keep current targets requested by default, and update tests/docs/proof.
   The authenticated lane is the local implementation focus; the public one-time
   lane cleanup is split into `PR-0357`.
2. A later DOCX contract slice should add the producer/Gateway/Skriptoteket
   artifact contract, labels, file actions, and output proof.
3. A later exam-state persistence/editor slice should decide the source-neutral
   editable representation, ownership model, save/share semantics, and QTI
   editor surface.
4. A later question-pool slice should add sharing, tagging, discovery, and
   assembly workflows over the saved editable exam state.

## Non-Goals

### Source: Non-Goals

- No PDF output template redesign in the first simplification PR.
- No DOCX artifact implementation until the Sir Convert/HuleEdu/Skriptoteket
  artifact contract exists.
- No QTI editor, question-pool, sharing, tagging, or test assembly UI in the
  immediate PR.
- No local Skriptoteket conversion engine for heavy imports.
- No change to protected-auth proof requirements: authenticated UI proof still
  enters through the HuleEdu browser-session ceremony.

## Notes

### Source: Notes

- `ST-21-03` remains historical authority for the original public and
  authenticated artifact lanes. This story supersedes its optional graded-result
  upload and early target-selection assumptions for new work.
- `ST-21-04` remains authority for durable teacher corrections and replayed
  artifact references. This story does not weaken the rule that corrected file
  actions must come from replay/export evidence, not original or stale artifacts.
- `ST-21-09` remains authority for coherent Gateway/Sir Convert trust lanes
  before heavy remote inference proof.
- `PR-0357` is the governed follow-up for removing the historical public
  one-time `graded_result_pdf`/target-selection contract after the
  authenticated source-only intake slice.
- [REF-current-product-lanes-and-sir-convert-boundary-v1](../../reference/ref-current-product-lanes-and-sir-convert-boundary-v1.md)
  is the current ownership doctrine for later Exam Converter work: Sir Convert
  owns heavy source import, enrichment, source bindings, and producer artifacts;
  Skriptoteket owns native exam state, review, editing, sharing, QTI/editor
  direction, and post-conversion file actions.

### Source: ST-21-10: Exam Converter Source-Only Intake And Export-Owned Formats



## Decision And Assumption Ledger

The source does not provide a separate decision and assumption ledger section; no additional decision and assumption ledger is recorded.

## Plan Document Review

The source does not provide a separate plan document review section; no additional plan document review is recorded.

## Story Closeout Review

The source does not provide a separate story closeout review section; no additional story closeout review is recorded.
