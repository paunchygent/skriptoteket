---
type: story
id: ST-11-02
title: "UI library + design tokens (Tailwind 4)"
status: done
owners: "agents"
created: 2025-12-21
epic: "EPIC-11"
acceptance_criteria:
  - "Given the SPA imports the UI library, when rendering the app shell, then global tokens and core layout primitives match the existing HuleEdu styling"
  - "Given the UI package builds, when the SPA renders core primitives, then components render with Tailwind utilities using @theme design tokens"
ui_impact: "Provides reusable layout/form primitives for the SPA, preserving the HuleEdu design language."
dependencies: ["ADR-0017", "ADR-0032"]
---

## Context

The SPA should not re-implement styling ad hoc. A small UI library with token-based CSS gives consistent primitives for
all views.
