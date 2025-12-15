---
type: story
id: ST-05-01
title: "CSS foundation and base template"
status: done
owners: "agents"
created: 2025-12-15
epic: "EPIC-05"
acceptance_criteria:
  - "Given the app loads, when viewing any page, then canvas background and IBM Plex fonts are visible (Verified)"
  - "Given the viewport is >= 768px, when viewing the page, then ledger frame border is visible with margin (Verified)"
  - "Given the app loads, when inspecting CSS, then HuleEdu design tokens are available as custom properties (Verified)"
---

## Context

Foundation work for harmonizing the frontend with the HuleEdu design system.

## Tasks

- Add HuleEdu design tokens to `static/css/huleedu-design-tokens.css` (Done)
- Create `static/css/app.css` with application extensions (Done)
- Update `base.html`: Google Fonts, CSS link, ledger frame, toast container, grid background (Done)
- Configure `hx-boost` for SPA-like navigation (Done)
