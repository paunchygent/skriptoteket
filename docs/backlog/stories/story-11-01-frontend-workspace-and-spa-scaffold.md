---
type: story
id: ST-11-01
title: "Frontend workspace + SPA scaffold"
status: done
owners: "agents"
created: 2025-12-21
epic: "EPIC-11"
acceptance_criteria:
  - "Given the repo is set up, when running the frontend install and quality scripts, then the SPA and UI package build, lint, and typecheck successfully with Tailwind 4 + HuleEdu design tokens configured"
  - "Given a developer runs the SPA dev command, when opening the app, then a basic routed shell renders and can navigate between placeholder routes"
ui_impact: "Introduces the new SPA app structure and replaces the islands-only frontend layout."
dependencies: ["ADR-0027", "ADR-0029"]
---

## Context

We need a first-class SPA workspace (pnpm) to replace the islands toolchain and support a full Vue application.

## Notes

- Keep the workspace structure aligned with the roadmap: `frontend/apps/skriptoteket` + `frontend/packages/huleedu-ui`.
- Enforce strict TypeScript + linting from day one to avoid drift during migration.
