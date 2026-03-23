# Session Handoff
Keep this file updated so the next session can pick up work quickly.

## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines; move history to `.agents/readme-first.md` + `docs/`.

## Snapshot

- Date: 2026-03-23
- Branch: `main` + local changes
- Current sprint: Sprint 24
- Production: Full Vue SPA
- Completed: `ST-24-01`, `ST-24-05`, `ST-24-02`, `ST-24-03`, `PR-0090`, `PR-0091`, `PR-0092`, `PR-0093`, `PR-0101`, `PR-0102`, `PR-0103`, `PR-0104`, and `PR-0105`.

## Status

- Klassrumskartan fundamentals lane is largely shipped:
  - grouping has blank `Nytt grupputkast`, grouping-only undo/redo, and a continuity drawer with reopen/delete for historic grouping drafts
  - overview is now quiet; the segmented toggle is the single mode switch
  - seating builder slices `PR-0101` to `PR-0103` are done (resize, ghost preview, wall-vs-floor rendering, artwork, zoom, `Anpassa`, `Rensa`, circular seats)
- `PR-0105` is now implemented locally:
  - backend: explicit seating lifecycle routes in `src/skriptoteket/web/api/v1/apps_classroom_planner_seating.py`
  - application: `src/skriptoteket/application/curated_apps/classroom_planner/handlers/seating_drafts.py` and `seating_history.py`
  - frontend: `PlannerWorkspaceShell.vue` exposes `Historik`, `Nytt sittschema`, and `Redigera klassrum` in the seating action row
  - continuity: seating reuses `PlannerHistoryDrawer.vue` for `Aktuellt sittschema` + `Tidigare sittscheman`
  - guardrail: `Nytt sittschema` requires a selected classroom and otherwise focuses the classroom picker with a teacher-facing hint
  - safety: seating create/open/delete actions now lock the seating toolbar and drawer while in flight
- Ruthless review of `PR-0105` was completed with a `GPT-5.4` high subagent:
  - busy-state / reentrancy issue: fixed and covered by tests
  - non-null `template_id` contract gap: fixed and covered by tests
  - flaky shared smoke dependency: replaced with a dedicated `PR-0105` browser proof
- `ST-24-04` stays open only for `PR-0106`: seating-specific undo/redo plus bounded in-draft history.
- Competitive-games lane is separate:
  - `ST-25-01` and `ST-25-02` are done through `PR-0104`
  - next planned chain there is `PR-0107` -> `PR-0108` -> `ST-25-03`

## Previous Sessions

- Older detailed verification history is now carried by story/epic docs plus git history; keep this handoff focused on the current sprint-critical state only.

## Verification

- 2026-03-23: `lsof -nP -iTCP:5173 -sTCP:LISTEN`; `lsof -nP -iTCP:4173 -sTCP:LISTEN`; `lsof -nP -iTCP:8000 -sTCP:LISTEN` (confirmed canonical local app on `127.0.0.1:5173`, backend on `127.0.0.1:8000`, and no extra `:4173` server).
- 2026-03-23: `pdm run pytest tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/web/apps/classroom_planner/test_api.py -q` (42 PASSED).
- 2026-03-23: `pdm run pytest tests/unit/web/apps/classroom_planner/test_api.py -q` (24 PASSED after adding the non-null `template_id` boundary test).
- 2026-03-23: `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/useClassroomState.spec.ts -t 'starts a brand-new seating draft through the dedicated lifecycle endpoint|activates a historical seating draft through the dedicated lifecycle endpoint|deletes a historical seating draft through the dedicated lifecycle endpoint' --reporter=verbose` (3 PASSED).
- 2026-03-23: `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/ClassroomPlannerView.spec.ts` (29 PASSED after adding seating busy-state/reentrancy coverage).
- 2026-03-23: `pdm run ruff check src/skriptoteket/application/curated_apps/classroom_planner/handlers/seating_drafts.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/seating_history.py src/skriptoteket/application/curated_apps/classroom_planner/__init__.py src/skriptoteket/di/curated_apps.py src/skriptoteket/web/api/v1/apps_classroom_planner_seating.py src/skriptoteket/web/router.py tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/web/apps/classroom_planner/test_api.py scripts/playwright_classroom_planner_smoke.py scripts/playwright_pr_0105_seating_continuity.py` (PASSED).
- 2026-03-23: `pdm run mypy src/skriptoteket/application/curated_apps/classroom_planner/handlers/seating_drafts.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/seating_history.py src/skriptoteket/application/curated_apps/classroom_planner/__init__.py src/skriptoteket/di/curated_apps.py src/skriptoteket/web/api/v1/apps_classroom_planner_seating.py` (PASSED).
- 2026-03-23: `pnpm -C frontend --filter @skriptoteket/spa exec eslint src/views/apps/useClassroomState.ts src/views/apps/useClassroomState.spec.ts src/views/apps/ClassroomPlannerView.vue src/views/apps/ClassroomPlannerView.spec.ts src/views/apps/components/PlannerWorkspaceShell.vue src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/components/PlannerHistoryDrawer.vue`; `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit`; `pnpm -C frontend --filter @skriptoteket/spa build` (PASSED).
- 2026-03-23: `pdm run python -m scripts.playwright_pr_0105_seating_continuity --base-url http://127.0.0.1:5173` (PASSED; proved classroom-required `Nytt sittschema`, verified a fresh seating draft clears a real seat assignment, reopened historic seating to restore that assignment, then deleted the remaining historic draft; artifact in `.artifacts/classroom-planner-smoke/pr0105-seating-continuity-proof.png`).
- 2026-03-23: `pdm run docs-validate` (PASSED after closing out `PR-0105`, updating `ST-24-04`, `EPIC-24`, and this handoff).

## How to Run

```bash
# Setup
docker compose up -d db && pdm run db-upgrade

# Development (backend + SPA)
ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts pdm run dev-local

# Focused verification
pdm run pytest tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/web/apps/classroom_planner/test_api.py -q
pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/useClassroomState.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/ClassroomPlannerView.spec.ts
pdm run python -m scripts.playwright_pr_0105_seating_continuity --base-url http://127.0.0.1:5173
```

## Known Issues / Risks

- `ST-24-04` remains open only for `PR-0106`: seating-specific undo/redo plus bounded in-draft history.
- Room-template editing must stay outside seating undo/redo; only seating-draft state belongs to the future seating history stack.
- `scripts/playwright_classroom_planner_smoke.py` still covers a broader surface than PR-level proofs; prefer the dedicated `PR-0105` browser proof for seating lifecycle regressions.

## Next Steps

- Implement `PR-0106`: generalize the current backend-owned draft-history mechanics from grouping-only to draft-kind-aware behavior where needed, then surface `Ångra` / `Gör om` in the seating action row.
- Reuse the shipped `PR-0105` continuity drawer/action row; do not reintroduce overview-level seating lifecycle controls.
- Keep room-template editing in `CreateRoomTemplateModal.vue` outside seating undo/redo.
- After `PR-0106`, re-run the dedicated seating proof plus a fresh browser pass for seating undo/redo before closing `ST-24-04`.
- Competitive-games lane is separate: after `PR-0107` and `PR-0108`, the next product slice there is `ST-25-03`.
