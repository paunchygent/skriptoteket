---
type: story
id: ST-05-10
title: "Script editor responsive layout"
status: ready
owners: "agents"
created: 2025-12-18
epic: "EPIC-05"
acceptance_criteria:
  - "Given viewport width ≤1024px, when editor page loads, then layout stacks vertically (single column)"
  - "Given stacked layout, when rendered, then sidebar controls appear above the code editor (not buried below)"
  - "Given stacked layout, when rendered, then sidebar width is 100% and no horizontal scrolling is required"
  - "Given viewport width >1024px, when editor page loads, then layout remains two-column with sidebar on the right"
  - "Given viewport width ≤1024px, when using primary action buttons (Save/Create draft, Publish/Request changes, Testkör), then touch targets are at least 44×44px"
---

## Context

The script editor uses a fixed 320px sidebar column that breaks on narrow screens. When stacked at the 1024px breakpoint, sidebar appears after the main content, burying critical controls (Save, Publish) below the fold.

## Tasks

- [ ] Add breakpoint tokens (`--huleedu-bp-sm`, `--huleedu-bp-md`, `--huleedu-bp-lg`) for documentation consistency (see ADR-0020 note about media queries)
- [ ] Refactor `.huleedu-editor-layout` to reorder sidebar first at `≤1024px` (e.g. `order: -1` on `.huleedu-editor-sidebar`)
- [ ] Ensure stacked layout uses full-width sidebar (no fixed 320px column behavior)
- [ ] Audit editor-page touch targets and adjust padding/min-height where needed for 44×44px (prefer a dedicated mobile/touch variant over global changes)
- [ ] Test editor workflow on 768px and 375px viewports

## Files to Modify

```text
src/skriptoteket/web/static/css/huleedu-design-tokens.css  # Breakpoint tokens
src/skriptoteket/web/static/css/app/editor.css             # Layout responsive rules
src/skriptoteket/web/static/css/app/buttons.css            # Touch target audit
src/skriptoteket/web/templates/admin/script_editor.html    # Possible markup changes for accordion
```

## Design Options

### Option 1: Sidebar First (order swap)

- Simple CSS change: `order: -1` on `.huleedu-editor-sidebar`
- Sidebar controls appear at top of stacked layout
- Code editor scrolls below

### Option 2: Collapsible Accordion

- Sidebar sections become expandable accordions
- More compact; consider `<details>/<summary>` for a no-JS baseline if needed
- Similar pattern to hamburger menu

### Recommendation

Start with Option 1 (order swap) for minimal effort. Consider Option 2 for ST-05-11 if user feedback indicates need for more compact mobile layout.

## Notes

- The 320px fixed sidebar width should become `100%` when stacked
- Consider sticky positioning for Save button on mobile
