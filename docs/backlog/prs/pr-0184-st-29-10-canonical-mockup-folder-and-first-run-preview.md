---
type: pr
id: PR-0184
title: "ST-29-10: canonical mockup folder and first-run preview"
status: done
owners: "agents"
created: 2026-03-31
updated: 2026-04-01
stories:
  - "ST-29-10"
tags: ["frontend", "ux", "klassrumskartan", "mockup", "planning"]
dependencies:
  - "EPIC-29"
acceptance_criteria:
  - "Given Klassrumskartan needs UI planning support, when the mockup slice lands, then the repo has one clear canonical home for story-scoped UI mockups under `docs/mockups/`."
  - "Given `ST-29-10` needs behavior alignment before production code changes, when the mockup is opened, then one self-contained HTML/CSS document demonstrates the intended first-run selector behavior for no-class, class-without-classroom, and class-with-classroom states."
  - "Given the mockup is for alignment only, when this slice ships, then no production frontend component or backend behavior is changed."
  - "Given the mockup file is created, when a local browser proof runs, then the document renders directly and is easy for later developers to find from the canonical mockup path."
---

## Problem

The story now has approved copy and reachability rules, but we still lack a fast, low-friction way
to align on the exact shell behavior before we start touching live planner code.

The repo also does not yet have a clear canonical place for story-scoped UI mockups, which makes
future planning assets harder to discover and easier to scatter.

## Goal

Create one canonical mockup location and one self-contained preview file that shows the intended
`ST-29-10` first-run behavior using the current Klassrumskartan overview shell as the visual
starting point.

## Non-goals

- Changing production Vue components, route-shell logic, or backend behavior.
- Creating a second design system separate from the existing planner surface.
- Building a full prototype app with backend data or reusable production assets.

## Implementation plan

1. Establish `docs/mockups/` as the canonical top-level home for story-scoped UI previews.
2. Create a story-based subfolder for `ST-29-10`.
3. Add one self-contained `index.html` with inline CSS and any tiny local JS needed for state
   switching.
4. Make the mockup demonstrate these three states:
   - no class
   - class without classroom
   - class with classroom
5. Keep the visual language close to the current overview shell so the mockup feels like a real
   implementation rehearsal instead of a detached wireframe.

## Proposed module focus

- `docs/mockups/st-29-10-first-run-workspace-gating/index.html`

## Test plan

- Open the HTML file locally in a browser and verify all three states render.
- `pdm run docs-validate`

## Rollback plan

- Remove the `ST-29-10` mockup folder if the repo later adopts a different canonical mockup home,
  while keeping the story and implementation-slice docs intact.
