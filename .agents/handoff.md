# Session Handoff
Keep this file updated so the next session can pick up work quickly.
## Editing Rules (do not break structure)
- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines.
- When compacting this file, append the removed content directly to `docs/reference/ref-development-changelog.md` first.
## Snapshot
- Date: 2026-04-07
- Branch: `main` + local changes
- Current lane: `PR-0232` guest local continuity, export, and account-only history polish
- Production: Full Vue SPA
- Completed: `PR-0231` is implemented locally with review follow-ups fixed; `ST-09-09` is done with the shipped Hemma deploy launcher/monitor path; ShellCheck is now part of pre-commit and `pdm run lint`; active docs guidance now has a canonical development changelog and the stale v0.2 implementation map has been removed
## Status
- `PR-0231` is implemented locally and its retained review follow-ups are fixed. Guest `Regler`, public solver-backed Smart, request streaming limits, persistence rollback, and helper-family throttle wiring are in place.
- `PR-0232` is now the next implementation slice. It owns guest local undo/redo parity, direct-download export through dedicated public routes, and final account-only history/recovery affordance polish under approved `REV-PR-0231`.
- `ST-09-09` is done. The canonical local operator commands are `pdm run hemma-deploy` and `pdm run hemma-deploy-monitor`, while the on-host deploy script remains the single deploy/readiness source of truth.
- Shell quality is part of the normal repo gate now: `pre-commit` runs ShellCheck on staged shell scripts, and `pdm run lint` includes repo-wide `pdm run shellcheck-all`.
- Active docs guidance now uses `docs/reference/ref-development-changelog.md` as the append-only dump for removed handoff history, and the stale `REF-implementation-map-script-hub-v0-2` reference has been removed.
## Verification
- `pdm run lint` (pass; includes repo-wide `shellcheck-all`)
- `pdm run docs-validate` (pass after deleting `REF-implementation-map-script-hub-v0-2`, adding `REF-development-changelog`, compacting `.agents/handoff.md`, and aligning the handoff/changelog invariant in active guidance)
- `pdm run fe-test -- --run src/views/apps/ClassroomPlannerGuestOverviewView.spec.ts src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts src/views/apps/usePublicSmartGroupingRun.spec.ts src/views/apps/usePublicSmartSeatingRun.spec.ts` (pass; guest overview/shell parity plus public Smart composables)
- `pdm run pytest tests/unit/application/apps/classroom_planner/test_public_smart_run.py tests/unit/web/test_public_apps_classroom_planner_smart.py` (pass; stateless public Smart handlers and public helper routes)
- Live public browser proof against `http://127.0.0.1:5173/public/apps/classroom.group-seating-studio` with local backend on `http://127.0.0.1:8000` (pass; guest `Regler`, guest Smart drawer parity without `Historik`, and live `POST /api/v1/public/apps/classroom.group-seating-studio/grouping/smart-run` `200 OK`)
- Live production proof on Hemma (pass on 2026-04-07): `pdm run hemma-deploy` handed off detached remote PID `1243606`; the authoritative raw log `/home/paunchygent/apps/skriptoteket/.artifacts/hemma-deploy-20260407-092323.log` shows commit `94be5c23bbfb8294278cf21d3f679ee693277f73` deployed, migrations applied, and seating-export smoke passed
## How to Run
```bash
ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts pdm run dev-local
pdm run fe-test -- --run src/views/apps/ClassroomPlannerGuestOverviewView.spec.ts src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts src/views/apps/usePublicSmartGroupingRun.spec.ts src/views/apps/usePublicSmartSeatingRun.spec.ts
pdm run pytest tests/unit/application/apps/classroom_planner/test_public_smart_run.py tests/unit/web/test_public_apps_classroom_planner_smart.py
pdm run fe-type-check
pdm run docs-validate
```
## Known Issues / Risks
- The authenticated route still shows the pre-existing guest-upgrade import dialog with `Internal server error`; this did not block the planner verification because `Inte nu` closed it, but the upgrade/import path still needs its own debugging lane.
- `ClassroomPlannerView.spec.ts` still emits the pre-existing suppressed runtime warning from `resolveHomeRosterId(...)` during one centered-shell test even though the suite passes; it was not part of `PR-0226`.
## Next Steps
- Execute `PR-0232` next as the remaining `ST-32-06` guest-mode bridge slice: guest local undo/redo parity, direct-download export, and account-only history/recovery affordance polish.
- Keep guest/public continuity honest in `PR-0232`: local undo/redo only, direct-download export only, and no fallback into authenticated export/history/recovery seams.
- Return to `PR-0229` only after the guest-mode bridge slice if the planner-toolbar overflow lane still needs dedicated follow-up.
- Debug the authenticated guest-upgrade import prompt separately; it remains outside the current `PR-0232` lane.
