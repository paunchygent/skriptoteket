## Current

- [ST-SKRIPT-38-01](docs/backlog/stories/st-skript-38-01-adopt-the-shared-governed-development-system.md)
  and `EPIC-SKRIPT-38` are verified and done. The shared governed-development
  cutover is complete.
- [TASK-SKRIPT-REP-0006](docs/backlog/tasks/task-skript-rep-0006-st-38-01-cut-over-governed-development-operations.md)
  is independently approved and done. Its topology-derived typed checks cover
  governance, scripts, web, and frontend without an unscoped aggregate.
- [TASK-SKRIPT-REP-0003](docs/backlog/tasks/task-skript-rep-0003-migrate-current-governed-corpus.md)
  is done. Current governed documents use the shared contract, while 764
  terminal records remain historical and byte-identical.
- [TASK-SKRIPT-REP-0004](docs/backlog/tasks/task-skript-rep-0004-st-38-01-adopt-topology-derived-quality.md)
  is done. Schema-v3 facts now route existing backend and frontend
  producers through named scopes and complete current validators.
- [TASK-SKRIPT-REP-0005](docs/backlog/tasks/task-skript-rep-0005-st-38-01-adopt-the-integrated-frontend-catalog.md)
  is done. The app now consumes the shared 17-entry catalog and three central
  resource metadata files without replacing product resources.

## Recent

- Task 0006 adopted the approved immutable shared runtime, preserved local
  producers, corrected active routing to root `handoff.md`, and passed current
  and historical document validation, read-only Hemma transport, and
  deterministic staleness proof.
- Task 0005 synchronized only the reserved catalog block, adopted all 17 shared
  dependency references, and produced a bounded PNPM lock closure.
- Frozen PNPM installation, frontend typecheck, five focused UI primitive
  tests, and the production build pass.
- The shared resource manifest, schema, and package metadata match central
  authority byte-for-byte; Skriptoteket CSS and components remain unchanged.
- Task 0004 inspected the complete, backend, and frontend plans before running
  only the two approved named checks.
- Backend typecheck is clean for `src` and `tests`; frontend typecheck is clean.
- The named runs exposed existing backend and frontend test failures. Focused
  classification proved they are pre-existing product/test readiness debt.
- The targeted pre-commit pytest helper now routes through the existing
  native-library-aware `test-parallel` producer.

## Facts

- Session Date: 2026-07-31
- Last Refreshed: 2026-07-31
- Current docs validate with `pdm run docs-validate`.
- Historical terminal docs audit separately with
  `pdm run python -m scripts.historical_docs.validate_historical_docs`.
- The quality manifest is a routing table for existing repository commands; it
  does not model product architecture or replace local producers.
- Product, Docker, deployment, database, auth, worker, and observability
  commands remain outside Task 0004.
- The frontend catalog is dependency coordination and quality control, not a
  second product architecture model.
