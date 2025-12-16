---
type: story
id: ST-06-06
title: "Test warnings hygiene (TemplateResponse deprecation + dependency warning filtering)"
status: done
owners: "lead-dev"
created: 2025-12-16
epic: "EPIC-06"
acceptance_criteria:
  - "Running `pdm run test -- -q` produces zero warnings from Skriptoteket code."
  - "All `templates.TemplateResponse(...)` calls use the new Starlette signature (request-first) to avoid deprecation warnings."
  - "Only unavoidable dependency-internal warnings are filtered, using narrow `filterwarnings` rules in `pyproject.toml`."
  - "A follow-up `pdm run docs-validate` passes."
---

## Context

The current test suite is green, but it prints DeprecationWarnings that hide real regressions. The largest source is
Starlette’s `TemplateResponse` signature change. We should fix our call sites rather than silencing them globally, and
only filter warnings that truly originate in dependencies.

## Scope

- Update `templates.TemplateResponse(...)` call sites in `src/skriptoteket/web/` to use the new signature
  (`TemplateResponse(request=..., name=..., context=...)`).
- Update any code comments/examples that show the old signature.
- Add narrowly-scoped `filterwarnings` entries in `pyproject.toml` only for dependency warnings that cannot be fixed.

## Out of scope

- Large UX redesigns or router refactors.
- Changing third-party library versions to chase warnings.
