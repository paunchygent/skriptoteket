---
id: "070-testing-standards"
type: "quality"
created: 2025-12-13
updated: 2026-01-22
scope: "all"
---

# 070: Testing Standards (pytest + protocols + DI)

## 1. Test organization (current)

```text
tests/
├── unit/
│   ├── application/
│   ├── domain/
│   ├── infrastructure/
│   ├── web/
│   ├── workers/
│   └── observability/
├── integration/
│   ├── cli/
│   ├── infrastructure/
│   └── web/
├── fixtures/
└── conftest.py
```

## 2. Conftest stays minimal (REQUIRED)

- Keep `tests/conftest.py` as a small re-export surface.
- Put fixtures and helpers in explicit modules under `tests/fixtures/`.

Example fixtures in this repo:

- `tests/fixtures/identity_fixtures.py`
- `tests/fixtures/database_fixtures.py`

## 3. Mock protocols, not implementations (REQUIRED)

- Use `AsyncMock(spec=SomeProtocol)` to keep tests behavior-focused.
- Avoid `@patch` and implementation-detail mocks; prefer DI seams.

## 4. Markers and default test selection

By default, tests exclude `docker`, `slow`, `financial`, and `simulation` (see `pyproject.toml`).

Common commands:

- Default suite: `pdm run test`
- Parallel: `pdm run test-parallel`
- Simulation suites: `pdm run test-simulations`
- Docker-marked tests (override default marker filter):
  - `pytest -m docker --override-ini addopts=''`

Use `simulation` for expensive statistical proof suites such as repeated classroom-layout runs.
Keep quick geometry/unit smoke checks unmarked so they still run in the normal commit path.

## 5. Frontend tests

- Vitest: `pdm run fe-test`
- Playwright proofs: `pdm run pr-0253-auth-retirement --start-backend --start-vite` / `pdm run pr-0255-auth-bootstrap --start-backend --start-vite`
