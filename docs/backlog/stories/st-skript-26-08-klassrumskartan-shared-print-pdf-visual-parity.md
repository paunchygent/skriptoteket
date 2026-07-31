---
type: story
id: ST-SKRIPT-26-08
title: Klassrumskartan shared print PDF visual parity
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
epic: EPIC-SKRIPT-26
acceptance_criteria:
- Given a teacher exports seating from the authenticated workspace, when the PDF is
  generated, then the A3 landscape artifact visually inherits from the approved shared
  seating render while remaining a print-native, low-ink PDF.
- Given a teacher exports grouping from the authenticated workspace, when the PDF
  is generated, then the A4 portrait artifact visually inherits from the approved
  shared grouping render while remaining a print-native, low-ink PDF.
- Given a seating or grouping share link is active, when `Ladda ner PDF` is used,
  then the downloaded PDF uses the same print-owned renderer behavior as the corresponding
  workspace export path.
- Given a share-link PDF is rendered, when the artifact is loaded, then it renders
  from immutable `presentation_payload` and never from responsive browser HTML, JavaScript,
  screenshots, or page-printing.
- Given the PDF body adopts the share-page visual language, when rendered PNG proof
  is inspected, then the compact PDF header still shows visible Klassrumskartan/Skriptoteket
  branding and does not include share-page action chrome.
retired_ids:
- ST-26-08
---

## Context


`PR-0276` made share links feel like real published artifacts: grouping pages
use large serif titles, clean card grids, restrained borders, and circular
member markers; seating pages use a spatial classroom map with wall fixtures,
benches, seats, and centered student labels. The PDF download paths still need
to catch up.

This story exists because the redesign crosses older workspace PDF exports
(`Exportera PDF`) and the newer share-link `Ladda ner PDF` action. It should
not be buried as another `PR-0276` afterthought: `PR-0276` is closed and its
review is approved, while this work changes the print artifacts teachers
download from both authenticated workspace and immutable share-link contexts.

## Epic Contract Slice

No separate epic contract slice is stated in the source.

## ADR Coverage

No separate adr coverage is stated in the source.

## Contract Inputs

No separate contract inputs is stated in the source.

## Live Verification Plan

No separate live verification plan is stated in the source.

## Non-Goals

No separate non-goals is stated in the source.

## Notes


- Grouping PDFs should keep `A4` portrait and adopt the shared grouping
  language: large serif title, `Skapad`, clean two-column group cards, numbered
  member markers without reversed dark fills, and strong but restrained
  borders.
- Seating PDFs should keep `A3` landscape and adopt the shared seating language:
  spatial classroom map, low-ink wall fixtures and benches, larger circular
  seats, centered labels, no floor tile grid, no repeated bench labels, and a
  classroom that uses as much printable area as possible.
- Workspace `Exportera PDF` and shared-link `Ladda ner PDF` must share the same
  print-owned renderer contracts instead of drifting into two visual
  implementations.
- Shared-link PDF must continue to render from immutable `presentation_payload`.
- Do not use JavaScript, screenshots, browser-page printing, or responsive
  public share HTML as the core PDF implementation.
- Keep PDF headers simplified, compact, and low-clutter. Preserve the visible
  logo/branding already present in the PDF renderers.
- Keep `Skapad: YYYY-MM-DD` or equivalent creation metadata only where it fits
  the simplified print header.
- Do not include share-page action chrome such as `Ladda ner PDF` buttons or
  attribution links inside the PDFs.
- Shared-link seating renders should receive the same spatial cleanup where it
  improves the approved shared-link body: no floor tile grid, no door-opening
  half-circle decoration, no repeated bench labels, and slightly larger seats
  closer to benches. Keep shared-link fills where they are part of the approved
  web visual language.
- Real PDF proof is required for workspace seating, workspace grouping,
  shared-link seating, and shared-link grouping downloads: page count, media
  box, first-page rendered PNG inspection, occupied content/layout checks, logo
  visibility, and header-size sanity.

### Source: Visual Direction


Use these approved product screenshots as the north star:

- Grouping shared-link render:
  `/Users/olofs_mba/Pictures/Photos Library.photoslibrary/originals/4/463E2773-3625-4030-9F1F-5A01DB0B8EC2.png`
- Seating shared-link render:
  `/Users/olofs_mba/Pictures/Photos Library.photoslibrary/originals/5/5A45790B-C423-44F5-A09E-31F9F67EF614.png`

The target is inheritance, not a web-page print clone. PDFs keep a compact
print-native header, visible Klassrumskartan/Skriptoteket branding, and no web
controls.

## Decision And Assumption Ledger

| source | semantic | carried_forward | Source material is retained in the sections above. | source |

## Plan Document Review

No review evidence is recorded in this migration candidate; the frontmatter gate remains authoritative.

## Story Closeout Review

No review evidence is recorded in this migration candidate; the frontmatter gate remains authoritative.
