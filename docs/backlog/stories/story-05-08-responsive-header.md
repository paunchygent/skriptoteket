---
type: story
id: ST-05-08
title: "Responsive header with mobile navigation"
status: ready
owners: "agents"
created: 2025-12-18
epic: "EPIC-05"
acceptance_criteria:
  - "Given viewport width <768px, when page loads, then hamburger button is visible and desktop nav links are not visible"
  - "Given hamburger button, when activated, then a mobile nav dropdown panel is shown and the button toggles aria-expanded true/false"
  - "Given hamburger button, when rendered, then it has aria-controls pointing at the mobile nav panel element"
  - "Given mobile nav open, when a navigation link is activated, then navigation occurs and the menu is closed by the subsequent page swap/reload"
  - "Given viewport width ≥768px, when page loads, then full nav links are visible (no hamburger)"
  - "Given any viewport, when header renders, then brand logo and logout button remain accessible"
  - "Given keyboard navigation, when tabbing to the hamburger button, then focus is visible and the menu can be toggled via Enter/Space"
---

## Context

The current header uses `flex-wrap: nowrap` which causes navigation links to overflow horizontally on narrow screens. Users on mobile/tablet cannot access navigation.

## Tasks

- [ ] Create `.huleedu-hamburger` button component (CSS + minimal JS toggle)
- [ ] Add `@media (max-width: 767px)` rules to hide `.huleedu-header-nav` and show hamburger
- [ ] Create `.huleedu-mobile-nav` dropdown panel for mobile navigation
- [ ] Add JS event handler for hamburger toggle (~20 LOC in `app.js`) that updates `aria-expanded`
- [ ] Update `base.html` with hamburger markup (hidden on desktop)
- [ ] Test on 320px, 375px, 768px viewports

## Files to Modify

```text
src/skriptoteket/web/static/css/huleedu-design-tokens.css  # Breakpoint tokens
src/skriptoteket/web/static/css/app/layout.css             # Header responsive rules
src/skriptoteket/web/static/css/app/components.css         # Hamburger + mobile nav styles
src/skriptoteket/web/static/js/app.js                      # Toggle handler
src/skriptoteket/web/templates/base.html                   # Hamburger markup
```

## Notes

- Keep hamburger simple: three-line icon using CSS (no icon library)
- Mobile nav can reuse existing `.huleedu-header-nav a` styles
- `aria-expanded` and `aria-controls` are required for accessibility
