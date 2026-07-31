---
type: task
id: TASK-SKRIPT-26-04-01
title: 'Klassrumskartan: grouping PDF A4 portrait presentation renderer and delivery'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: in_progress
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
story: ST-SKRIPT-26-04
task_kind: story
acceptance_criteria:
- Given a grouping export job is created with `export_kind=pdf`, when the artifact
  is rendered, then the renderer consumes the shared `GroupingExportPresentation`
  model and produces export-owned HTML/CSS that is converted locally to PDF with WeasyPrint
  instead of reusing the live planner DOM or converting the `XLSX` workbook to PDF.
- Given the PDF is generated, when the teacher opens it, then `A4` portrait is the
  default and only page contract in this slice.
- Given the PDF spans one or more pages, when groups are laid out, then class/document
  headings, group labels, member ordering, section boundaries, and left-right row
  pairing remain deterministic and easy to scan on screen and on paper.
- Given a group section is near a page break, when pagination occurs, then the renderer
  avoids orphaning a group heading at the bottom of a page without at least the first
  member row.
- Given the grouping PDF is rendered, when the teacher opens it, then the document
  uses a restrained Skriptoteket-branded letterhead and a two-column grid of framed
  group cards that reduces page count while keeping scan order intuitive.
- Given the PDF succeeds, when the teacher downloads it, then the file is delivered
  through the explicit grouping export job lane with a teacher-safe filename and `Ladda
  ned igen` support from the grouping workspace.
---

## Context

Source: `docs/backlog/prs/pr-0141-klassrumskartan-grouping-pdf-a4-portrait-presentation-renderer-and-delivery.md`. Klassrumskartan: grouping PDF A4 portrait presentation renderer and delivery.

The grouping PDF is important for presentation, but without a locked page contract it could drift into either a weak spreadsheet dump or an inappropriate seating-style poster. Render the first grouping `PDF` as an `A4` portrait digital handout that is clean to post in Teams or Google Classroom and still printable when needed. - The grouping `PDF` is not a poster. Do not reuse seating poster layout, sizing, or naming. - The grouping `PDF` must be rendered from export-owned HTML/CSS and converted locally with WeasyPrint. - The renderer input is the shared `GroupingExportPresentation` model, not the generated workbook. - `A4` portrait is the only supported grouping PDF page contract in this sli

## Decision And Assumption Ledger

| ID | Type | Status | Question/Assumption | Recommendation/Decision | Source |
| --- | --- | --- | --- | --- | --- |
| MIG-TASK-SKRIPT-26-04-01 | migration | closed | How is source meaning preserved? | Preserve the source task contract, current relationships, and status while changing identity only. | ST-SKILL-08-06; TASK-SKRIPT-REP-0003 |

## Story Contract Slice

The task preserves the source implementation slice under its current story parent.

## Contract Inputs

- Source task/PR and audit-approved migration authority.
- Current story or repository relationship in candidate frontmatter.

## Plan

Execute only the bounded plan represented by the source record; do not add scope during migration.

## Implementation Steps

1. Preserve the source implementation or proof sequence.
2. Verify current relationships and focused evidence at task closeout.

## Proof

The source proof obligations are retained as historical evidence below; no execution proof is asserted by this candidate.

## Validation

Run the task-selected focused gates and repository docs validation after parent integration.

## Stop Conditions

Stop for missing authority, unresolved identity/relationship, terminal ancestry, or scope expansion.

## Lessons Learned

The source material is retained verbatim below for migration fidelity.

## Notes

### Source evidence

### Problem

The grouping PDF is important for presentation, but without a locked page contract it could drift
into either a weak spreadsheet dump or an inappropriate seating-style poster.

### Goal

Render the first grouping `PDF` as an `A4` portrait digital handout that is clean to post in Teams
or Google Classroom and still printable when needed.

### Locked design decisions

- The grouping `PDF` is not a poster. Do not reuse seating poster layout, sizing, or naming.
- The grouping `PDF` must be rendered from export-owned HTML/CSS and converted locally with
  WeasyPrint.
- The renderer input is the shared `GroupingExportPresentation` model, not the generated workbook.
- `A4` portrait is the only supported grouping PDF page contract in this slice.
- The document may span multiple pages. Do not force a one-page artifact at the cost of legibility.
- The PDF must keep the same deterministic group order and member order as the `Dela och exportera`
  workbook sheet from `PR-0140`.
- The presentation body uses an explicit two-column grid with left-right row pairing.
- Group sections render as framed cards rather than as loose stacked tables.
- The first page includes a restrained Skriptoteket letterhead with logo.

### Current blocker

- Grouping `PDF` now renders locally with WeasyPrint and is proven on the host lane, including the
  upper-right Skriptoteket logo letterhead.
- The related seating letterhead follow-up is no longer treated as a Sir Convert authorization
  problem.
- `ADR-0075` now locks the cleaner architecture:
  - Klassrumskartan-owned PDF artifacts render locally inside Skriptoteket
  - Sir Convert remains for general conversion workloads, not final seating-PDF rendering
- The remaining seating follow-up is therefore a migration/removal task:
  `PR-0146` moves seating PDF to the same local render/finalize lane as grouping PDF and deletes
  the obsolete Sir Convert-specific webhook/callback dependency from that artifact path.

### Non-goals

- Supporting `A3`, landscape, or teacher-selectable paper sizes.
- Adding poster-style room geometry, seating markers, or classroom fixtures.
- Introducing multiple PDF themes or branding variants.

### Implementation plan

1. Build a PDF renderer view model from the shared presentation contract:
   - add `src/skriptoteket/application/curated_apps/classroom_planner/exports/grouping_pdf_view_model.py`
2. Implement the export-owned HTML/CSS renderer:
   - add `src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/grouping_pdf_renderer.py`
3. Wire the renderer into the grouping export job flow:
   - update `src/skriptoteket/application/curated_apps/classroom_planner/handlers/grouping_export_jobs.py`
   - update the grouping export completion/download helper under
     `src/skriptoteket/application/curated_apps/classroom_planner/handlers/`
4. Keep the SPA grouping export flow stable unless local-PDF completion needs targeted wording
   changes:
   - verify `frontend/apps/skriptoteket/src/views/apps/useGroupingExportFlow.ts`
   - verify `frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspacePane.vue`

### PDF layout specification

- Page size: `A4`
- Orientation: portrait
- Page posture: digital handout first, printout second
- Header block at the top of the first page:
  - document title `Gruppindelning`
  - class name
  - export date
  - restrained Skriptoteket branding / logo
- Group sections are placed in a two-column grid with explicit left-right row pairing.
- Each group section contains:
  - group heading
  - a simple two-column member table with `Nr` and `Elev`
- Group sections should read as framed cards with cohesive spacing, borders, and padding.
- Use generous but compact white space and clear rules/borders, not poster-style oversized geometry.
- Keep branding light and editorial rather than decorative.
- Pagination rule:
  - never leave a group heading alone at the bottom of a page
  - move the heading to the next page if the first member row does not fit with it
  - prefer keeping each group card intact on one page when possible
  - allow a very tall single group to continue only when it cannot fit as one intact card

### File naming

- Filename stem comes from `GroupingExportPresentation.filename_stem`.
- Final PDF filename pattern:
  - `<filename_stem>-a4-portrait.pdf`
- Example:
  - `sa24d-gruppindelning-a4-portrait.pdf`

### Test plan

- Rendering tests proving:
  - `A4` portrait contract
  - deterministic group/member order
  - deterministic two-column left-right card order
  - pagination guard against orphaned headings
- Application tests for local PDF generation, Vault persistence, and download metadata.
- Frontend tests proving the grouping export menu still defaults to `Excel (.xlsx)` while the PDF
  path remains available as `PDF (A4 stående)`.
- Live browser/manual proof:
  - open grouping workspace
  - export `PDF (A4 stående)`
  - confirm download succeeds
  - visually inspect the artifact for digital readability, two-column left-right ordering, framed
    cards, restrained letterhead branding, and clean page breaks

### Rollback plan

- Remove local grouping PDF rendering while preserving the grouping `XLSX` artifact and the shared
  grouping export contract.

## Plan Document Review

No specialist approval is asserted; parent review remains required.

## Implementation Review

No closeout evidence is asserted in this candidate.
