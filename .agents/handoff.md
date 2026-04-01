# Session Handoff
Keep this file updated so the next session can pick up work quickly.
## Editing Rules (do not break structure)
- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines; move history to `docs/`.
## Snapshot
- Date: 2026-04-01
- Branch: `main` + local changes
- Current sprint: Sprint 24
- Production: Full Vue SPA
- Completed: `PR-0120`, `PR-0121`, `PR-0122`, `PR-0123`, `PR-0124`, `PR-0125`, `PR-0126`, `PR-0128`, `PR-0129`, `PR-0130`, `PR-0137`, `PR-0138`, `PR-0139`, `PR-0140`, `PR-0142`, `PR-0143`, `PR-0145`, `PR-0146`, `PR-0147`, `PR-0148`, `PR-0149`, `PR-0150`, `PR-0151`, `PR-0152`, `PR-0153`, `PR-0154`, `PR-0155`, `PR-0157`, `PR-0161`, `PR-0162`, `PR-0163`, `PR-0164`, `PR-0165`, `PR-0166`, `PR-0169`, `PR-0170`, `PR-0171`, `PR-0173`, `PR-0174`, `PR-0176`, `PR-0177`, `PR-0179`, `PR-0180`, `PR-0181`, `PR-0185`, `PR-0186`
## Status
- `ST-29-06` / `PR-0187` are now implemented locally: `frontend/apps/skriptoteket/src/views/apps/classroomPlannerPayloadNormalization.ts`, `classroomPlannerStateSupport.ts`, `classroomPlannerLifecycle.ts`, `useClassroomPlannerRouteShell.ts`, and `classroomPlannerRouteShellErrors.ts` keep the planner boundary hardening for thin no-classroom payloads and suppress raw runtime/framework text; the canonical local `5173` repro is now known to use the backend-served static SPA bundle until `pdm run fe-build` realigns it; `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesMapCanvas.vue` now renders the approved no-classroom empty-state copy in default `Planeringsvy` while keeping the planning eyebrow on the class name and reserving `Ej på karta` for `Klassrumsvy`; `scripts/playwright_pr_0185_rules_no_classroom_fallback_check.py` now proves that live header contract; and `.codex/agents/skriptoteket-reviewer.toml` now explicitly states that `skriptoteket_reviewer` is the sole reviewer and must not delegate.
- The sole-reviewer loop is now closed for `PR-0187`: the first `skriptoteket_reviewer` pass found a stale draft-save acknowledgement normalization gap in `frontend/apps/skriptoteket/src/views/apps/classroomPlannerStateSupport.ts`, `skriptoteket_implementation_specialist` fixed that slice plus added coverage in `classroomPlannerStateSupport.spec.ts`, and the final sole-reviewer rerun returned no actionable findings.
## Verification
- 2026-04-01 `ST-29-06` / `PR-0187` no-classroom remediation:
  - local API payloads for the no-classroom path returned `200` for `workspace-summary`, `drafts/resolve`, `draft workspace`, and `smart-rules`, and focused diagnostics confirmed the canonical `5173` repro lands on the backend-served static SPA bundle from `:8000`, so `pdm run fe-build` is required before trusting the browser proof
  - `pdm run fe-test -- --run src/views/apps/components/PlannerRulesMapCanvas.spec.ts src/views/apps/components/PlannerRulesWorkspacePane.spec.ts`
  - `pdm run fe-test -- --run src/views/apps/classroomPlannerPayloadNormalization.spec.ts src/views/apps/classroomPlannerRouteShellErrors.spec.ts src/views/apps/classroomPlannerStateSupport.spec.ts src/views/apps/classroomPlannerRouteShellOverviewCrud.spec.ts src/views/apps/ClassroomPlannerView.spec.ts src/views/apps/components/PlannerRulesMapCanvas.spec.ts src/views/apps/components/PlannerRulesWorkspacePane.spec.ts`
  - `pdm run fe-type-check`
  - `pdm run fe-build`
  - `pdm run python -m scripts.playwright_pr_0185_rules_no_classroom_fallback_check --base-url http://127.0.0.1:5173` -> `playwright-pr-0185: ok`
  - `pdm run docs-validate`
  - live functional check on `http://127.0.0.1:5173/apps/classroom.group-seating-studio` via the real bootstrap-superuser browser flow now reaches `Regler` without raw JS text, shows the approved no-classroom empty-state copy in `Planeringsvy`, keeps the planning eyebrow on the class name, and leaves the off-map roster actionable
## How to Run
```bash
ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts pdm run dev-local
pdm run python -m scripts.playwright_classroom_planner_smoke --base-url http://127.0.0.1:5173
ssh hemma 'cd ~/apps/skriptoteket && ./scripts/hemma_deploy_and_verify_seating_export.sh'
```
## Known Issues / Risks
- The canonical local browser proof for Klassrumskartan no-classroom flows depends on the backend-served static SPA bundle once auth redirects into `:8000`; rerun `pdm run fe-build` before trusting `http://127.0.0.1:5173` Playwright outcomes after frontend changes.
- The warnings-as-errors audit still surfaces a dependency-level Python 3.14 deprecation in `pytest-asyncio` (`asyncio.AbstractEventLoopPolicy`); repo-owned code is clean for the audited patterns, but the plugin likely needs a compatible bump.
- Keep the `7d4c1a2b9e6f` repair migration in mind if a long-lived local DB reports Alembic head but misses the roster smart-rule root contract.
- `tests/integration/test_migration_revision_coverage_idempotent.py` still has one pre-existing full-suite harness failure on merge revision `6a1e9d3c4b7f` because `tests/integration/migration_idempotency_support.py` assumes a linear `down_revision`; the new `b7f9c2d4e1a6` revision itself passes both targeted migration checks.
## Next Steps
- Deploy/release remains out of scope for this session; if the no-classroom proof is rerun after more frontend changes, rebuild the backend-served SPA first with `pdm run fe-build`.
