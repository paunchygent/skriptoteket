# Session Handoff
Keep this file updated so the next session can pick up work quickly.
## Editing Rules (do not break structure)
- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines.
- When compacting this file, move non-session-vital history to `.codex/long-term-memory/entries/` first.
## Snapshot
- Date: 2026-06-19.
- Branch: `main`.
- Latest closed slice: `PR-0364` under `ST-37-03`; current planned slice:
  `PR-0365` authenticated shell navigation realignment.
- Older PR-0355/PR-0356 proof and Hemma deploy detail was compacted to
  `.codex/long-term-memory/entries/session-2026-06-19-pr-0355-pr-0356-and-pr-0363-runtime-compaction.md`.
- Prior PR-0310 through PR-0354 history lives in existing entries under
  `.codex/long-term-memory/entries/`.
## Status
- `EPIC-37` is active. `PR-0358` through `PR-0362` are done and govern the
  current product direction, Sir Convert boundary, shell plan, and app
  presentation sequence.
- `PR-0363` is done and approved by `REV-PR-0363`:
  `frontend/apps/skriptoteket/src/views/apps/conversionHubModeRoute.ts`,
  `frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedView.vue`,
  `frontend/apps/skriptoteket/src/views/apps/ConversionHubModeTabs.vue`, and
  focused specs under `frontend/apps/skriptoteket/src/views/apps/`.
- `ST-37-03` remains open for `PR-0365` authenticated shell navigation
  realignment.
- `PR-0364` is done and approved by `REV-PR-0364` after user approval and overseer
  design-rule alignment of the C2 authenticated home mockup:
  `docs/mockups/pr-0364-authenticated-home-work-apps-surface/README.md`.
  It should make authenticated `/` app-first with primary shelves for
  Klassrumskartan, Provkonverteraren `?mode=exam`, Ljudtranskribering
  `?mode=transcript`, Dokumentkonverteraren, and Kodredigerare. Do not fake the
  Dokumentkonverteraren route; stop/attach a route-visible slice if no truthful
  target exists.
- `PR-0364` runtime frontend implementation is now in
  `frontend/apps/skriptoteket/src/views/HomeView.vue`,
  `frontend/apps/skriptoteket/src/components/home/HomeWorkAppsSection.vue`,
  `frontend/apps/skriptoteket/src/components/home/homeWorkApps.ts`, and
  `frontend/apps/skriptoteket/src/views/HomeView.spec.ts`. Follow-up review
  fixes are now in `frontend/apps/skriptoteket/src/composables/home/useHomeDashboard.ts`
  and `frontend/apps/skriptoteket/src/composables/home/useHomeDashboard.spec.ts`.
  Authenticated `/` is app-first, `Kodredigerare` is primary,
  Dokumentkonverteraren is visible but non-linkable, the default home loader no longer
  hits retired runs/favorites/recent endpoints, and the old home
  `dashboard-card` grid plus `Mina körningar`/latest/recent chrome are
  removed.
- `REV-PR-0364` is now `approved`. Final proof closeout confirmed the
  loader-boundary and HomeView-spec findings stayed fixed and that the
  Docker-backed authenticated browser proof passed when using the HuleEdu
  auth-integration `local-shared-verify-export.json` that matches the running
  Identity service DB. See
  `docs/backlog/reviews/review-pr-0364-authenticated-home-work-apps-surface.md`.
- Post-deploy correction: authenticated home app cards now use image identities
  instead of CSS graph-paper sketches. `Klassrumskartan` reuses the existing
  classroom-map symbol; the other visible app-card labels are Swedish:
  `Provkonverteraren`, `Ljudtranskribering`, `Dokumentkonverteraren`, and
  `Kodredigerare`.
- The PR-0364 rejected card-grid and service-foyer attempts were deleted at
  user request on 2026-06-19; do not implement either layout. Approved C2 also
  removes `Mina körningar`, latest-used/recent-used home chrome, separate
  `Öppna` links, and nested card layouts.
- `PR-0364` mockup/docs alignment and independent review validation passed:
  `pdm run docs-validate`, `pdm run handoff-validate`, and `git diff --check`.
- Docker-service breadcrumb is now encoded in
  `.codex/skills/skriptoteket-testing/references/browser-automation.md`,
  `.codex/skills/skriptoteket-testing/references/backend-pytest.md`,
  `docs/runbooks/runbook-testing.md`, and the shared
  `local-devops/references/skriptoteket.md`.
- Protected HuleEdu Gateway/browser-session proof must use Docker
  `skriptoteket_web` on `hule-network` with alias `skriptoteket-web`; do not
  use host Uvicorn for this lane.
## Verification
- Current local shared-auth runtime:
  - HuleEdu Gateway container `huleedu_api_gateway_service` healthy on
    `http://localhost:8080`.
  - Skriptoteket Docker service `skriptoteket_web` running and reachable from
    Gateway as `http://skriptoteket-web:8000`.
  - Host Skriptoteket Vite at `http://localhost:5173` with
    `VITE_DEV_PROXY_TARGET=http://localhost:8080`.
- Gateway-to-Skriptoteket Docker check passed:
  `docker exec huleedu_api_gateway_service curl -sS -i --max-time 10 http://skriptoteket-web:8000/healthz`.
- Focused verification passed:
  - Red-first loader proof:
    `pdm run fe-test -- --run src/composables/home/useHomeDashboard.spec.ts`
    failed because the default authenticated-home loader still called
    `/api/v1/my-runs`, `/api/v1/favorites?limit=5`, and
    `/api/v1/me/recent-tools?limit=5`.
  - `pdm run fe-test -- --run src/views/HomeView.spec.ts src/composables/home/useHomeDashboard.spec.ts`
    passed with 7 tests for the authenticated home shelf behavior plus the
    new loader-boundary contract.
  - `pdm run fe-test -- --run src/views/HomeView.spec.ts` passed with 5 tests
    for the authenticated home app shelf, truthful route targets, retired-home
    chrome removal, secondary-ledger structure, and signed-out unchanged
    behavior.
  - `pdm run fe-type-check`
  - `pdm run fe-lint`
  - `pdm run docs-validate`
  - `pdm run handoff-validate`
  - `git diff --check`
  - `pdm run test tests/unit/scripts/test_playwright_script_surface.py`
    passed with 3 tests.
- PR-0364 live browser proof passed:
  - Docker/Gateway lane is healthy and `skriptoteket_web` resolves from
    `huleedu_api_gateway_service`.
  - Started missing HuleEdu login UI lane with
    `pdm run run-local-pdm auth-integration fe-dev` in the HuleEdu repo.
  - Correct preflight:
    `pdm run auth-edge-bootstrap-preflight --export-json /Users/olofs_mba/Documents/Repos/huleedu/.artifacts/skriptoteket-auth-bootstrap/local-shared-verify-export.json --output-json .artifacts/skriptoteket-auth-bootstrap/preflight-pr-0364-local-shared.json`
    passed with all checks `ok`.
  - Retained proof:
    `pdm run python -m scripts.playwright_pr_0364_authenticated_home_work_apps --base-url http://localhost:5173`
    passed.
  - Retained artifact:
    `.artifacts/playwright-pr-0364-authenticated-home-work-apps-surface/20260619T102703Z/manifest.redacted.json`.
  - Captures:
    `authenticated-home-desktop.png` at `1512x900` and
    `authenticated-home-compact.png` at `390x844`.
- PR-0364 post-deploy app-card visual identity proof passed:
  - Correct preflight:
    `pdm run auth-edge-bootstrap-preflight --export-json /Users/olofs_mba/Documents/Repos/huleedu/.artifacts/skriptoteket-auth-bootstrap/local-shared-verify-export.json --output-json .artifacts/skriptoteket-auth-bootstrap/preflight-pr-0364-visual-identity.json`
    passed with all checks `ok`.
  - Retained proof:
    `pdm run python -m scripts.playwright_pr_0364_authenticated_home_work_apps --base-url http://localhost:5173 --artifact-root .artifacts/playwright-pr-0364-authenticated-home-work-apps-surface-visual-identity`
    passed.
  - Retained artifact:
    `.artifacts/playwright-pr-0364-authenticated-home-work-apps-surface-visual-identity/20260619T135320Z/manifest.redacted.json`.
  - Captures:
    `authenticated-home-desktop.png` at `1512x900` and
    `authenticated-home-compact.png` at `390x844`.
## How to Run
```bash
# Reuse or start HuleEdu auth integration first, then ensure Skriptoteket uses Docker web.
DOCKER_BUILDKIT=1 COMPOSE_DOCKER_CLI_BUILD=1 docker compose -f compose.yaml -f compose.dev.yaml up -d web

# Start/reuse Skriptoteket Vite with protected API traffic proxied to HuleEdu Gateway.
VITE_HULEEDU_AUTH_BASE_URL=http://localhost:8080 VITE_HULEEDU_AUTH_ENTRY_URL=http://localhost:8080/auth/login VITE_DEV_PROXY_TARGET=http://localhost:8080 pdm run fe-dev

# If the HuleEdu login UI is not already serving on :5174, start it from the HuleEdu repo.
(cd /Users/olofs_mba/Documents/Repos/huleedu && pdm run run-local-pdm auth-integration fe-dev)

# Verify Gateway can resolve the product backend by Docker alias.
docker exec huleedu_api_gateway_service curl -sS -i --max-time 10 http://skriptoteket-web:8000/healthz

# Focused PR-0364 checks.
pdm run fe-test -- --run src/views/HomeView.spec.ts src/composables/home/useHomeDashboard.spec.ts
pdm run fe-type-check
pdm run fe-lint
pdm run docs-validate
pdm run handoff-validate
git diff --check

# Browser-proof preflight and retained proof for PR-0364.
pdm run auth-edge-bootstrap-preflight --export-json /Users/olofs_mba/Documents/Repos/huleedu/.artifacts/skriptoteket-auth-bootstrap/local-shared-verify-export.json --output-json .artifacts/skriptoteket-auth-bootstrap/preflight-pr-0364-local-shared.json
pdm run python -m scripts.playwright_pr_0364_authenticated_home_work_apps --base-url http://localhost:5173

```
## Known Issues / Risks
- Do not start host `pdm run dev`/Uvicorn for Gateway-authenticated backend dev
  tests or browser proof. Gateway app continuation uses Docker DNS
  `skriptoteket-web:8000`, so host Uvicorn reproduces a false failure.
- If PR-0364/PR-0365 preflight fails with `missing_identity_projection`, first
  verify the export path. The running HuleEdu auth-integration lane currently
  matches
  `/Users/olofs_mba/Documents/Repos/huleedu/.artifacts/skriptoteket-auth-bootstrap/local-shared-verify-export.json`;
  `local-verify-export.json` targets a different Identity DB generation and
  reproduces a false `identity_linking_required` failure.
- If Gateway `:8080` appears occupied by Docker while no container publishes
  it, suspect stale Docker Desktop port-proxy state; restart Docker Desktop and
  recreate the affected HuleEdu services before blaming app code.
- `REV-PR-0363` is approved. Keep the Docker-service proof lane intact for
  `PR-0364` and `PR-0365`.
## Next Steps
- Continue with `PR-0365` authenticated shell navigation realignment.
- `PR-0277` remains open for `REV-PR-0277` plus fresh Teams unfurl proof.
