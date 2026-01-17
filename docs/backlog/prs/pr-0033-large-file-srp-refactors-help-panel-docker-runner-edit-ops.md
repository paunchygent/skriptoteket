---
type: pr
id: PR-0033
title: "Refactor: reduce >500 LOC hotspots (HelpPanel + HomeView + ScriptEditorView, Docker runner + edit-ops + diff applier)"
status: ready
owners: "agents"
created: 2026-01-16
updated: 2026-01-16
stories: []
tags: ["backend", "frontend", "refactor", "srp", "performance"]
acceptance_criteria:
  - "`frontend/apps/skriptoteket/src/components/help/HelpPanel.vue` is reduced below 500 LOC via SRP refactor AND the help UI is not part of the default initial bundle (lazy-loaded)."
  - "`frontend/apps/skriptoteket/src/views/HomeView.vue` is reduced below 500 LOC via SRP refactor (extract view-model + IO), preserving behavior."
  - "`frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue` is reduced below 500 LOC via SRP refactor (extract page orchestration), preserving behavior."
  - "`src/skriptoteket/infrastructure/runner/docker_runner.py` is reduced below 500 LOC via SRP refactor AND eliminates redundant input normalization/workdir building steps."
  - "`src/skriptoteket/application/editor/edit_ops_handler.py` is reduced below 500 LOC via SRP refactor, keeping protocol-first DI and preserving behavior."
  - "`src/skriptoteket/infrastructure/editor/unified_diff_applier.py` is reduced below 500 LOC via SRP refactor (split normalization/parsing/apply), preserving behavior."
  - "No user-facing behavior changes beyond improved performance/maintainability (same routes, same responses, same UI semantics)."
  - "Minimal verification passes: `pdm run fe-type-check`, `pdm run fe-test`, `pdm run test`."
  - "If any UI/route behavior changes, a live functional check is recorded in `.agent/handoff.md`."
---

## Problem

We have multiple files above the repo’s size budget (>500 LOC). This is a consistent SRP smell and increases:

- Cognitive load and change risk (especially in high-churn areas like editor AI).
- Performance cost where large code is eagerly loaded (SPA entry bundle) or runs on hot paths (tool execution).
- Review difficulty: changes in a “god file” tend to mix responsibilities and hide subtle regressions.

This PR aims to address the highest-impact hotspots and create a prioritized inventory for follow-up work.

## Goal

- Reduce the in-scope hotspots to <500 LOC via cohesive modularization (SRP-compliant, not “extract a helper and move on”).
- Improve performance where it matters:
  - Reduce baseline SPA bundle by lazy-loading the Help UI (and/or its topics).
  - Reduce redundant work in the Docker runner execution path.
- Keep public APIs stable and behavior unchanged (refactor-only).
- Provide a clear, ordered list of remaining >500 LOC files with recommended priority.

## Non-goals

- Feature work (no new UX, no new endpoints, no new runner behavior).
- “Micro-splitting” just to satisfy LOC budgets (avoid creating fragmented modules with unclear ownership).
- Refactoring generated/binary/lock files.

## Implementation plan

## Checklist (MUST be kept up-to-date during implementation)

- [ ] **Scope:** the 6 refactor jobs below are still in scope (or de-scopes are explicitly approved and recorded here).
- [ ] **LOC budget:** each target file is <500 LOC after refactor (record actual LOC next to each item below).
- [ ] **SRP refactor quality:** no “helper-only” slicing; responsibilities are separated into cohesive modules with clear naming and ownership.
- [ ] **API stability:** public exports and DI wiring remain stable (or call-site changes are explicitly listed and justified).
- [ ] **Verification recorded:** exact commands and manual checks are recorded in `.agent/handoff.md`.
- [ ] **Perf confirmation:** for frontend, confirm Help UI is not in the default initial bundle (document how you verified: chunk inspection / bundle report).

### 1) Frontend: Help UI (P0) — lazy-load + SRP split

**Current file:** `frontend/apps/skriptoteket/src/components/help/HelpPanel.vue` (~596 LOC)
**Reason:** Always mounted from `frontend/apps/skriptoteket/src/App.vue` → included in the default initial bundle.

**Target outcome**

- `HelpPanel.vue` becomes a thin orchestrator + shared layout (panel shell + topic switch).
- Content-heavy topics move into dedicated modules/components.
- Help UI (at minimum: the panel itself, ideally also topic content) is lazy-loaded.

**Suggested module layout (example)**

- `frontend/apps/skriptoteket/src/components/help/HelpPanel.vue` (panel shell + async topic loader)
- `frontend/apps/skriptoteket/src/components/help/topics/HelpTopicHome.vue`
- `frontend/apps/skriptoteket/src/components/help/topics/HelpTopicBrowseProfessions.vue`
- `frontend/apps/skriptoteket/src/components/help/topics/HelpTopicAdminEditor.vue`
- `frontend/apps/skriptoteket/src/components/help/helpTopics.ts` (topic registry + lazy import map)

**Steps**

1. Extract each topic’s content into `topics/*` components (keep “dumb” UI components where possible).
2. Replace the `v-if` topic blocks with a single `activeTopic → component` resolver.
3. Lazy-load topic components via `defineAsyncComponent` and a registry map.
4. Optionally (recommended): lazy-load the entire `HelpPanel` from `App.vue` (so the help UI is not in the entry chunk).
   - Keep `useHelp()` state as the stable API; the panel should just subscribe/render.
5. Validate that help still works (open/close, index routing, route sync) and that SSR is not required.

**Files likely to be touched**

- `frontend/apps/skriptoteket/src/components/help/HelpPanel.vue`
- `frontend/apps/skriptoteket/src/components/help/useHelp.ts`
- `frontend/apps/skriptoteket/src/App.vue` (to lazy-load HelpPanel)
- New: `frontend/apps/skriptoteket/src/components/help/helpTopics.ts`
- New: `frontend/apps/skriptoteket/src/components/help/topics/*.vue`

### 2) Frontend: Home dashboard view (P1) — split view-model + IO (behavior-preserving)

**Current file:** `frontend/apps/skriptoteket/src/views/HomeView.vue` (~677 LOC)
**Reason:** High-traffic route; mixes API IO, modal/workflow state, and rendering.

**Target outcome**

- `HomeView.vue` becomes a thin view that composes:
  - A “view-model” composable for dashboard data loading (runs/tools/admin metrics + error handling).
  - A composable (or subcomponent) for the “create draft tool” modal state + submit behavior.
- Prefer reusing existing components (`components/home/*`) and keep the route behavior identical.

**Suggested module layout (example)**

- `frontend/apps/skriptoteket/src/views/HomeView.vue` (thin orchestration + template)
- `frontend/apps/skriptoteket/src/composables/home/useHomeDashboard.ts` (data loading + derived state)
- `frontend/apps/skriptoteket/src/composables/home/useCreateDraftToolModal.ts` (modal state + submit)

**Steps**

1. Extract dashboard data fetching (`/api/v1/my-runs`, `/api/v1/my-tools`, `/api/v1/admin/tools`, favorites, recents) into a composable with explicit loading/error state.
2. Extract “create draft tool” modal state + submission into a composable or a dedicated component.
3. Keep route-level concerns in the view (auth gating + navigation), but move most state machines out.
4. Ensure `HomeView.vue` is <500 LOC and the behavior matches before/after (same API calls, same toasts, same navigation).

**Files likely to be touched**

- `frontend/apps/skriptoteket/src/views/HomeView.vue`
- New: `frontend/apps/skriptoteket/src/composables/home/*` (or equivalent location)
- Potentially: `frontend/apps/skriptoteket/src/components/home/*` (if additional SRP subcomponents are warranted)

### 3) Frontend: Admin Script editor view (P1) — extract page orchestration into a view-model composable

**Current file:** `frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue` (~753 LOC)
**Reason:** Route-level view is doing a lot of orchestration and reactive wiring; high churn and difficult to review.

**Target outcome**

- `ScriptEditorView.vue` becomes a thin view that mostly renders the template and delegates state orchestration to a dedicated composable.
- Preserve existing composable boundaries (many already exist) but reduce the “wiring soup” and watcher clutter.

**Suggested module layout (example)**

- `frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue` (thin view)
- `frontend/apps/skriptoteket/src/composables/editor/useScriptEditorPageState.ts` (wires route/router/auth/layout + existing composables; returns a stable “page state” object)

**Steps**

1. Extract route/role derivations, orchestration logic, and cross-composable wiring into a single composable.
2. Keep “leaf” behavior where it belongs (existing composables), but centralize page-level coordination (watchers, mode toggles).
3. Keep template stable; avoid renaming props/slots in shared components unless needed.
4. Ensure `ScriptEditorView.vue` is <500 LOC and the editor still works end-to-end (required live check).

**Files likely to be touched**

- `frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue`
- New: `frontend/apps/skriptoteket/src/composables/editor/useScriptEditorPageState.ts`
- Possibly: `frontend/apps/skriptoteket/src/components/editor/*` (if a subcomponent extraction is clearly cohesive)

### 4) Backend: Docker runner (P0) — SRP split + remove redundant work

**Current file:** `src/skriptoteket/infrastructure/runner/docker_runner.py` (~628 LOC)
**Reason:** Hot path; mixes Docker client concerns, archive building, contract parsing, output truncation, timeouts, and error mapping.

**Target outcome**

- Keep `DockerToolRunner` and `DockerRunnerLimits` as the public entry point (stable imports for DI and tests).
- Split responsibilities into cohesive modules under a `docker/` subpackage.
- Remove redundant `normalize_input_files()` work (currently performed twice).

**Suggested module layout (example)**

- `src/skriptoteket/infrastructure/runner/docker_runner.py` (thin exports: `DockerRunnerLimits`, `DockerToolRunner`)
- `src/skriptoteket/infrastructure/runner/docker/protocols.py` (Docker Protocols)
- `src/skriptoteket/infrastructure/runner/docker/workdir_archive.py` (build tar once, accept already-normalized inputs)
- `src/skriptoteket/infrastructure/runner/docker/container_io.py` (log/result extraction helpers)
- `src/skriptoteket/infrastructure/runner/docker/errors.py` (DomainError mappings + helpers)
- `src/skriptoteket/infrastructure/runner/docker/runner.py` (orchestrator implementation)

**Steps**

1. Move the Docker Protocols out of `docker_runner.py` to a dedicated module.
2. Refactor `_build_workdir_archive(...)` to accept already-normalized input files (or pre-normalize once and reuse).
3. Extract container IO helpers:
   - “put archive”
   - “fetch result.json”
   - “fetch output archive”
   - “truncate logs”
4. Keep the orchestration flow in a single place (`DockerToolRunner`), but make it mainly “call helpers + glue”.
5. Ensure existing unit tests remain meaningful; update them to import the same public symbols.

**Files likely to be touched**

- `src/skriptoteket/infrastructure/runner/docker_runner.py`
- `src/skriptoteket/di/infrastructure.py`
- `tests/unit/infrastructure/runner/test_docker_runner.py`
- New modules under `src/skriptoteket/infrastructure/runner/docker/`

### 5) Backend: Editor AI edit-ops handler (P0) — SRP split into a small `edit_ops/` package

**Current file:** `src/skriptoteket/application/editor/edit_ops_handler.py` (~918 LOC)
**Reason:** “God handler” mixing:

- UoW + persistence (sessions/turns/messages)
- Budgeting + prompt construction
- Failover routing + retryability rules
- LLM provider execution
- Parse/validation outcomes + user-facing error strings
- Logging + capture-on-error behavior

**Target outcome**

- `EditOpsHandler.handle(...)` remains the public entry point and stays thin.
- Split into cohesive modules with clear boundaries and minimal shared state.
- Preserve protocol-first DI and behavior (no UX/contract changes).

**Suggested module layout (example)**

- `src/skriptoteket/application/editor/edit_ops_handler.py` (thin orchestrator; <500 LOC)
- `src/skriptoteket/application/editor/edit_ops/constants.py` (messages, TTL, small pure constants)
- `src/skriptoteket/application/editor/edit_ops/persistence.py` (UoW ops: create turns/messages, update status)
- `src/skriptoteket/application/editor/edit_ops/budgeting.py` (budget application + preflight fit checks)
- `src/skriptoteket/application/editor/edit_ops/routing.py` (failover routing + record success/failure)
- `src/skriptoteket/application/editor/edit_ops/execution.py` (provider call + retryability logic)
- `src/skriptoteket/application/editor/edit_ops/capture.py` (capture-on-error helper)

**Steps**

1. Extract constants and pure helpers first (no behavior change).
2. Extract persistence operations behind small functions (keep dependencies explicit: repos + uow + ids).
3. Extract failover routing logic (keep “decision” logic close to `ChatFailoverRouterProtocol` calls).
4. Extract provider execution + retryability checks.
5. Keep `EditOpsHandler` as orchestration glue and make sure it still:
   - Enforces role guard
   - Uses in-flight guard correctly
   - Records turns/messages consistently
   - Preserves all error messages/semantics

**Files likely to be touched**

- `src/skriptoteket/application/editor/edit_ops_handler.py`
- `tests/unit/application/test_editor_edit_ops_handler.py`
- `tests/unit/application/test_editor_edit_ops_capture_on_error.py`
- New modules under `src/skriptoteket/application/editor/edit_ops/`

### 6) Backend: Unified diff applier (P1) — split parsing/normalization/apply (behavior-preserving)

**Current file:** `src/skriptoteket/infrastructure/editor/unified_diff_applier.py` (~606 LOC)
**Reason:** Mixes multiple responsibilities (diff normalization, parsing/repair, subprocess invocation, error mapping).

**Target outcome**

- Keep the public protocol (`UnifiedDiffApplierProtocol`) and current default implementation behavior.
- Split the file into cohesive modules so the applier is thin and testable:
  - text normalization (pure)
  - diff parsing/repair (pure)
  - subprocess apply + output mapping (impure)

**Suggested module layout (example)**

- `src/skriptoteket/infrastructure/editor/unified_diff_applier.py` (thin entry + exports)
- `src/skriptoteket/infrastructure/editor/unified_diff/normalize.py`
- `src/skriptoteket/infrastructure/editor/unified_diff/parse.py`
- `src/skriptoteket/infrastructure/editor/unified_diff/apply_patch.py`
- `src/skriptoteket/infrastructure/editor/unified_diff/errors.py`

**Steps**

1. Move pure normalization helpers into `normalize.py` (keep deterministic “applied” annotations).
2. Move parsing/repair helpers into `parse.py` (keep existing error semantics/messages).
3. Keep subprocess invocation + output parsing in a single module with explicit inputs/outputs.
4. Update imports in `src/skriptoteket/application/editor/edit_ops_preview_handler.py` if needed, but preserve behavior.

**Files likely to be touched**

- `src/skriptoteket/infrastructure/editor/unified_diff_applier.py`
- `src/skriptoteket/application/editor/edit_ops_preview_handler.py`
- New: `src/skriptoteket/infrastructure/editor/unified_diff/*`

## Inventory: >500 LOC files (as of 2026-01-16)

This list is ordered by **criticality** (runtime/perf impact first) and then **priority** (maintainability + churn).
Items marked **(generated/binary)** are not candidates for SRP refactor.

### P0 (in scope for this PR)

1. `frontend/apps/skriptoteket/src/components/help/HelpPanel.vue` (596) — eagerly loaded in SPA entry
2. `src/skriptoteket/infrastructure/runner/docker_runner.py` (628) — tool execution hot path
3. `src/skriptoteket/application/editor/edit_ops_handler.py` (918) — high-churn orchestration “god handler”

### P1 (in scope for this PR)

4. `frontend/apps/skriptoteket/src/views/HomeView.vue` (677) — main landing view chunk; large UI + data loading
5. `frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue` (753) — complex admin/editor view (route-chunked)
6. `src/skriptoteket/infrastructure/editor/unified_diff_applier.py` (606) — patch normalization + parsing + subprocess apply

### P2 (next; high value follow-ups, likely separate PRs)

7. `frontend/apps/skriptoteket/src/composables/editor/useEditorChat.ts` (581) — editor AI chat client state machine
8. `frontend/apps/skriptoteket/src/composables/editor/useEditorEditOps.ts` (578) — edit-ops client orchestration
9. `src/skriptoteket/application/editor/edit_ops_preview_handler.py` (503) — preview + apply handler in one file
10. `src/skriptoteket/protocols/llm.py` (643) — mixed Pydantic DTOs + protocols; candidate for split by concern
11. `src/skriptoteket/web/api/v1/editor/models.py` (572) — large API surface; candidate for split by endpoint area

### P3 (later; mostly dev/admin tools or large demo scripts)

12. `src/skriptoteket/cli/commands/seed_script_bank.py` (530) — CLI orchestration; refactor only if churn continues
13. `src/skriptoteket/script_bank/scripts/html_to_pdf_preview.py` (1037) — demo tool; split into cohesive helpers if maintained
14. `src/skriptoteket/script_bank/scripts/markdown_to_docx.py` (705) — tool script; only refactor if actively evolving
15. `src/skriptoteket/script_bank/scripts/yrkesgenerator.py` (685) — tool script; only refactor if actively evolving
16. `scripts/ai_prompt_eval/run_live_backend.py` (605) — internal tooling; refactor optional
17. `scripts/export_runbook_pdf_html.py` (562) — internal tooling; refactor optional

### P4 (do not refactor as SRP “code” tasks; track separately if needed)

18. `frontend/apps/skriptoteket/src/api/openapi.d.ts` (6059) — **generated**
19. `frontend/pnpm-lock.yaml` (3807) — **lockfile**
20. `pdm.lock` (3203) — **lockfile**
21. `docs/research/54945-ppr-family-17h-models-00h-0fh-processors/54945_3.03_ppr_ZP_B2_pub.pdf` (57919) — **binary**
22. `docs/reference/ref-ai-script-generation-kb.md` (1000) — large doc
23. `docs/runbooks/runbook-home-server.md` (793) — large runbook
24. `docs/runbooks/runbook-gpu-ai-workloads.md` (683) — large runbook
25. `docs/reference/ref-ai-completion-architecture.md` (589) — large doc
26. `docs/reference/reports/ref-vue-spa-migration-roadmap.md` (640) — report
27. `docs/reference/reports/ref-external-observability-integration.md` (611) — report
28. `docs/reference/reports/ref-hemma-host-freeze-investigation-2026-01-03.md` (584) — report
29. `docs/reference/reports/ref-frontend-expert-review-epic-05.md` (578) — report
30. `docs/reference/reports/artifacts/llama-canonical-chat-v3/llama-canonical-chat-v3-20260105T012947Z/review.telemetry.txt` (2220) — artifact
31. `docs/reference/reports/artifacts/llama-canonical-chat-v3/llama-canonical-chat-v3-20260105T012947Z/diff.telemetry.txt` (2220) — artifact
32. `doc_structure_requirements.md` (596) — legacy doc; consider archiving/pruning separately
33. `observability/grafana/provisioning/dashboards/skriptoteket-nginx-proxy-security.json` (567) — dashboard config
34. `.claude/skills/distributed-tracing/reference.md` (564) — skill reference
35. `.claude/skills/structlog-logging/reference.md` (544) — skill reference
36. `.claude/skills/loki-logql/reference.md` (528) — skill reference
37. `stakeholders/tooleditor_flow.html` (1417) — stakeholder artifact
38. `stakeholders/server_runbook_pdf.html` (912) — stakeholder artifact
39. `stakeholders/sommarskuggan.html` (662) — stakeholder artifact

**Large test files (split only if they become unmaintainable; not performance-critical)**

40. `tests/unit/application/test_editor_chat_handler.py` (862)
41. `tests/unit/application/identity/test_register_user_handler.py` (793)
42. `tests/unit/web/test_api_v1_auth_and_csrf_routes.py` (642)
43. `tests/unit/web/test_editor_api_routes.py` (546)
44. `tests/unit/domain/scripting/test_scripting_models.py` (558)
45. `tests/unit/application/scripting/handlers/test_interactive_tool_api.py` (618)
46. `tests/unit/application/scripting/handlers/test_run_active_tool.py` (517)
47. `tests/integration/infrastructure/repositories/test_catalog_repository.py` (548)
48. `tests/integration/infrastructure/repositories/test_tool_run_repository.py` (538)

## Test plan

- Frontend: `pdm run fe-type-check`, `pdm run fe-test`, `pdm run fe-build`
- Backend: `pdm run test` (and `pdm run lint` if you touched Python)
- Manual checks (required if UI changes):
  - Start `pdm run dev-local`, load `/`, open the Help panel, confirm topics render and route-sync still works.

## Rollback plan

- Revert the PR commit(s). No migrations, no schema changes expected.
