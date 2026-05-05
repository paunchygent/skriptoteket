---
type: story
id: ST-11-26
title: "HuleEdu palette token refresh and semantic color split"
status: in_progress
owners: "agents"
created: 2026-05-04
updated: 2026-05-04
epic: "EPIC-11"
acceptance_criteria:
  - "Given the shared design-token source, when frontend code consumes HuleEdu colors, then Deep Navy, Warm Terracotta, Verdigris Teal, and light canvas/paper are available as canonical role tokens."
  - "Given action, brand, warning, and critical UI roles, when shared primitives are rendered, then terracotta is not used for warning/destructive semantics and teal is not used for warning/destructive semantics."
  - "Given existing screens still contain legacy burgundy utility usage, when this story lands, then burgundy remains a compatibility/critical channel while new functional action usage moves to Verdigris tokens."
  - "Given shared button, rail, toggle, and segmented-control primitives, when a control is active or selected, then the filled/selected state uses Verdigris Teal instead of structural navy."
  - "Given a selector is rendered as selected on a filled Verdigris surface, when it has nested labels or disabled state, then no navy text class overrides the light selected text color."
  - "Given the light warm canvas background, when body copy or dense workspace text appears, then Deep Navy remains the only new palette color used for long readable text."
  - "Given pages and dense workspaces use the light canvas, when panels, rows, and highlights are composed, then the UI avoids large white-on-canvas patchwork and prefers translucent canvas-toned panel surfaces with lighter row/object highlights."
  - "Given a share/link action is secondary, when it appears beside export or setup controls, then it uses Verdigris outline/text with a link icon instead of filled primary CTA styling or a plus icon."
---

## Context

The first SPA token set collapsed brand accent, primary CTA, selected state, and
destructive/critical decisions into the old burgundy channel. The HuleEdu working
palette now separates those roles:

- Deep Navy `#082B4C`: structural and textual foundation.
- Warm Terracotta `#C94F32`: brand-signature accent only.
- Verdigris Teal `#3F7F78`: functional action, selected state, focus, and calm
  completion/status accent.
- Canvas/Paper `#FAFAF6`: light warm base surface. It should unify the page rather than act as a
  backdrop for stacked white panels; use lighter row/object highlights to create emphasis without a
  blotchy background.

Warning and destructive semantics are not part of the terracotta or teal roles.
Warning remains amber/ochra. Destructive and truly user-critical decisions remain
on the burgundy/error-family channel.

## Notes

- Keep existing greys where applicable.
- Preserve the deprecated `burgundy` compatibility alias for older references, but do not use it for
  new functional action, focus, hover, or brand-accent styling.
- New code should prefer semantic tokens (`action`, `critical`, `terracotta`) over
  the legacy `burgundy` name.
- Avoid broad white panels on canvas by default. Use translucent canvas-toned panel surfaces, borders, spacing,
  and light highlights unless a specific object needs stronger contrast.
