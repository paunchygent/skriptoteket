---
type: story
id: ST-29-01
title: "Klassrumskartan — Canonical operation symbols and planner control primitives"
status: done
owners: "agents"
created: 2026-03-28
updated: 2026-04-01
epic: "EPIC-29"
dependencies:
  - "EPIC-24"
  - "EPIC-27"
acceptance_criteria:
  - "Given the planner renders repeated operations, when the symbol-system slice ships, then undo, redo, history, settings/rules, shuffle, add/create, close, export/download, zoom, fit, and overflow each use one canonical symbol across overview, grouping, seating, and rules."
  - "Given a planner action is frequent and industry-obvious, when the new control primitives render it, then the action may be icon-only or icon-led instead of occupying a long text button."
  - "Given an icon-only or icon-led planner control renders, when the shared control system ships, then the control exposes an accessible name through visible text or `aria-label` and also provides a discoverability aid such as a tooltip, hover label, or nearby microcopy."
  - "Given a planner action is ambiguous, app-specific, destructive, or high commitment, when the slice ships, then text remains visible or is paired with the symbol rather than being hidden behind iconography alone."
  - "Given the planner control primitives are introduced, when later redesign stories or other tool-grade Skriptoteket apps implement the same operations, then they reuse shared design-system affordance components instead of inventing per-app glyph/button treatments."
  - "Given dense planner controls render through the shared primitive family, when the slice ships, then standalone buttons no longer mix square and slightly rounded corner treatments arbitrarily and instead use one harmonized hard small-radius (`4px`) shape language, with grouped controls keeping that radius only on the outer edges."
ui_impact: "Yes (shared planner controls, affordances, iconography)"
data_impact: "No"
---

## Context

This story now represents the shipped foundation layer for the later EPIC-29 workspace work. The
control-language freeze, frontend codemap, shared dense-tool primitives, and first canonical symbol
assets are now present in the repo and underpin the current desktop-first Klassrumskartan shell.

## Notes

- This story is about a reusable control system, not about final workspace composition.
- The primary planning output for this story is a shared cross-app control-language contract, not a
  planner-only icon pass.
- Implementation should start from the `V1 freeze` section in `REF-shared-tool-control-language-v1`
  before consulting the longer worked topologies.
- Use the workspace doctrine and design-system rule as the planning baseline.
- `PR-0156` and `PR-0157` are now the canonical shipped slices for this story: the repo has the
  design-system codemap, explicit primitive planning sequence, shared dense-tool primitives, and
  canonical symbol assets that later EPIC-29 slices already consume in practice.
- The original `PR-0158` seating-first proving-ground plan is canceled as stale planning. The
  remaining follow-on work is no longer "finish ST-29-01 in seating" and is now tracked explicitly
  as broader post-core tightening in `ST-29-11`, `ST-29-12`, and the later tooltip enhancement
  story `ST-29-08`.

## Planned PR slices

- [PR-0156: ST-29-01 control-language freeze, primitive contract, and frontend codemap](../prs/pr-0156-st-29-01-control-language-freeze-primitive-contract-and-fe-codemap.md) — `done`
- [PR-0157: ST-29-01 shared dense-tool primitives and canonical symbol assets](../prs/pr-0157-st-29-01-shared-dense-tool-primitives-and-canonical-symbol-assets.md) — `done`
- [PR-0158: ST-29-01 seating workspace adoption of shared dense-tool primitives](../prs/pr-0158-st-29-01-seating-workspace-adoption-of-shared-dense-tool-primitives.md) — `canceled`
- Follow-on story: [ST-29-11: Shared site/app dense-control primitive tightening](story-29-11-klassrumskartan-shared-site-and-app-dense-control-primitive-tightening.md)
- Follow-on story: [ST-29-12: Canonical symbol language and discoverability contract completion](story-29-12-klassrumskartan-canonical-symbol-language-and-discoverability-contract-completion.md)

## References

- Epic parent: [EPIC-29](../epics/epic-29-klassrumskartan-desktop-first-workspace-overhaul.md)
- Shared control matrix: [REF-shared-tool-control-language-v1](../../reference/ref-shared-tool-control-language-v1.md)
- Frontend codemap: [REF-frontend-design-system-codemap-2026-03-28](../../reference/ref-frontend-design-system-codemap-2026-03-28.md)
- Workspace doctrine: [REF-klassrumskartan-workspace-ui-doctrine-2026-03-28](../../reference/ref-klassrumskartan-workspace-ui-doctrine-2026-03-28.md)
- Product direction: [REF-group-seating-studio-product-direction-2026-03-21](../../reference/ref-group-seating-studio-product-direction-2026-03-21.md)
- Design-system rule: [045-huleedu-design-system](../../../.agents/rules/045-huleedu-design-system.md)
- Frontend skill: [skriptoteket-frontend-specialist](../../../.claude/skills/skriptoteket-frontend-specialist/SKILL.md)
