## Current

- [TASK-SKRIPT-39-01-02](docs/backlog/tasks/task-skript-39-01-02-preserve-decimal-scores-and-replace-missing-digiexam-images-with-visible-placeholders.md)
  is implemented and locally proven with both unchanged teacher files. It
  preserves fractional scores and repairs missing titles/images without extra
  provider work or invalid QTI resources. Exam.net acceptance remains with the user.
- [TASK-SKRIPT-39-01-03](docs/backlog/tasks/task-skript-39-01-03-degrade-unknown-digiexam-question-types-to-reviewable-free-text.md)
  remains unopened until Task 02 is published.
- Production code merge `fab9412a` serves the corrected Exam Converter review flow.
  The canonical Hemma checkout follows published `main` and contains that merge;
  Skriptoteket web/worker are healthy, and public `/healthz` returns 200. The deploy applied
  migrations and passed the seating-export readiness gate. Reserved Sir GPU and
  STT containers remain exited and were not restarted. The user retains the
  production `.dxe` acceptance; agents did not submit a production conversion.
- Exam Converter uses PostgreSQL/UoW as the public-job authority and has no
  web-process queue. Teacher review persists one or all valid AI suggestions
  through the correction-session UoW, waits for durable reprojection, and advances directly
  through unresolved questions. The corrected review UI has neutral equal `Granska` /
  `Godkänn alla` actions, separate `Förslag` and `Saknar facit` states, exact-row navigation,
  local `Avbryt`, and no exposed gap identifiers. Desktop keeps one fixed-height detail frame with stationary
  `Översikt | Godkänn/Spara | Ändra/Avbryt` slots and no duplicate footer; phone uses its
  distinct natural-height composition with contained top and bottom actions.
- The mixed-DigiExam backend repair and frontend review-projection follow-up are
  integrated on `main` and deployed on Hemma. The real authenticated local
  browser journey used unchanged `1776888013-ak7-lag-och-ratt.dxe` and crossed
  upload, actual worker/provider completion, 390 px and 1440 px layouts, local
  cancel with zero writes, individual acceptance/advance, atomic bulk
  acceptance, four manual gaps, durable replay/reprojection, and QTI/PDF
  downloads with zero browser errors. The real PostgreSQL vertical, 1,264
  frontend tests, lint, typecheck, production build, and binary source-hash
  checks are green. The user owns the
  production mobile `.dxe` acceptance; agents did not submit a production file.
  Production state confirms the failed-job replay fix: failed row
  `29b8b86f-0edb-47ac-9899-7523893504a3` relinquished its deterministic key when
  failed row `b4a6f79d-a329-4af9-9426-78a2bd69a746` was admitted, so the next
  retry creates a fresh job instead of replaying either historical failure.
- [TASK-SKRIPT-39-03-02](docs/backlog/tasks/task-skript-39-03-02-cut-over-the-public-exam-converter-to-skriptoteket-owned-execution.md)
  is `done` under the user-directed no-further-review closeout. Canonical Hemma
  main `8fe6b722` serves the declared public deep link directly and completed
  anonymous local job `1a6dc301-d63e-40e7-b335-b71e75d44fb9` from a genuine
  unmodified MCQ `.dxe`. The public result preserved warnings, manual
  follow-ups, readiness, and named downloads; all available artifact sizes and
  hashes matched. Bounded logs contained zero Sir exam-conversion calls and
  zero provider calls. Both production consumers have now moved, so Task 03
  Sir exam cleanup and then Task 04 Qwen cleanup are next.
- [TASK-SKRIPT-39-03-01](docs/backlog/tasks/task-skript-39-03-01-cut-over-the-authenticated-exam-converter-to-skriptoteket-owned-execution.md)
  is `done` under the existing independent approval. Canonical Hemma main
  `098f5100` runs migration `c8e4f2a6d9b1`, the native `in_process` lane, and
  durable answer-key provider configuration in web and worker. Authenticated
  HuleEdu job `8b8c837d-4bdf-4996-b652-6c6ebc0b20d1` completed from a genuine
  unmodified MCQ `.dxe` through Luna, teacher review/replay, local PDF download,
  and Mina filer save with zero Sir exam-conversion requests. The temporary
  live Compose override was removed.
- [ST-SKRIPT-39-02](docs/backlog/stories/st-skript-39-02-port-the-remote-answer-key-completion-line-with-a-daily-token-lease.md)
  is `done` and independently `VERIFIED` with no material findings. Both tasks
  are `done`, independently approved, implemented on main through `6f4baa7a`
  (`7b32ed60` plus the reviewed mixed-exam port repair), live-proven through
  the authenticated HuleEdu browser-session ceremony, and terminally published.
  Both task worktrees and local-only branches are retired. Verifier record:
  `.orchestration/context/sessions/01a04d62-c71c-721c-a43a-76384e182429/evidence/reviews/ST-SKRIPT-39-02/terminal-spec-verification.md`.
  [TASK-SKRIPT-39-02-01](docs/backlog/tasks/task-skript-39-02-01-stand-up-the-in-process-answer-key-completion-vertical-with-the-luna-profile-and-postgres-lease.md)
  live proof on reviewed commit `847fae31`: unchanged real `.dxe` `a274a9d9…`,
  conversion `882f4d81-9eea-44ce-8d63-e1ac65e5af03`, enrichment
  `f390fea4-10ae-4009-ab58-e4d3edb613c4`, six `gpt-5.6-luna` low-effort
  completions, six reconciled non-refundable lease rows, overlay
  `9c46587e-853f-4784-b175-3c19bbe2738e`, eleven preserved manual-marking
  items, passed QTI and successful bundle (`8faa7722…`). Captures `0022`-`0028`.
  [TASK-SKRIPT-39-02-02](docs/backlog/tasks/task-skript-39-02-02-prove-failover-exhaustion-fail-close-and-operator-lease-status-for-the-answer-key-lane.md)
  live proofs on local main `6f4baa7a`: unchanged real `.dxe` `9eb02293…`;
  forced failover job `c2d233bd-0d2e-4115-8775-14f6ba1d90af` made two Luna
  request failures followed by two real GLM-5.3-flash completions, four lease
  rows, GLM overlay `1bb8be60-d71c-4132-960c-aa8d0f007d29`, and passed QTI.
  Forced exhaustion job `bb9817ba-f367-440b-bbb1-467a6f26a3c3` at limit `1`
  returned typed `daily_token_lease_exhausted` before any provider call, added
  zero leases/overlays, and the authenticated admin status returned HTTP 200
  with the day balance/reset. Captures `0032`-`0038`; ordinary configuration
  is restored and web/worker are healthy.
- [TASK-SKRIPT-39-01-01](docs/backlog/tasks/task-skript-39-01-01-prove-the-in-process-dxe-to-exam-net-bundle-walking-skeleton.md)
  has an implemented, independently reviewed walking skeleton (branch
  `codex/task-skript-39-01-01`): the exam-conversion domain chain
  ported from sir-convert-a-lot `41be61a6` under
  `src/skriptoteket/domain/curated_apps/exam_conversion/`, QTI writer /
  WeasyPrint / artifact-store seams under
  `infrastructure/curated_apps/apps/conversion_hub/`, the operator lane switch
  `EXAM_CONVERTER_CONVERSION_LANE` (default `sir_convert`), and the
  authenticated route `POST /api/v1/apps/documents.conversion_hub/exam-converter/conversions`
  served through the existing job-status and artifact-download surface via a
  `local-exam:` producer id. Parity proof: the in-process QTI package and
  Exam.net PDF are byte-identical to the Sir Convert reference outputs for
  fixture `1772718003-test-samma-prov-i-digiexam.dxe` with a deterministic
  teacher overlay (QTI sha256
  `f36a4ae342a4a734a9f8126b694101517a46b7b3751d1b19ece72484a5328698`, empty
  accepted-difference list). Verification 2026-08-29: 96 new/ported tests green
  (`pdm run pytest tests/unit/domain/curated_apps/exam_conversion tests/unit/application/curated_apps/test_exam_conversion_parity.py tests/unit/application/curated_apps/handlers/test_conversion_hub_jobs.py tests/unit/web/exam_converter -q`), `pdm run lint` green, `pdm run typecheck`
  at the pre-existing 10-error `script_bank` baseline, full `tests/unit`
  failure set identical to the clean tree. The task is `done`; integrated
  merge `704d7fe7` is published. Independent review 2026-08-29: the reviewer
  regenerated the Sir Convert reference from `41be61a6` and reproduced byte
  equality for the QTI package and the PDF, confirmed the full validator set
  and all named Exam.net contract obligations, requested two changes (both
  resolved: the volatile `CHECKPOINT.md` state map excluded from the merge;
  uploads read through the shared `read_upload_files` size caps), and
  approved the resolutions on re-review. Live check 2026-08-29: the
  authenticated HuleEdu browser-session ceremony proof is recorded — with the
  local shared-auth lane (HuleEdu `auth-integration` Gateway :8080 + login UI
  :5174, `auth-integration check` all ok) and the Docker-backed Skriptoteket
  lane from main `704d7fe7` under `EXAM_CONVERTER_CONVERSION_LANE=in_process`,
  `scripts/_playwright_auth.py::login_via_auth_entry` as `superuser@local.dev`
  followed by an in-context CSRF-headered POST to the new conversions route
  with the fixture and deterministic teacher overlay produced job
  `e3be5d9c-b7be-4e7a-9dbc-d7e5dd9aebcb` (`succeeded`); the bundle downloaded
  through the existing `/jobs/{id}/artifact` route contains `qti-package.zip`
  byte-identical to the parity reference (sha256 `f36a4ae3…`), the Exam.net
  PDF, and a passed `qti-validation-report.json`, and the Gateway log confirms
  both calls were proxied to `skriptoteket-web:8000`. The container-rendered
  PDF hash differs from the macOS seat as the documented WeasyPrint font-stack
  dependence predicts; the committed structural PDF assertion covers this.
  The `.dxe` fixtures are byte-exact and excluded from the pre-commit
  end-of-file/whitespace fixers after the fixer mutated them once at
  integration. The task worktree is retired (branch deleted after the merge);
  the live-check docker lanes (HuleEdu auth-integration, Skriptoteket
  web/db/frontend from main) are left running per user decision.
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
  is independently verified and done. Its published option-A implementation
  provides importable production web/worker workload declarations and adapters
  plus the separate required cleanup gate. Hule `TASK-HULE-09-02-26` retains
  the closed host registry, controller, target/conflict selection, and
  exact-subset restoration proof.
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

## Facts

- Session Date: 2026-08-31
- Last Refreshed: 2026-08-31
- Current docs validate with `pdm run docs-validate`.
- Historical terminal docs audit separately with `pdm run python -m scripts.historical_docs.validate_historical_docs`.
- The quality manifest is a routing table for existing repository commands; it
  does not model product architecture or replace local producers.
- Product, Docker, deployment, database, auth, worker, and observability
  commands remain outside Task 0004.
- The frontend catalog is dependency coordination and quality control, not a
  second product architecture model.
