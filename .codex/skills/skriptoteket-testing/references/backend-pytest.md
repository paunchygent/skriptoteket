# Backend Pytest

Use this reference for Skriptoteket backend unit, integration, API, domain, and
application tests.

## Read First

- `.codex/rules/070-testing-standards.md`
- `docs/runbooks/runbook-testing.md`
- `.codex/skills/skriptoteket-backend-dev/SKILL.md`
- Relevant architecture rules from `.codex/rules/000-rule-index.md`, usually
  `020`, `040`, `042`, `048`, and `053`.

## Rules

- Domain and application unit tests should mock `typing.Protocol` boundaries
  with `AsyncMock(spec=...)`.
- Avoid `@patch` when constructor injection, Dishka DI, or an explicit protocol
  fixture can express the seam.
- API tests assert HTTP status, response contract, error code, correlation, and
  authorization behavior. Business rules belong below the router.
- Repository/UoW tests may use integration lanes; repositories never commit and
  UoW owns transaction behavior.
- Keep fixtures named by domain purpose. Shared fixtures live under
  `tests/fixtures/`, not as hidden behavior in `tests/conftest.py`.

## Commands

Use the command map in `docs/runbooks/runbook-testing.md` and `AGENTS.md`.
Prefer focused pytest targets while iterating, then the backend close-out gates
required for the touched layer.
