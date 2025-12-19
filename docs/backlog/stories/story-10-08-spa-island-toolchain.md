---
type: story
id: ST-10-08
title: "Frontend toolchain for SPA islands (Vue/Vite/Tailwind)"
status: ready
owners: "agents"
created: 2025-12-19
epic: "EPIC-10"
acceptance_criteria:
  - "Given the repo is set up, when pnpm install and pnpm build are run, then Vite emits hashed SPA assets and a manifest that the app can reference from templates"
  - "Given production mode, when a SPA island page is rendered, then the template includes the correct hashed asset URLs via the Vite manifest"
  - "Given development mode, when iterating on SPA code, then changes can be tested without rebuilding the Python app on every edit (either dev server proxy or watch build)"
ui_impact: "Introduces the approved SPA island stack (Vue/Vite/Tailwind) for editor/runtime surfaces only."
dependencies: ["ADR-0025"]
---

## Context

To keep SPA islands aligned with HuleEdu, we need a first-class frontend toolchain in the repo. This must coexist with
the existing SSR/HTMX app without turning the entire site into a SPA.
