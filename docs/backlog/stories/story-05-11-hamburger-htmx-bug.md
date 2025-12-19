---
type: story
id: ST-05-11
title: "Fix hamburger menu after HTMX navigation"
status: done
owners: "agents"
created: 2025-12-19
epic: "EPIC-05"
acceptance_criteria:
  - "Given a user on mobile viewport (<768px), when they click hamburger and navigate via mobile nav, then hamburger works on subsequent clicks without page reload"
  - "Given multiple HTMX hx-boost navigations, when user clicks hamburger after 3+ navigation cycles, then menu toggles correctly each time"
  - "Given the initialization guard, when app.js re-executes on HTMX swap, then duplicate event listeners are not attached"
---

## Context

The hamburger menu works on first page load but stops working after HTMX `hx-boost` navigation. Users must reload the page to restore hamburger functionality.

## Root Cause

1. `base.html` has `hx-boost="true"` on `<body>` (line 16)
2. HTMX swaps only `<main>` content; the `<header>` (with hamburger) persists in DOM
3. `app.js` re-executes on each navigation (script tag in body is re-evaluated by HTMX)
4. Each execution attaches duplicate event listeners to `document`
5. Multiple listeners fight for control, breaking the hamburger toggle

## Fix

Add initialization guard at top of IIFE in `app.js`:

```javascript
(function () {
  "use strict";

  // Prevent duplicate initialization on HTMX hx-boost navigation
  if (window.__huleeduAppInitialized) return;
  window.__huleeduAppInitialized = true;

  // ... rest unchanged
})();
```

## Tasks

- [x] Create this story file
- [ ] Add initialization guard to `src/skriptoteket/web/static/js/app.js`
- [ ] Verify locally (hamburger works after 3+ nav cycles)
- [ ] Run `pdm run lint`
- [ ] Deploy to production
- [ ] Verify on production

## Files to Modify

```text
src/skriptoteket/web/static/js/app.js  # Add init guard (2 lines)
```

## Notes

- The reverted fix (commit `f413317`) used `htmx:afterSettle` to reinitialize, which was incorrect
- The guard pattern is standard for preventing duplicate initialization in SPAs
- Alternative (hx-select="main") would require testing all HTMX partials, so the guard is simpler
