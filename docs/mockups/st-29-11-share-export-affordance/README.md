---
type: mockup
id: MOCK-st-29-11-share-export-affordance
title: "ST-29-11 share/export affordance consolidation"
status: approved
owners: "agents"
created: 2026-05-03
updated: 2026-05-06
tags: ["ST-29-11", "ST-26-06", "klassrumskartan", "sharing", "export", "mockup"]
summary: "Approved visual direction for folding Klassrumskartan workspace export actions into the Dela affordance."
canonical_preview: "share-export-affordance-mockup.png"
submission_policy: "Use this mockup as qualitative direction for PR-0286; implementation must preserve the hierarchy and stable toolbar affordance, not pixel-match the generated image."
winner_policy: "The original generated PNG remains the PR-0286 consolidation direction; the 2026-05-05 selector alternatives add the product-owner preferred follow-up for PR-0301."
---

# ST-29-11 Share/Export Affordance Consolidation

## Purpose

Retain the approved visual direction for consolidating the split
`Exportera`/`Dela` toolbar affordances in Klassrumskartan `Grupper` and
`Sittplatser`.

## Assets

- [Share/export affordance mockup](share-export-affordance-mockup.png)
- [Overview scope selector alternatives](share-export-scope-selector-alternatives-2026-05-05.png)

## Direction

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

## Preferred Follow-up Direction

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
