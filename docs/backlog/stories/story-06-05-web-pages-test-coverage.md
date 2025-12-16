---
type: story
id: ST-06-05
title: "Improve test coverage for remaining web page routers (admin tools, scripting runs, suggestions)"
status: ready
owners: "agents"
created: 2025-12-16
epic: "EPIC-06"
acceptance_criteria:
  - "`admin_tools.py` and `admin_scripting_runs.py` exceed >70% coverage."
  - "`suggestions.py` exceeds >70% coverage."
  - "Coverage improvements come from behavior-focused tests (no implementation patching)."
  - "All tests pass without regressions."
---

## Context

Coverage reports show several web page routers are still below the router coverage target (>70%) in
`.agent/rules/070-testing-standards.md`:

- `src/skriptoteket/web/pages/admin_tools.py`
- `src/skriptoteket/web/pages/admin_scripting_runs.py`
- `src/skriptoteket/web/pages/suggestions.py`

These routes are core to admin and contributor workflows.

## Plan

1. Add targeted unit tests that call the route functions with protocol-mocked dependencies.
2. Prefer asserting on response type/status/redirect headers and key template context fields.
3. Add a small number of integration tests only where real DB behavior is essential.

