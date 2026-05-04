---
type: pr
id: PR-0291
title: "ST-29-12: symbol inventory and visual index artifact"
status: done
owners: "agents"
created: 2026-05-04
updated: 2026-05-04
stories:
  - "ST-29-12"
tags: ["frontend", "docs", "mockup", "design-system", "icons", "klassrumskartan"]
dependencies:
  - "EPIC-29"
  - "REF-symbol-semantics-inventory-and-decision-contract-2026-05-04"
acceptance_criteria:
  - "Given a designer or implementer opens the mockup HTML, when they inspect it, then they can see the current wrapper inventory, the seed semantic map, and the complete local Lucide component inventory."
  - "Given a symbol is currently used for more than one semantic concept, when the artifact is reviewed, then the drift is visible in the seed semantic map."
  - "Given the artifact depends on local Lucide availability, when it is generated, then it records the package/version basis and does not rely on memory."
  - "Given HuleEdu classroom/education semantics need broader research, when the artifact is reviewed, then it links to an Iconify-backed Lucide Lab and Tabler fallback board without approving a new runtime dependency."
---

## Problem

Klassrumskartan and adjacent SPA surfaces have accumulated icon drift. Some
symbols are doing double work, such as link symbols standing for both actual
share links and rule proximity. Decisions are currently made from individual
screens rather than from a complete visual inventory.

## Goal

Create the complete visual reasoning artifact for `ST-29-12`.

The artifact must include:

- all current shared icon wrappers and their Lucide/custom source
- all direct Lucide imports in Klassrumskartan and adjacent shared UI surfaces
- the complete local Lucide inventory available from the installed package
- a seed semantic map showing current use, unresolved candidates, and drift
- an Iconify research board for Lucide Lab and Tabler fallback candidates across
  HuleEdu semantic families

## Non-goals

- Choosing the final icon set.
- Changing runtime UI symbols.
- Adding new icon packages.
- Replacing Lucide with a different source.

## Implementation Plan

1. Regenerate or replace
   `docs/mockups/st-29-12-symbol-inventory/index.html` from the local installed
   Lucide package and current frontend wrapper/import usage.
2. Ensure the mockup README and this PR link to the canonical reference.
3. Add notes in the artifact for known drift:
   - actual links/share/export
   - keep-near relationship rules
   - near-teacher rules
   - groups and seating mode symbols
   - file type versus download action symbols
4. Keep the artifact usable as a product/design review surface without turning
   it into production UI.
5. Generate the fallback research board through Iconify search/SVG endpoints so
   `PR-0292` can compare Lucide Lab and Tabler candidates for education,
   classroom, organization, student, assignment, assessment, and writing
   semantics.

## Test Plan

- `pdm run docs-validate`
- `git diff --check`

## Rollback Plan

Remove the mockup bundle and this PR doc if the story is re-cut into a different
design-system lane.

## Implementation Summary

This slice is complete.

- Added a bundle-local generator at
  `docs/mockups/st-29-12-symbol-inventory/generate-symbol-inventory.mjs`.
- Added a bundle-local Iconify research generator at
  `docs/mockups/st-29-12-symbol-inventory/generate-huleedu-iconify-research.mjs`.
- Regenerated `docs/mockups/st-29-12-symbol-inventory/index.html` from the
  installed `lucide-vue-next@0.563.0` CJS bundle and current SPA source tree.
- Generated
  `docs/mockups/st-29-12-symbol-inventory/huleedu-iconify-research.html` as a
  research-only comparison board for `lucide-lab` and `tabler` candidates
  across 17 HuleEdu semantic families, including proximity/short-distance
  semantics for keep-near and related rule-language decisions.
- The HTML now includes the seed semantic map, a rendered custom-SVG wrapper
  strip, high-value candidate icon strip, all current shared wrappers, all
  current direct `lucide-vue-next` imports in the SPA, and the complete local
  Lucide component inventory.
- The custom wrappers `IconAdjustments`, `IconFitView`, `IconMinus`,
  `IconZoomIn`, and `IconZoomOut` are visually rendered so they can be compared
  against Lucide or compatible EdTech-oriented add-on-library candidates.
- The known drift around actual share links versus proximity/keep-near rules is
  visible before PR-0292 makes semantic decisions.

## Verification

- `node docs/mockups/st-29-12-symbol-inventory/generate-symbol-inventory.mjs`
  generated `index.html` with 1668 Lucide components, 31 wrappers, and 33 direct
  imports.
- `node docs/mockups/st-29-12-symbol-inventory/generate-huleedu-iconify-research.mjs`
  generated the HuleEdu Iconify fallback board for 17 semantic families.
- `pdm run handoff-validate`
- `pdm run docs-validate`
- `git diff --check`
