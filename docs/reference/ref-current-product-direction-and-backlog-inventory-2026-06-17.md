---
type: reference
id: REF-current-product-direction-and-backlog-inventory-2026-06-17
title: "Current product direction and backlog inventory rules"
status: active
owners: "agents"
created: 2026-06-17
topic: "product-direction-backlog-inventory"
---

# Current Product Direction And Backlog Inventory Rules

This reference captures the product-direction input that should govern the
next backlog inventory pass. It is not a replacement for the backlog hierarchy;
it is the decision lens that `EPIC-37` applies while deciding which old epics,
stories, and PR-sized tasks remain productive.

For durable product-lane and Sir Convert/Skriptoteket ownership doctrine after
the initial inventory, use
[REF-current-product-lanes-and-sir-convert-boundary-v1](ref-current-product-lanes-and-sir-convert-boundary-v1.md).

## Current Product Center

Skriptoteket is now a teacher-first productivity service built around bespoke
application lanes. User-generated script creation and script running remain
valuable and should be preserved where they still align with current code and
teacher value, but they are no longer the only front-door product story.

The current app-family direction is:

- `Klassrumskartan`: classroom and grouping/seating planning.
- Audio transcription: speech or media to transcript, with saved transcripts,
  speaker overlays, and transcript export actions.
- Exam Converter: exam conversion, correction, editing, sharing, and later QTI
  or source-neutral exam-state workflows.
- Document Converter: general document-format conversion and presentation
  output lanes, including PDF, DOCX, HTML/CSS, and template-shaped outputs.

The main service shell should present these teacher workflows directly. It
should not lead with vanity cards, generic "tool" framing, or broad conversion
copy that hides the specific work a teacher came to do.

## Sir Convert Boundary

Sir Convert-a-Lot remains the owner of heavy conversion and model/runtime work:

- source imports that need complex parsing, OCR, PDF/DOCX/HTML processing, or
  artifact packaging
- hosted LLM or STT/diarization inference
- producer-owned formatter/export artifacts where the output is generated from
  an accepted conversion contract

Skriptoteket should own native product state and simple workflow manipulation:

- saved transcripts and speaker overlays
- teacher-reviewed exam/correction state after conversion
- QTI or source-neutral exam editing, sharing, and assembly once a native app
  state exists
- UI presentation, route structure, file actions, and "Mina filer" ownership

Do not introduce Sir Convert replay, hash-table, fingerprint, or artifact
overlay workflows for native application actions that no longer require a heavy
conversion boundary. That complexity belongs only where the end product still
depends on producer-owned conversion evidence.

## Inventory Classification Rules

Every active/proposed/ready/in-progress/blocked backlog item should receive one
of these outcomes during the inventory:

| Outcome | Meaning |
|---------|---------|
| `keep-active` | Still points at current architecture, current product lanes, or a preserved script/editor capability. |
| `done-state-repair` | The implementation exists in code or docs, but the backlog item was never closed honestly. |
| `superseded-cancel` | The item is no longer the intended implementation path because later architecture or product direction replaced it. |
| `drop-epic` | An epic is no longer a valid active/proposed product lane and should be marked `dropped` with retained rationale. |
| `split-or-rehome` | The idea still has value, but the current backlog item is too broad or belongs under a newer epic/story. |
| `needs-decision` | The item cannot be fairly classified without a product or architecture decision record. |

Historical documents should be retained unless deletion is explicitly useful
and safe. The main cleanup is status truth, crosslink truth, and clear
supersession rationale, not erasing history.

## Audit Evidence Requirements

Before a backlog item is marked `done`, `canceled`, or `dropped`, the audit
should name the evidence:

- code paths, docs, ADRs, reviews, or proof artifacts that show it is done
- the later story/PR/ADR/implementation that supersedes it
- the reason it is no longer aligned with the current product direction
- any preserved value that should be moved into a new story instead of lost

For old script-authoring and runner work, the audit must distinguish between
"no longer front-door product positioning" and "no longer valuable." Script
creation, the editor, the runner, and governance workflows should not be
scrapped merely because bespoke apps are now the main product proposition.
