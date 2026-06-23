---
type: reference
id: REF-current-product-lanes-and-sir-convert-boundary-v1
title: "Current product lanes and Sir Convert boundary"
status: active
owners: "agents"
created: 2026-06-18
updated: 2026-06-22
topic: "product-direction"
---

# Current Product Lanes And Sir Convert Boundary

This reference is the durable doctrine for `ST-37-02` / `PR-0360`. It turns the
post-inventory product direction into a stable planning boundary for later UI,
app-presentation, conversion, exam, and transcript work.

It does not rename routes, app ids, API modules, or production copy by itself.
Those implementation choices belong to later reviewed slices.

## Current Teacher-Facing Lanes

| Lane | Teacher job | Current code reality | Next planning owner |
|------|-------------|----------------------|---------------------|
| Klassrumskartan | Plan classrooms, groups, seating, rules, exports, and sharing. | Bespoke curated app `classroom.group-seating-studio`. | `EPIC-26`, `EPIC-27`, `EPIC-29`, `EPIC-36`, and `ST-37-03` shell work. |
| Audio Transcription | Convert speech or media to saved transcript, review speakers, and export transcript formats. | Authenticated transcript workflow currently lives under `documents.conversion_hub` technical surfaces. | `EPIC-21` transcript stories and later app-presentation decomposition. |
| Exam Converter | Create exams, import exams, edit structure, items, points, answer keys, and metadata, review/correct answer-key state, export files, and grow toward source-neutral QTI/share workflows. | Public and authenticated Exam Converter currently live under `documents.conversion_hub` technical surfaces. | `ST-21-10`, `PR-0357`, `ST-21-04`, and later exam-state/editor slices. |
| Document Converter | Convert and prepare presentation/document formats such as PDF, DOCX, HTML/CSS, Markdown, and template-shaped outputs. | Approved as a visible shell lane by the C2 home mockup, but the active code still has no proven truthful route; the registry title says `Konvertera dokument` while the bespoke host currently presents Exam Converter. | `ST-37-04` app-presentation decomposition and a reviewed route-visible slice before runtime links or registry implementation. |

`documents.conversion_hub` remains a technical compatibility shell until later
work decomposes app presentation. New product planning should not use the broad
"Conversion Hub" name as the teacher-facing concept unless it explicitly means
historical or technical compatibility.

## Sir Convert Owns Heavy Conversion

Sir Convert-a-Lot remains the producer/runtime authority when the workflow
depends on conversion, model, or artifact evidence that Skriptoteket should not
own locally:

- parsing and packaging source imports such as PDF, DOCX, HTML, Markdown,
  DigiExam, and other conversion sources
- OCR, layout extraction, LLM enrichment, STT, diarization, and other hosted
  model/runtime work
- producer-owned artifacts, manifests, source bindings, hashes, signatures, and
  artifact-readiness evidence
- deterministic formatter/export artifacts produced from accepted source state
  or accepted transcript JSON
- heavy remote inference proof and trust-lane coherence through HuleEdu Gateway

Skriptoteket may call Sir Convert through the accepted HuleEdu Gateway or local
producer boundary, but should not expose Sir Convert service credentials,
workdirs, raw upstream ownership, or browser-direct authority.

## Skriptoteket Owns Native Product State

Skriptoteket owns teacher-facing product state after heavy conversion has
produced an accepted source representation:

- saved transcripts, speaker overlays, selected export actions, and Mina filer
  handoff
- Exam Converter correction sessions, source-bound authoring state,
  teacher-reviewed answer-key decisions, exam creation, structure, item, point,
  answer-key, and metadata editing, file actions, and later source-neutral exam
  state
- sharing, editing, assembly, QTI/editor workflows, future question pools, and
  document-facing file actions once native state exists
- route structure, app presentation, dashboards, help, copy, and UI workflow
  ownership
- owner scoping, access checks, local state persistence, and user-visible
  recovery or stale-state messaging

Native app state must not be routed through Sir Convert replay, hash-table,
fingerprint, or artifact-overlay workflows merely because those workflows
existed for heavy conversion. Use Sir Convert only when the product needs fresh
producer evidence or generated artifacts.

## Boundary Matrix

| Workflow question | Owner | Notes |
|-------------------|-------|-------|
| Does the user need a source file parsed, OCRed, enriched, diarized, or converted into a producer representation? | Sir Convert | Skriptoteket coordinates and persists product-side references. |
| Does the user need to edit, share, assemble, or review already-converted app state? | Skriptoteket | Sir Convert may later replay/export from the current state, but does not own teacher state. |
| Does the output need producer-owned evidence, source binding, artifact readiness, or conversion manifest proof? | Sir Convert | Keep hashes/signatures/artifact references producer-owned. |
| Does the action only change labels, teacher decisions, selected file actions, or product presentation? | Skriptoteket | Avoid unnecessary replay/fingerprint coupling. |
| Is the operation a public anonymous upload or compute path? | Sir Convert plus Skriptoteket public boundary | Must stay scoped, abuse-controlled, TTL-bound, and direct-download only unless a later accepted contract expands it. |

## Lane-Specific Doctrine

### Klassrumskartan

Klassrumskartan is already a bespoke native app lane. Its classroom, roster,
rules, smart grouping/seating, export, sharing, and guest-upgrade state stays in
Skriptoteket-owned modules. Sir Convert is not the default engine for classroom
state changes.

### Audio Transcription

Sir Convert owns STT/diarization and transcript formatter artifacts. Skriptoteket
owns saved canonical transcript JSON, speaker overlays, selected export actions,
Mina filer handoff, and transcript UI state. Browser-owned replay/export sagas
are retired; future transcript follow-ups should remain product-owned unless
they truly need producer conversion evidence.

### Exam Converter

Sir Convert owns heavy source import, LLM answer-key enrichment, OCR/PDF or
DigiExam parsing, source bindings, and replay/export artifacts. Skriptoteket
owns durable teacher correction sessions, source-bound authoring state,
teacher-reviewed answer-key decisions, exam creation, structure, item, point,
answer-key, and metadata editing, future source-neutral exam state, QTI
editing, sharing, and question-pool workflows.

`ST-21-10` is the active direction: intake is source-only, optional marked or
graded-result upload is not current product intent, and visible target choice
belongs to post-conversion file actions.

### Document Converter

Document Converter is the approved teacher-facing lane for format and
presentation output work: PDF, DOCX, HTML/CSS, Markdown, template-shaped output,
and platform-ready presentation artifacts. The lane may appear in approved
shell design, but runtime links must wait for a truthful reviewed route target.
It should not be conflated with Exam Converter or Audio Transcription merely
because all three historically lived under broad Conversion Hub language.

`ST-37-04` owns app-presentation decomposition before implementation changes
app registry titles, descriptions, or route surfaces. `PR-0364` may use the
approved C2 mockup as home design direction, but must stop rather than fake a
Document Converter route.

## Script, Editor, And Runner Preservation

The script editor, runner contracts, file references, Vault, and governance
tools remain valuable platform capabilities. `Kodredigerare` is a first-class
app surface in the approved authenticated shell, while `Mina körningar` is no
longer part of the home-surface proposition.

Future shell and app-presentation work should present editor capability as an
aligned authoring/power-user app while centering the teacher-facing productivity
lanes and files/materials flow above retired run-history chrome.

## Implementation Guidance

- Use this reference before `PR-0357`, `PR-0361`, `PR-0362`, and later
  Document Converter or exam-state/editor work.
- Do not rename app ids or routes in this reference. Use later implementation
  slices with tests and browser proof.
- Do not change Sir Convert/HuleEdu contracts here. Use accepted ADRs or
  cross-repo stories for producer/Gateway contract changes.
- Keep `EPIC-37` review state explicit: this doctrine was created under the
  user's 2026-06-18 docs-only implementation direction and does not by itself
  approve the proposed epic.
