---
type: epic
id: EPIC-06
title: "Quality and test coverage"
status: active
owners: "agents"
created: 2025-12-16
outcome: "Automated tests provide high confidence in critical flows; overall coverage >80% and high-risk modules exceed >80%."
---

## Scope

- Raise automated test coverage to meet the targets in `.agent/rules/070-testing-standards.md`.
- Add focused **integration tests** for repository behavior (CRUD, ordering, not-found paths).
- Add **web middleware** tests for HTML vs JSON error responses.
- Add **behavior tests** for seeded script-bank tools to prevent regressions.

## Stories

- ST-06-01: Improve test coverage for Admin Scripting and Docker Runner
- ST-06-02: Improve test coverage for PostgreSQL repositories (ToolRun + suggestions + tools)
- ST-06-03: Add test coverage for error handling middleware (HTML + JSON)
- ST-06-04: Add unit tests for script bank tools (IST guardian email extractor)
- ST-06-05: Improve test coverage for remaining web page routers (admin tools, scripting runs, suggestions)
- ST-06-06: Test warnings hygiene (TemplateResponse deprecation + dependency warning filtering)
- ST-06-07: Integrate toast notifications into admin workflows (completes ST-05-06)
- ST-06-08: Fix script editor UI issues (file input, CodeMirror scroll)
- ST-06-09: Playwright test isolation: prevent source code pollution
- ST-06-10: Context-Rule linter architecture foundation
- ST-06-11: Editor quick fixes (CodeMirror diagnostic actions)
- ST-06-12: Lint panel and keyboard navigation
- ST-06-13: Lint gutter filtering and diagnostics polish
- ST-06-14: Headless linter rule test harness

## Notes

- Prefer protocol-mocked unit tests for application/domain code; use testcontainers only where behavior requires a real DB.
- Keep tests deterministic; avoid time-based flakiness and fragile HTML assertions.
