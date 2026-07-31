---
type: reference
id: REF-SKRIPT-MOCKUP-st-29-11-share-export-affordance-consolidation
title: ST-29-11 share/export affordance consolidation
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
reference_kind: mockup
summary: ST-29-11 share/export affordance consolidation
---

## Intent
### Purpose
Retain the approved visual direction for consolidating the split
`Exportera`/`Dela` toolbar affordances in Klassrumskartan `Grupper` and
`Sittplatser`.
### Direction
- The workspace toolbar exposes one `Dela` affordance for outward distribution.
- The opened panel is titled `Dela och exportera`.
- Link actions stay grouped under `Länk` with `Skapa länk`, active links,
  `Kopiera`, and `Återkalla`.
- File actions stay grouped under `Filer`.
- `Grupper` offers `Excel (.xlsx)` as `Standard` and `PDF (A4 stående)`.
- `Sittplatser` offers `Affisch (A3)` as `Standard`, `Affisch (A4)`, and
  `Excel (.xlsx)`.
- The refactor keeps share and export orchestration separate underneath the
  combined surface.

## Package Manifest
### Assets
- [Share/export affordance mockup](share-export-affordance-mockup.png)
- [Overview scope selector alternatives](share-export-scope-selector-alternatives-2026-05-05.png)

## Design Interpretation
The source record did not define a separate section for this package heading.

## Runtime And Proof Boundary
The source record did not define a separate section for this package heading.

## Governing Links And Follow-Up
### Preferred Follow-up Direction
For the overview workspace `Dela och exportera` selector, product-owner review
on 2026-05-05 selected the third alternative from the scope-selector mockup:

- use a compact rail/toolbar toggle for `Gruppindelning` and `Sittschema`
- keep the selector visually familiar with other Klassrumskartan rail controls
- show a selected-draft confirmation summary below the rail
- include both class-list and classroom context in that confirmation, for
  example `SA24D · G20`
- keep `Länk` and `Filer` column behavior unchanged

This direction is governed by
[PR-0301](../../backlog/prs/pr-0301-st-29-11-overview-share-export-scope-rail-and-draft-confirmation.md).
