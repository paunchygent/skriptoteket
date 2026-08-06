# Skriptoteket Platform Discovery Overview

As of 2026-08-03; authored from repository state on that date. Counts and lane
names below are bound to that date. Every rule this document names is stated in
full by the authority it links to; read the authority before acting on a
boundary.

## 1. What This Repository Is

Skriptoteket is a teacher-first Script Hub: one deployable product that lets
teachers run curated scripts and purpose-built applications against their own
classroom data. It is a single FastAPI application over PostgreSQL with a Vue 3
/ Vite SPA, not a service fan-out. HuleEdu owns the shared browser-session login
and identity context; Skriptoteket keeps roles and authorization local. Target
Python is 3.13-3.14 (`requires-python = ">=3.13,<3.15"`), managed with PDM.

Top-level layout:

| Path             | Holds                                                          |
| ---------------- | -------------------------------------------------------------- |
| `AGENTS.md`      | Repository route list and command policy; the boot router      |
| `CLAUDE.md`      | Narrow Claude specialist file (UI/design review, Swedish copy) |
| `handoff.md`     | Volatile current-state pointers, kept under 200 lines          |
| `src/`           | The `skriptoteket` application package (all backend layers)    |
| `frontend/`      | pnpm workspace holding the SPA                                 |
| `runner/`        | Helper modules injected into the sandboxed script runtime      |
| `migrations/`    | Alembic environment and 84 versioned migrations                |
| `tests/`         | Backend unit, integration, and fixture suites                  |
| `scripts/`       | Repository-local proof and browser-automation entry points     |
| `observability/` | Grafana, Loki, Prometheus, and Promtail stack configuration    |
| `docs/`          | Governed docs-as-code surface plus generated indexes           |
| `data/`          | Sample and reference inputs for scripts and curated apps       |
| `stakeholders/`  | Non-governed material written for people outside the repo      |
| `.codex/`        | Repo-local agent lane: rules, agents, skills, long-term memory |
| `.github/`       | CI workflows                                                   |

Deploy and local surfaces are compose files at the root: `compose.yaml`,
`compose.dev.yaml`, `compose.prod.yaml`, `compose.runner.yaml`, and
`compose.observability.yaml`, with `Dockerfile` for the application and
`Dockerfile.runner` for the script sandbox.

Working lanes excluded from version control include `.artifacts/`,
`.orchestration/`, and `.codex/repomix_packages/`.

## 2. `src/skriptoteket/` — Backend Layers

The backend follows a DDD/Clean layering. Dependency direction runs inward:
`web` and `workers` depend on `application`, `application` depends on `domain`
and on `protocols`, and `infrastructure` implements `protocols`. Nothing in
`domain` imports outward.

| Layer             | Holds                                                                                                                                 |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `domain/`         | Entities, value objects, and `errors.py`; subpackages `catalog`, `curated_apps`, `favorites`, `identity`, `scripting`, `suggestions`  |
| `protocols/`      | The protocol surface every adapter implements — the seam between application and infrastructure                                       |
| `application/`    | Use cases per capability: `catalog`, `curated_apps`, `editor`, `favorites`, `identity`, `scripting`, `suggestions`                    |
| `infrastructure/` | Adapters: `db`, `repositories`, `runner`, `llm`, `documents`, `email`, `security`, `vault`, `artifacts`, `file_refs`, `session_files` |
| `web/`            | FastAPI surface: `app.py`, `router.py`, `api/v1/`, `routes/`, `auth/`, `middleware/`, `error_mapping.py`, `spa_fallback` and `static` |
| `workers/`        | The execution queue worker and its job database binding                                                                               |
| `di/`             | Dishka provider wiring, one module per capability                                                                                     |
| `cli/`            | Operator CLI (`main.py`, `commands/`, `_db.py`)                                                                                       |
| `script_bank/`    | Seeded catalog entries and their tool-input contracts, plus the shipped script sources under `scripts/`                               |
| `observability/`  | Structured logging, metrics, tracing, redaction, health, and auth-outcome instrumentation                                             |
| `config.py`       | Settings                                                                                                                              |

Unit of Work owns commit and rollback; repositories never commit. `DomainError`
maps to HTTP only at the web boundary. Both rules and the file-tree detail are
stated by `.codex/skills/skriptoteket-backend-dev/SKILL.md`.

## 3. Curated Apps

Curated apps are first-class application modules with bespoke UX and
app-specific APIs, not scripts. Each one spans `domain/curated_apps/`,
`application/curated_apps/`, `di/`, and a dedicated `web/api/v1/apps_*.py`
router, with public (unauthenticated share) surfaces in `public_apps*.py`.

Current apps: Classroom Planner (rosters, seating, grouping, smart rules,
shares, exports, guest upgrade), Conversion Hub (document converter, transcript
saves and exports, exam-converter correction sessions), Reagent Prep Chef, and
Flunk-Out Frenzy. Flunk-Out Frenzy playfield geometry has its own authority in
`.codex/skills/pinball-board-authoring/SKILL.md`.

Conversion work delegates to Sir Convert-a-Lot across the trust lane; the client
contract lives in `application/curated_apps/sir_convert_contracts.py` and the
shared `sir-convert-a-lot-client` skill.

## 4. Script Execution And The Runner

User-authored tools run in a Docker sandbox, never in the application process.
`infrastructure/runner/` owns the sandbox: `docker_runner.py`, the `docker/`
image lane, `contracts/`, capacity limiting, path safety, artifact management,
retention, run-input storage, and session promotion. Queued execution runs
through `workers/execution_queue/` (processor, execution, heartbeat,
normalization, formatting).

`runner/` at the repository root is the other half: the helper modules mounted
into the sandbox and importable by tool scripts — `pdf_helper` (WeasyPrint HTML
to PDF), `tool_errors` (`ToolUserError` for user-facing messages),
`skriptoteket_toolkit`, and `_runner.py`. Its README is written in Swedish for
teacher-developers.

## 5. `frontend/` — SPA Workspace

A pnpm workspace (`apps/*`, `packages/*`) that currently ships one application,
`apps/skriptoteket`: Vue 3.5, Vite, TypeScript, Pinia, Vue Router, Tailwind CSS
v4, Vitest. Its `src/` carries `api`, `components`, `composables`,
`design-system`, `router`, `stores`, `styles`, `types`, `utils`, and `views`.
`openapi.json` plus `pdm run openapi-export-v1` and `fe-gen-api-types` keep
client types generated from the backend contract rather than hand-written.

Shared dependency versions are pinned in the `pnpm-workspace.yaml` catalog
between the `repository-governance:frontend-catalog` markers; those lines are
machine-owned. Stack doctrine is the shared `integrated-frontend-stack` skill
and its Skriptoteket reference.

## 6. `docs/` — Governed Docs Surface

`docs/index.md` is the doorway. Lanes: `backlog/` (`epics`, `stories`, `tasks`,
`prs`, `reviews`, `sprints`, plus a generated `INDEX.md`), `adr/` and
`decisions/`, `prd/`, `reference/` (140 documents), `runbooks/`, `guides/`,
`mockups/`, `releases/`, `research/`, `templates/`, and `_meta/`.

Domain-scoped depth maps already live in `docs/reference/` and stay there:

- [Frontend design-system codemap — `docs/reference/ref-skript-plan-frontend-design-system-codemap-spa-planner-editor-frontend-design-system-codemap-spa-planner-editor.md`](../../../../docs/reference/ref-skript-plan-frontend-design-system-codemap-spa-planner-editor-frontend-design-system-codemap-spa-planner-editor.md)
- [Tool editor framework codemap — `docs/reference/ref-skript-general-tool-editor-framework-codemap-current-vs-target-tool-editor-framework-codemap-current-vs-target.md`](../../../../docs/reference/ref-skript-general-tool-editor-framework-codemap-current-vs-target-tool-editor-framework-codemap-current-vs-target.md)
- [Runner/tool code modularization map — `docs/reference/ref-skript-general-runner-tool-code-modularization-map-shared-libs-multi-file-bundles-runner-tool-code-modularization-map-shared-libs-multi-file-bundles.md`](../../../../docs/reference/ref-skript-general-runner-tool-code-modularization-map-shared-libs-multi-file-bundles-runner-tool-code-modularization-map-shared-libs-multi-file-bundles.md)
- [Exam Converter reviewed AI-facit contract map — `docs/reference/ref-exam-converter-reviewed-ai-facit-contract-map-pr-0331.md`](../../../../docs/reference/ref-exam-converter-reviewed-ai-facit-contract-map-pr-0331.md)

The Exam Converter map is retained historical evidence and is marked
deprecated in its own frontmatter. This overview links these maps at their
exact repository-relative paths; it does not replace them.
`docs/templates/template-codemap.md` remains the authoring template for that
family.

Generated indexes are refreshed by `pdm run docs-sync` and enforced by
`pdm run docs-validate`; both scan `docs/` only, so `AGENTS.md` and `.codex/`
sit outside them. Scaffold governed documents with the package-owned
`pdm run new-task`, `new-story`, `new-epic`, `new-review`, `new-doc`; never
author frontmatter by hand. `docs/_meta/docs-contract.yaml` is the historical
legacy contract — the package-owned contract is the current authority. Local
paths and governance facts are in the shared `agent-docs-governance`
Skriptoteket reference.

## 7. Ownership Boundaries

- `.codex/skills/` is the repo-local skill lane. It holds skills that describe
  this repository only and are never promoted into the shared skill hub. Shared
  skills are authored in the canonical skill repository and reached through the
  harness alias; repo facts belong in a shared skill's Skriptoteket reference,
  not in a copied local skill.
- `.claude/skills` is a symlink to `.codex/skills`, so the Claude harness
  discovers this lane at session start. The sanctioned symlink direction is
  local skill source into a harness configuration folder; installing shared-skill
  shims into this repository stays forbidden.
- Identity is split: HuleEdu owns the browser-session login ceremony,
  Skriptoteket owns local roles and authorization. Authenticated browser proof
  must use the HuleEdu ceremony and the repo helpers, never direct
  credential POSTs or local cookie shortcuts.
- Skriptoteket shares Hemma infrastructure with HuleEdu through
  `shared-postgres` and shared edge surfaces; host policy is the shared
  `hemma-devops` skill.

## 8. Validation Surfaces

`pdm run format`, `lint`, `typecheck`, `test`, and `check` for Python;
`fe-type-check`, `fe-lint`, `fe-build`, and the Vitest lanes for the SPA;
`docs-sync` and `docs-validate` for the `docs/` contract; `skills-validate` for
`.codex/skills/`; `handoff-validate` for `handoff.md`; `check-md` and
`format-md` for changed markdown. `AGENTS.md` states which set a given change
closes on; `local-devops` and its Skriptoteket reference carry the local
development and command-wrapper detail.
