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
- Latest closed slice: `PR-0363` under `ST-37-03`; current planned slice:
  `PR-0364` authenticated home work-apps surface.
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
- `ST-37-03` remains open for `PR-0364` authenticated home work-apps surface
  and `PR-0365` authenticated shell navigation realignment.
- `PR-0364` is ready for `REV-PR-0364` after user approval of the C2
  authenticated home mockup:
  `docs/mockups/pr-0364-authenticated-home-work-apps-surface/README.md`.
  It should make authenticated `/` app-first with primary shelves for
  Klassrumskartan, Exam Converter `?mode=exam`, Audio Transcription
  `?mode=transcript`, Document Converter, and Kodredigerare. Do not fake the
  Document Converter route; stop/attach a route-visible slice if no truthful
  target exists.
- The PR-0364 rejected card-grid and service-foyer attempts were deleted at
  user request on 2026-06-19; do not implement either layout. Approved C2 also
  removes `Mina körningar`, latest-used/recent-used home chrome, separate
  `Öppna` links, and nested card layouts.
- `PR-0364` mockup/docs alignment validation passed: `pdm run docs-validate`,
  `pdm run handoff-validate`, and `git diff --check`.
- Docker-service breadcrumb is now encoded in
  `.codex/skills/skriptoteket-testing/references/browser-automation.md`,
  `.codex/skills/skriptoteket-testing/references/backend-pytest.md`,
  `docs/runbooks/runbook-testing.md`, and the shared
  `local-devops/references/skriptoteket.md`.
- Protected HuleEdu Gateway/browser-session proof must use Docker
  `skriptoteket_web` on `hule-network` with alias `skriptoteket-web`; do not
  use host Uvicorn for this lane.
## Verification
- Correct local runtime for PR-0363 proof:
  - HuleEdu Gateway container `huleedu_api_gateway_service` healthy on
    `http://localhost:8080`.
  - Skriptoteket Docker service `skriptoteket_web` running and reachable from
    Gateway as `http://skriptoteket-web:8000`.
  - Host Skriptoteket Vite at `http://localhost:5173` with
    `VITE_DEV_PROXY_TARGET=http://localhost:8080`.
- Gateway-to-Skriptoteket Docker check passed:
  `docker exec huleedu_api_gateway_service curl -sS -i --max-time 10 http://skriptoteket-web:8000/healthz`.
- PR-0363 authenticated browser proof passed:
  `pdm run python -m scripts.playwright_pr_0363_conversion_mode_deeplink`.
- Retained artifact:
  `.artifacts/playwright-pr-0363-conversion-mode-deeplink/20260618T225544Z/manifest.redacted.json`.
- Proof covered `/apps/documents.conversion_hub?mode=exam` and
  `/apps/documents.conversion_hub?mode=transcript` at viewport `1512x900`.
- Focused verification passed:
  - `pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedView.spec.ts src/views/apps/ExamConverterAuthenticatedView.modeRoute.spec.ts src/views/apps/conversionHubModeRoute.spec.ts src/views/apps/ExamConverterAuthenticatedUiInspectionFixtures.spec.ts`
    passed with 4 files / 44 tests.
  - `pdm run fe-type-check`
  - `pdm run fe-lint`
  - `pdm run fe-build` passed with existing dynamic/static import and
    large-chunk warnings.
  - `pdm run test tests/unit/scripts/test_playwright_script_surface.py`
    passed with 3 tests.
  - `pdm run docs-validate`, `pdm run handoff-validate`, and
    `pdm run skills-validate` passed in this repo.
  - `git diff --check` passed in this repo.
  - Shared skill repo `pdm run skills-validate` and `pdm run docs-validate`
    passed after the `local-devops` breadcrumb update; shared skill repo
    `git diff --check` also passed.
## How to Run
```bash
# Reuse or start HuleEdu auth integration first, then ensure Skriptoteket uses Docker web.
DOCKER_BUILDKIT=1 COMPOSE_DOCKER_CLI_BUILD=1 docker compose -f compose.yaml -f compose.dev.yaml up -d web

# Start/reuse Skriptoteket Vite with protected API traffic proxied to HuleEdu Gateway.
VITE_HULEEDU_AUTH_BASE_URL=http://localhost:8080 VITE_HULEEDU_AUTH_ENTRY_URL=http://localhost:8080/auth/login VITE_DEV_PROXY_TARGET=http://localhost:8080 pdm run fe-dev

# Verify Gateway can resolve the product backend by Docker alias.
docker exec huleedu_api_gateway_service curl -sS -i --max-time 10 http://skriptoteket-web:8000/healthz

# Focused PR-0363 checks.
pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedView.spec.ts src/views/apps/ExamConverterAuthenticatedView.modeRoute.spec.ts src/views/apps/conversionHubModeRoute.spec.ts src/views/apps/ExamConverterAuthenticatedUiInspectionFixtures.spec.ts
pdm run fe-type-check
pdm run fe-lint
pdm run python -m scripts.playwright_pr_0363_conversion_mode_deeplink
pdm run test tests/unit/scripts/test_playwright_script_surface.py
pdm run fe-build
pdm run docs-validate
pdm run handoff-validate
pdm run skills-validate
git diff --check
git -C /Users/olofs_mba/Documents/Repos/skill-repository diff --check
```
## Known Issues / Risks
- Do not start host `pdm run dev`/Uvicorn for Gateway-authenticated backend dev
  tests or browser proof. Gateway app continuation uses Docker DNS
  `skriptoteket-web:8000`, so host Uvicorn reproduces a false failure.
- If Gateway `:8080` appears occupied by Docker while no container publishes
  it, suspect stale Docker Desktop port-proxy state; restart Docker Desktop and
  recreate the affected HuleEdu services before blaming app code.
- `REV-PR-0363` is approved. Keep the Docker-service proof lane intact for
  `PR-0364` and `PR-0365`.
## Next Steps
- Send `REV-PR-0364` to an independent reviewer before implementation, then
  run the approved C2 contract through red-first frontend implementation.
- `PR-0277` remains open for `REV-PR-0277` plus fresh Teams unfurl proof.
