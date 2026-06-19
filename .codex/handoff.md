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
- Latest closed slice: `PR-0365` under `ST-37-03`.
- Active slice: none; the current repo session closed `PR-0365`.
- Next planned slice remains `PR-0366` copy-only app-lane alignment under
  `ST-37-04`.
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
- `PR-0365` is done. `frontend/apps/skriptoteket/src/components/layout/AuthSidebar.vue`,
  `frontend/apps/skriptoteket/src/components/layout/AuthSidebar.spec.ts`, and
  `scripts/playwright_pr_0365_authenticated_shell_navigation.py` now keep the
  persistent sidebar/mobile drawer utility-first with `Hem`, `Mina filer`,
  `Föreslå verktyg`, `Katalog`, and `Profil`; keep `Hjälp` owned only by the
  top auth bar; keep contributor/admin links below the utility block; and keep
  duplicate app links plus `Mina körningar`/`Dokumentkonvertering` out of
  persistent nav. `ST-37-03` is now done with retained shared-auth proof at
  `.artifacts/playwright-pr-0365-authenticated-shell-navigation/20260619T212625Z/`.
- `PR-0364` is done and approved by `REV-PR-0364`; detailed proof and
  post-deploy correction history was compacted to
  `.codex/long-term-memory/entries/session-2026-06-19-pr-0364-auth-home-proof-compaction.md`.
  Keep the authenticated-home app symbols from
  `frontend/apps/skriptoteket/src/components/home/homeWorkApps.ts`.
- `PR-0370` public landing image direction is approved:
  `docs/mockups/pr-0370-public-landing-authenticated-app-preview/round-4-no-index-markers.png`.
  Final copy is approved under
  `docs/mockups/pr-0370-public-landing-authenticated-app-preview/approved-copy.md`.
  HTML/CSS mockup is approved at
  `docs/mockups/pr-0370-public-landing-authenticated-app-preview/index.html`;
  production implementation now belongs to `PR-0371`, including
  `docs/reference/ref-public-landing-copy-lock.md`.
- `PR-0371` is done and approved by `REV-PR-0371`:
  `frontend/apps/skriptoteket/src/views/HomeView.vue` no longer renders
  `LandingFeaturedClassroom`, and
  `frontend/apps/skriptoteket/src/components/home/LandingAuthenticatedPreview.vue`
  now renders the approved `När du loggar in` three-panel preview using the
  same app symbols as authenticated home. The review-fix pass made those three
  public preview images eager, synchronous, and high-priority after the first
  retained mobile proof left lower preview symbols blank.
- `PR-0372` is done:
  `frontend/apps/skriptoteket/src/components/layout/LandingLayout.vue` and
  `frontend/apps/skriptoteket/src/components/layout/LandingLayout.spec.ts` now
  keep the signed-out header to brand + `Logga in` + `Hjälp`, remove the
  duplicate public `Klassrumskartan` link, and keep the small-screen header on
  one row.
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
- PR-0365 / PR-0372 current focused evidence:
  - Red-first: `pdm run fe-test -- --run src/components/layout/AuthSidebar.spec.ts src/components/layout/AuthLayout.spec.ts src/App.spec.ts`
    failed because the sidebar still rendered duplicate `Hjälp` after `Profil`
    instead of leaving help solely in the top auth bar.
  - Red-first: `pdm run fe-test -- --run src/components/layout/LandingLayout.spec.ts`
    failed because the old public header still rendered `Klassrumskartan`.
  - Focused green: `pdm run fe-test -- --run src/components/layout/AuthSidebar.spec.ts src/components/layout/AuthLayout.spec.ts src/App.spec.ts`
    passed with 10 tests.
  - Script-surface green:
    `pdm run test tests/unit/scripts/test_playwright_script_surface.py`
    passed with 3 tests.
  - Frontend static gates:
    `pdm run fe-type-check`
    and
    `pdm run fe-lint`
    both passed.
  - Focused green: `pdm run fe-test -- --run src/components/layout/LandingLayout.spec.ts`
    passed with 2 tests.
  - Combined green: `pdm run fe-test -- --run src/components/layout/AuthSidebar.spec.ts src/components/layout/AuthLayout.spec.ts src/App.spec.ts src/components/layout/LandingLayout.spec.ts src/views/HomeView.spec.ts`
    passed with 17 tests.
  - `pdm run run-local-pdm auth-integration check` passed from the HuleEdu
    repo, confirming Gateway/login UI/proxy readiness for shared-auth proof.
  - In-app browser public proof on `http://localhost:5173/` confirmed:
    - desktop header contains only brand, `Logga in`, and `Hjälp`
    - mobile header keeps brand, `Logga in`, and `Hjälp` on one row
    - the public header no longer renders `Klassrumskartan`
    - retained screenshots:
      `.artifacts/pr-0372-public-landing-header-simplification/public-landing-desktop.png`
      and
      `.artifacts/pr-0372-public-landing-header-simplification/public-landing-mobile.png`
  - Protected authenticated sidebar/mobile-drawer proof now passed with:
    `pdm run python -m scripts.playwright_pr_0365_authenticated_shell_navigation --base-url http://localhost:5173`
    retaining artifacts at
    `.artifacts/playwright-pr-0365-authenticated-shell-navigation/20260619T212625Z/`.
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

# Focused PR-0365 / PR-0372 checks.
pdm run fe-test -- --run src/components/layout/AuthSidebar.spec.ts src/components/layout/AuthLayout.spec.ts src/App.spec.ts src/components/layout/LandingLayout.spec.ts src/views/HomeView.spec.ts
pdm run fe-type-check
pdm run fe-lint
pdm run docs-validate
pdm run handoff-validate
git diff --check

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
- After `PR-0365`, continue with `PR-0366` copy-only app-lane naming
  alignment without reintroducing `Mina körningar`; route retirement remains a
  later slice.
- `PR-0277` remains open for `REV-PR-0277` plus fresh Teams unfurl proof.
