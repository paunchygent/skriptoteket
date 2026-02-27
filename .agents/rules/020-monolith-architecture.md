---
id: "020-monolith-architecture"
type: "architecture"
created: 2025-12-13
updated: 2026-01-22
scope: "all"
---

# 020: Monolith Layer Architecture (Skriptoteket)

Skriptoteket is a **FastAPI monolith** with a **Vue 3 + Vite SPA** frontend. The backend serves:

- `/api/v1/*` JSON APIs (OpenAPI is the contract; TS types are generated from it)
- `/static/*` assets (including the built SPA)
- SPA history fallback (serves `index.html` for client-side routes)

Legacy SSR/Jinja/HTMX is **removed** (ADR-0027).

## 1. Repository shape

```text
src/
└── skriptoteket/                 # The only Python package (src-layout)
    ├── config.py                 # Pydantic Settings
    ├── di/                       # Dishka container assembly (composition root)
    ├── protocols/                # typing.Protocol boundaries (by domain)
    ├── domain/                   # Pure domain rules (no web/db/framework imports)
    ├── application/              # Use-cases (handlers orchestrate protocols + UoW)
    ├── infrastructure/           # Protocol implementations (DB/repos/runner/llm/etc.)
    ├── workers/                  # Background loops (e.g. execution queue worker)
    ├── observability/            # logging/metrics/tracing helpers
    └── web/                      # FastAPI app + routers + middleware + static + SPA fallback

runner/                           # Runner image entrypoint/runtime (tool containers)
frontend/                         # pnpm workspace (SPA + component lib)
docs/                             # Docs-as-code (PRDs/ADRs/backlog/runbooks/releases)
tests/                            # pytest (unit + integration) + fixtures
```

## 2. Layer boundaries (REQUIRED)

### Web layer (`src/skriptoteket/web/`)

- **Responsibilities**: routing, auth/CSRF deps, request validation, response shaping, error mapping, SPA hosting.
- **Must stay thin**: no business rules; call application handlers via protocols.
- **SPA hosting**:
  - Static: `src/skriptoteket/web/static/`
  - SPA build output: `src/skriptoteket/web/static/spa/`
  - History fallback: `src/skriptoteket/web/routes/spa_fallback.py` (MUST be registered last).

### Application layer (`src/skriptoteket/application/`)

- **Responsibilities**: orchestrate use-cases (commands/queries), coordinate protocols + Unit of Work, enforce
  cross-entity invariants that are not purely local to one domain object.
- **No framework coupling**: no FastAPI types or routers.

### Domain layer (`src/skriptoteket/domain/`)

- **Pure**: no FastAPI, SQLAlchemy, Docker SDK, network IO, or environment reads.
- **Errors**: raise `DomainError` (no HTTP).

### Protocols (`src/skriptoteket/protocols/`)

- **Contract boundary**: depend on `typing.Protocol`, not concrete implementations.
- **Placement**: protocols are organized by domain (not a single `protocols.py` file).

### Infrastructure (`src/skriptoteket/infrastructure/`)

- **Implements protocols**: repositories, DB models, runner integration, LLM providers, etc.
- **Transactions**: repositories never commit; Unit of Work owns commit/rollback.

### Workers (`src/skriptoteket/workers/`)

- Background processes (e.g. execution queue worker loop per ADR-0062).
- Must use the same application/infrastructure layers (no ad-hoc DB access patterns).

## 3. Dependency direction (REQUIRED)

```text
web/ ───────▶ application/ ───────▶ domain/
 │                 │                 ▲
 │                 └──── depends ────┘
 │
 └──────────▶ protocols/ ◀────────── infrastructure/
                    ▲
                    └──────── workers/
```

Rule of thumb:

- `domain` is pure.
- `web` is thin.
- `infrastructure` is where IO lives.
- `protocols` are the seams.
