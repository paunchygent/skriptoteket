---
type: pr
id: PR-0278
title: "ST-26-08 shared print PDF visual redesign"
status: ready
owners: "agents"
created: 2026-05-01
updated: 2026-05-02
stories:
  - "ST-26-08"
tags: ["backend", "renderer", "pdf", "klassrumskartan", "sharing"]
dependencies:
  - "PR-0276"
acceptance_criteria:
  - "Given grouping PDFs are generated from the workspace export path, when the first page is rendered to PNG, then the body visually follows the current shared grouping link: large serif title, `Skapad`, two-column group cards, low-ink circular numbered member markers, restrained strong borders, and A4 portrait sizing."
  - "Given grouping PDFs are generated from the shared-link download path, when compared to the workspace grouping PDF proof, then both paths use the same print-owned grouping renderer behavior and do not fork into separate visual implementations."
  - "Given seating PDFs are generated from the workspace export path, when the first page is rendered to PNG, then the body visually follows the current shared seating link: spatial classroom map, low-ink wall and bench fixtures, larger circular seats, centered labels, no floor tile grid, A3 landscape sizing, and classroom content using as much printable area as possible."
  - "Given seating PDFs are generated from the shared-link download path, when compared to the workspace seating PDF proof, then both paths use the same print-owned seating renderer behavior and do not fork into separate visual implementations."
  - "Given a shared-link PDF download is requested, when the renderer is invoked, then it continues to reconstruct from immutable `presentation_payload` and delegate through export-owned print contracts rather than responsive browser HTML."
  - "Given the redesigned PDFs are rendered, when their first-page PNGs are inspected, then the visible Klassrumskartan/Skriptoteket logo remains present and the compact print header does not consume excessive page space."
  - "Given PDF output is produced, when text extraction or visual inspection is performed, then PDFs do not contain share-page action chrome such as `Ladda ner PDF` controls or public-app attribution links."
  - "Given renderer tests run, when hostile display names or long labels are present, then escaping, label containment, and no-script/no-browser-printing assumptions remain covered."
---

## Problem

The newly improved shared-link renders now set the product visual direction for
Klassrumskartan presentation artifacts, but the actual downloaded PDFs still
use older print layouts. The current code already protects the important
contract boundary: shared-link PDF downloads render from immutable
`presentation_payload` through export-owned renderers, not by printing the
responsive share page. The remaining gap is visual parity and proof across all
four teacher-facing PDF paths:

- workspace seating `Exportera PDF`
- workspace grouping `Exportera PDF`
- shared-link seating `Ladda ner PDF`
- shared-link grouping `Ladda ner PDF`

## Goal

Redesign the print-owned PDF renderers so the PDF bodies inherit from the
approved share-page visual language while keeping PDF headers compact,
print-native, branded, and free of web-only action chrome.

## Non-goals

- No export payload schema changes.
- No share-token, slug, revocation, expiry, owner, public-read, or guest helper
  semantics changes.
- No responsive browser HTML, JavaScript, screenshots, or browser-page printing
  as the PDF source.
- No replacement of the simplified PDF header with the full share-page web
  header.
- No web-only controls, download actions, or attribution links inside the PDF.
- No new external conversion service boundary for Klassrumskartan-owned PDFs.
- Shared-link HTML renders may receive the same non-print-only spatial cleanup
  where it preserves the approved shared-link direction; PDF-only ink-saving
  fill removal does not apply to shared-link fills.

## Decision Checkpoints

1. **Refactor existing export PDF renderers to adopt share-link visual language
   directly.**
   - Pros: Smallest structural change; keeps current renderer ownership easy to
     review.
   - Cons: Risks copying share visual rules into multiple print renderers and
     letting workspace/share paths drift again.

2. **Extract shared print-scene/card primitives used by both export PDF and
   share PDF paths.** Recommended if the implementation can stay small.
   - Pros: Matches the current contract: shared-link PDFs already delegate to
     export-owned print renderers, and common print helpers can keep workspace
     and share downloads visually aligned.
   - Cons: Needs restraint so a visual cleanup does not become a broad renderer
     framework.

3. **Keep export renderers separate but add strict parity tests and visual
   proof.**
   - Pros: Lowest abstraction risk.
   - Cons: Accepts duplicated visual implementations and relies on tests/proof
     to catch future drift.

Recommended path: choose option 2 if extraction is limited to obvious
print-owned card/scene/header helpers. Fall back to option 1 if extraction
creates churn or pushes modules toward broad abstractions. Avoid option 3 unless
the code proves sharing primitives would be more disruptive than useful.

## Implementation Plan

1. Inspect and preserve the current PDF source-of-truth chain:
   `share_pdf_renderer.py` must keep reconstructing `PreparedSeatingExportContract`
   or `GroupingExportPresentation` from immutable `presentation_payload`, then
   delegate into export-owned print renderers.
2. For grouping, redesign the A4 portrait PDF body in
   `grouping_pdf_renderer.py` and its view-model support so it visually follows
   `share_group_renderer.py`: serif hierarchy, `Skapad`, two-column cards,
   member-count labels, circular numbered markers, and restrained dark borders.
3. For seating, redesign the A3 landscape poster body in `poster_renderer.py`
   so the print scene borrows from `share_scene_renderer.py`: wall fixtures,
   benches, larger circular seats, centered labels, no floor tile grid, and
   maximal printable classroom area.
4. Keep `seating_pdf_renderer.py` as the local conversion boundary unless the
   implementation exposes a narrow, renderer-owned helper that both workspace
   and share downloads can use without changing protocols.
5. If helper extraction is chosen, keep helpers print-owned and narrow, for
   example shared card/marker/header/scene style functions under the
   classroom-planner renderer package; do not make share HTML the dependency of
   PDFs.
6. Extend renderer tests to prove workspace and share PDF paths call the same
   print renderers and preserve A4/A3 media contracts.
7. Add or document a real artifact proof that generates all four PDFs and
   first-page PNG renders, preferably under `.artifacts/pr-0278-print-pdf-redesign/`.
8. Update `ST-26-08`, `PR-0278`, `.codex/handoff.md`, and any review evidence
   with exact proof commands and artifact paths before closeout.

Shared-link alignment add-on: mirror the accepted seating spatial cleanup in
`share_scene_renderer.py` by removing the floor tile grid, removing the door
opening half-circle decoration, suppressing repeated bench labels, and making
seat tokens slightly larger/closer to benches. Preserve the existing filled
teacher-desk treatment and grouping ordinal fills in the shared-link renders.

## Likely Code Entry Points

- `src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/grouping_pdf_renderer.py`
- `src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/poster_renderer.py`
- `src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/seating_pdf_renderer.py`
- `src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/share_pdf_renderer.py`
- `src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/share_group_renderer.py`
- `src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/share_scene_renderer.py`
- `src/skriptoteket/application/curated_apps/classroom_planner/exports/grouping_pdf_view_model.py`
- `src/skriptoteket/application/curated_apps/classroom_planner/handlers/grouping_export_jobs.py`
- `src/skriptoteket/application/curated_apps/classroom_planner/handlers/seating_export_jobs.py`
- `tests/unit/infrastructure/curated_apps/apps/classroom_planner/test_grouping_pdf_renderer.py`
- `tests/unit/infrastructure/curated_apps/apps/classroom_planner/test_seating_pdf_renderer.py`
- `tests/unit/infrastructure/curated_apps/apps/classroom_planner/test_share_pdf_renderer.py`

## Test Plan

Required automated gates:

```bash
pdm run pytest -q tests/unit/infrastructure/curated_apps/apps/classroom_planner/test_grouping_pdf_renderer.py tests/unit/infrastructure/curated_apps/apps/classroom_planner/test_seating_pdf_renderer.py tests/unit/infrastructure/curated_apps/apps/classroom_planner/test_share_pdf_renderer.py
pdm run lint
pdm run typecheck
pdm run docs-validate
git diff --check
```

Required real artifact proof:

- Generate one grouping PDF from the workspace export path.
- Generate one seating PDF from the workspace export path.
- Generate one grouping PDF from the shared-link download path.
- Generate one seating PDF from the shared-link download path.
- Render first-page PNGs for all four PDFs, using Poppler/`pdftoppm` when
  available.
- Record page count and media box for all four PDFs.
- Inspect rendered PNGs for logo visibility, compact header height, no
  share-page action chrome, occupied content area, no clipped labels, and no
  overlap.
- For seating, assert A3 landscape, visible wall fixtures, benches, seats, and
  centered labels with the classroom using the printable area. Print proof must
  show no floor tile grid, no door-opening half-circle decoration, and low-ink
  teacher desk and bench treatments. Bench fixture labels should be omitted as
  visual noise while other room labels remain visible.
- For grouping, assert A4 portrait, two-column cards, numbered member markers,
  restrained strong borders, readable member names, and low-ink ordinal
  markers without reversed dark fills.

## Implementation Evidence

Current implementation proof command:

```bash
PYTHONPATH=src:. pdm run python -m scripts.prove_pr_0278_print_pdf_redesign
```

Latest real-data proof run:

- Proof JSON:
  `.artifacts/pr-0278-print-pdf-redesign/runs/20260501T231045193140Z/proof.json`
- Workspace seating PNG:
  `.artifacts/pr-0278-print-pdf-redesign/runs/20260501T231045193140Z/workspace-seating.png`
- Workspace grouping PNG:
  `.artifacts/pr-0278-print-pdf-redesign/runs/20260501T231045193140Z/workspace-grouping.png`
- Shared-link seating PNG:
  `.artifacts/pr-0278-print-pdf-redesign/runs/20260501T231045193140Z/share-seating.png`
- Shared-link grouping PNG:
  `.artifacts/pr-0278-print-pdf-redesign/runs/20260501T231045193140Z/share-grouping.png`
- Shared-link seating HTML screenshot:
  `.artifacts/pr-0278-print-pdf-redesign/runs/20260501T231045193140Z/share-page-seating.png`
- Shared-link grouping HTML screenshot:
  `.artifacts/pr-0278-print-pdf-redesign/runs/20260501T231045193140Z/share-page-grouping.png`

The proof run uses canonical SA24D/G20 real data with 31 students, 31 seating
tokens, 13 normalized fixtures, 8 groups, and 31 group members. It writes a
fresh immutable run directory for every proof execution and records
`png_rendered_from_pdf_sha256` so each rendered PNG is tied to the exact PDF
bytes used by Poppler. The latest run reports A3 landscape seating media boxes,
A4 portrait grouping media boxes, one page for all four artifacts, no
`Ladda ner PDF` action chrome in extracted text, no extracted `BÄNK` bench
labels, 128 px by 128 px rendered seat components in the sampled occupancy
checks, and identical first-page PNG hashes for workspace versus shared-link
output in both seating and grouping. It also writes browser-rendered PNG proof
for the immutable shared-link HTML pages and records no floor grid CSS, no
door-swing CSS, no bench labels, and preserved shared-link fill treatments.

## Stop Conditions

Stop and ask before implementation if:

- The redesign would require changing export payload schemas.
- Workspace PDF and shared-link PDF paths cannot share renderer behavior
  without breaking current persistence or renderer contracts.
- A real PDF render proof cannot be produced locally.
- The new task would require changing share-token, revocation, expiry, owner,
  public-read, or guest-helper semantics.
- The implementation would need JavaScript, screenshotting, responsive
  browser-page printing, or public share HTML as the core PDF source.

## Rollback Plan

Restore the previous print renderer CSS/markup while preserving the existing
workspace export job and shared-link PDF routes. No data migration or share
artifact mutation should be required.
