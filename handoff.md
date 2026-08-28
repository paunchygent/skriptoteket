## Current

- [EPIC-SKRIPT-39](docs/backlog/epics/epic-skript-39-skriptoteket-owned-exam-conversion.md)
  and [ADR-SKRIPT-0090](docs/decisions/adr-skript-0090-skriptoteket-owned-exam-conversion-boundary-with-sir-convert-generic-extraction.md)
  are approved (`active`/`accepted`) through `agent-planning:user-closure-gate`
  on 2026-08-29: port the exam-conversion domain
  (DigiExam/Word/PDF parsing, authoring IR, answer-key enrichment, Exam.net
  QTI/PDF/DOCX export) into Skriptoteket by incremental strangler, narrowing
  ADR-SKRIPT-0066 so heavy OCR and STT stay in Sir Convert-a-Lot behind a
  generic extraction contract. Prerequisites executing first in
  sir-convert-a-lot: `TASK-SIRCON-REP-0029` (QTI export repair to the
  empirically confirmed Exam.net contract) and `TASK-SIRCON-08-01-07`
  (remote answer-key model profiles with a 5M token/day lease). Planning
  record: sir-convert-a-lot retained session
  `01a048d5-69f7-7394-93dd-8ff91af608cd`.
- [TASK-SKRIPT-REP-0032](docs/backlog/tasks/task-skript-rep-0032-adopt-shared-hemma-workload-switching-for-skriptoteket-production-services.md)
  has a verified option-A implementation for importable production web/worker
  workload declarations and adapters plus the separate required cleanup gate.
  Hule `TASK-HULE-09-02-26` retains the closed host registry, controller,
  target/conflict selection, and exact-subset restoration proof. The task stays
  `in_progress` with closeout not started until a real overseer owns that
  authority transition.
- [TASK-SKRIPT-REP-0026](docs/backlog/tasks/task-skript-rep-0026-st-28-04-make-hemma-cleanup-units-idle-safe.md)
  is independently verified and done. Its tracked wrapper, two hourly cleanup
  pairs, and bounded installer are published and installed on Hemma. Both
  timers remain enabled and active; stopped-app runs report explicit idle
  success, running-app runs complete successfully, and invalid selectors remain
  visible systemd failures. The task unblocks Task 0032 without changing it.
- Skriptoteket consumes immutable `repository-governance` 0.11.25 at revision
  `1548765abc4f81e54cbe13f6112163da96fa8842` for the shared Hemma workload
  declaration and terminal-outcome contract.
- [TASK-SKRIPT-REP-0030](docs/backlog/tasks/task-skript-rep-0030-adopt-the-repository-governance-binding-durability-repair.md)
  and [TASK-SKRIPT-REP-0031](docs/backlog/tasks/task-skript-rep-0031-adopt-the-repository-governance-live-authority-resolution-repair.md)
  are canceled and superseded by that cutover; their earlier release facts
  remain in the task records.
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

- Task 0032 pinned the corrected provider release, exported exact
  `skriptoteket-web` and `skriptoteket-worker` declarations with bounded
  `sudo -n` Docker adapters, and kept cleanup outside `WorkloadAdapter` so only
  literal `succeeded` advances the required product gate. No Hemma mutation or
  Hule-owned transaction proof was performed.
- Task 0026 replaced direct timer `docker exec` calls with one exact-container
  wrapper, retained the two existing schedules, proved all five installed bytes,
  and passed stopped, running, controlled-failure, and HuleEdu hostwide checks.
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

- Session Date: 2026-08-28
- Last Refreshed: 2026-08-28
- Current docs validate with `pdm run docs-validate`.
- Historical terminal docs audit separately with
  `pdm run python -m scripts.historical_docs.validate_historical_docs`.
- The quality manifest is a routing table for existing repository commands; it
  does not model product architecture or replace local producers.
- Product, Docker, deployment, database, auth, worker, and observability
  commands remain outside Task 0004.
- The frontend catalog is dependency coordination and quality control, not a
  second product architecture model.
