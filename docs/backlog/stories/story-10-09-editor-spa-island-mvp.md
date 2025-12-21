---
type: story
id: ST-10-09
title: "Editor SPA island MVP (admin/contributor)"
status: done
owners: "agents"
created: 2025-12-19
epic: "EPIC-10"
acceptance_criteria:
  - "Given an admin/contributor opens the tool editor page, when the page loads, then the SPA island mounts and displays the editor without layout collapse"
  - "Given the user edits script content, when Save is invoked, then the editor persists changes via the backend API and the user sees a success/failure state"
  - "Given the SPA island is present, when navigating the rest of Skriptoteket, then SSR/HTMX pages continue to function (no global take-over)"
ui_impact: "Stabilizes CodeMirror/editor UX and unlocks richer editor-side interactions beyond HTMX."
dependencies: ["ADR-0025", "ST-10-08"]
---

## Context

The admin and contributor editor surfaces are at the complexity boundary for Jinja + HTMX + raw JS, especially around
CodeMirror sizing, state, and richer editor interactions. This story delivers the minimal embedded SPA island that can
grow.
