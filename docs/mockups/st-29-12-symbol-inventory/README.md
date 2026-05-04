---
type: mockup
id: MOCK-st-29-12-symbol-inventory
title: "ST-29-12 symbol inventory and semantic mapping"
status: proposed
owners: "agents"
created: 2026-05-04
updated: 2026-05-04
tags: ["ST-29-12", "klassrumskartan", "design-system", "icons", "lucide"]
summary: "Reasoning artifact for auditing current icon semantics, current shared wrappers, and the full local Lucide symbol inventory before canonical symbol decisions are implemented."
canonical_preview: "index.html"
submission_policy: "Use this bundle as an inventory and decision surface. The HTML index is not production UI; regenerate it with the bundle-local generator when local Lucide or wrapper usage changes."
winner_policy: "The approved semantic mapping should be captured in the linked reference doc before runtime icon changes begin."
---

# ST-29-12 Symbol Inventory

## Purpose

This bundle gives product/design/implementation work one concrete place to
compare current Skriptoteket icon wrappers, current semantic assignments, and
the full locally installed Lucide inventory.

## Assets

- [Symbol inventory HTML](index.html)
- [HuleEdu Iconify semantic fallback board](huleedu-iconify-research.html)
- Generator: `generate-symbol-inventory.mjs`
- Iconify fallback-board generator: `generate-huleedu-iconify-research.mjs`

Regenerate from the repository root with:

```bash
node docs/mockups/st-29-12-symbol-inventory/generate-symbol-inventory.mjs
node docs/mockups/st-29-12-symbol-inventory/generate-huleedu-iconify-research.mjs
```

## Direction

- Treat the HTML as an inventory board, not as a decision record.
- Keep the installed package/version basis visible in the HTML; runtime truth
  comes from the local `lucide-vue-next` package, not from memory.
- Keep all current custom SVG wrappers visually rendered in the index; filenames
  alone are not sufficient for replacement decisions.
- Keep actual share/link semantics separate from relationship/proximity rule
  semantics.
- Decide global actions first, then Klassrumskartan domain semantics, then
  other site-specific semantics.
- Route approved runtime usage through canonical wrappers or a small semantic
  registry instead of direct feature-local Lucide imports.
- Use Iconify only as a research/indexing layer for fallback discovery across
  Lucide Lab and Tabler. Do not treat the generated fallback board as a runtime
  dependency decision.
