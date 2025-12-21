---
type: story
id: ST-11-02
title: "UI library + design tokens (pure CSS)"
status: ready
owners: "agents"
created: 2025-12-21
epic: "EPIC-11"
acceptance_criteria:
  - "Given the SPA imports the UI library, when rendering the app shell, then global tokens and core layout primitives match the existing HuleEdu styling"
  - "Given Storybook is run for the UI package, when viewing core primitives, then components render with token-driven styles without Tailwind"
ui_impact: "Provides reusable layout/form primitives for the SPA, preserving the HuleEdu design language."
dependencies: ["ADR-0017", "ADR-0029"]
---

## Context

The SPA should not re-implement styling ad hoc. A small UI library with token-based CSS gives consistent primitives for
all views.
