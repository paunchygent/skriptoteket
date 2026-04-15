# Session Handoff
Keep this file updated so the next session can pick up work quickly.
## Editing Rules (do not break structure)
- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines.
- When compacting this file, move non-session-vital history into repo long-term memory at `docs/reference/ref-development-changelog.md` first.
## Snapshot
- Date: 2026-04-15
- Branch: `main` + local changes
- Current lane: `EPIC-28` auth authority cutover is done locally through `ST-28-10` /
  `PR-0264`; next strategic lane is `EPIC-35` launch SEO/indexing review.
- Production: Full Vue SPA.
- Handoff compaction moved the older auth-cutover verification ledger into
  `docs/reference/ref-development-changelog.md`.
## Status
- `PR-0261` implemented direct HuleEdu action anchors/auto-handoff for login, registration,
  forgot-password, reset completion, and email verification, plus the hidden no-side-effect
  diagnostics route `GET /api/v1/diagnostics/huleedu-internal-identity`.
- HuleEdu reran `TASK-0327` live apply against that route and retained final `status=ok` provider
  proof:
  `/Users/olofs_mba/Documents/Repos/huledu-reboot/.artifacts/skriptoteket-lifecycle-proof/dev/skriptoteket-lifecycle-proof-apply-20260413T125336Z.json`.
- HuleEdu runner now accepts the approved sanitized diagnostics shape without requiring raw
  signed-context email or raw `realm_subject_id` in retained signed-context proof.
- `PR-0262` consumes the HuleEdu artifact as upstream provider evidence instead of re-driving the
  real-inbox lifecycle.
- `PR-0262` validates upstream direct-action/session/signed-context evidence, then proves
  Skriptoteket callback continuation, local projection, local role observation, live diagnostics,
  and redaction.
- Retained PR-0262 manifest:
  `.artifacts/playwright-pr-0262-real-lifecycle/local-nonprod/20260413T132801Z/manifest.redacted.json`.
- `PR-0254` now consumes retained HuleEdu `TASK-0326`/`TASK-0327` and Skriptoteket
  `PR-0261`/`PR-0262` manifests through an artifact preflight before any browser work.
- `pdm run pr-0254-auth-cutover` now writes `manifest.redacted.json`, proves the required
  `localhost` lane by default, and retains only sanitized route/assertion summaries plus screenshots.
- Plain `pdm run pr-0254-auth-cutover` now prefers the controlled
  `SKRIPTOTEKET_LIFECYCLE_PROOF_*` account from the HuleEdu dotenv before bootstrap-superuser
  fallback, so the default smoke proves `/editor` contributor RBAC.
- PR-0254 browser proof now includes public Klassrumskartan access, Gateway browser auth entry,
  HuleEdu session authority, `/editor` callback continuation, Gateway-proxied app-continuation,
  local projection/RBAC, CSRF negative/positive write, and shared logout invalidation.
- Shared temporary Playwright backend/Vite helpers now support free backend ports and Vite proxy
  wiring so targeted PR proofs do not collide with the long-running Docker dev stack on 8000/5173.
- `ST-28-12` is done; `PR-0254` localhost proof is green after the logout CSRF fix.
- Frontend `auth.logout()` now treats HuleEdu logout as an unsafe shared-auth write: it sends the
  cached/fetched shared CSRF token, refreshes once on `403`, and accepts HuleEdu `2xx` or `401` as
  logout-complete before clearing local app state.
- Auth-store tests are split into focused bootstrap/state, CSRF, and logout specs so touched test
  files remain under the repo size budget.
- Retained final PR-0254/PR-0263 manifest:
  `.artifacts/playwright-pr-0254-auth-cutover/local-nonprod/20260413T160856Z/manifest.redacted.json`.
- `PR-0263` + `REV-PR-0263` closed the required 127 closeout fix. The approved design treats the
  failure as loopback-origin parity across HuleEdu ceremony/session/CSRF/logout surfaces, while
  keeping protected Skriptoteket `/api` calls Gateway-proxied and avoiding local API auth.
- `PR-0264` is implemented. Skriptoteket now records bounded auth outcome metrics/logs for
  signed-context verification, projection/provisioning outcomes, and local RBAC denials without
  restoring local browser-session metrics.
- `REV-PR-0264` is approved after the 2026-04-15 re-review. The implementation follow-up is
  resolved: RBAC denial recording now happens in the central web `DomainError` boundary, eval-mode
  and draft-lock force-takeover role denials carry role guard metadata, and the new observability
  typing no longer uses `Any` / `cast(...)`.
- `ST-28-10` and `EPIC-28` are marked done. Observability runbooks now describe correlation-id
  triage and HuleEdu Gateway/session handoff for browser-session, CSRF, logout, and provider
  lifecycle failures.
- `PR-0265` is done and ports the HuleEdu mockup-bundle docs-as-code contract into Skriptoteket:
  `docs/mockups/INDEX.md`, typed bundle `README.md` docs, and bundle-local `submissions/` /
  `winner/` folders while preserving existing HTML/SVG preview paths.
- `PR-0261` received production callback remediation: anonymous direct entry to
  `/auth/callback?next=/` now auto-retries HuleEdu login once and then shows explicit
  `Inloggningen slutfördes inte` / `Logga in igen` recovery copy instead of the generic
  auth-entry fallback.
- `PR-0266` consolidated pyproject tooling: Docker dev operations now use
  `pdm run dev-stack <subcommand>`, observability operations use
  `pdm run obs-stack <subcommand>`, and obsolete `dev-*`/`obs-*` variants plus `kill-dev` were
  removed from the script table.
## Verification
- `pdm run db-upgrade` (pass).
- `pdm run docs-validate` (pass after independent `REV-PR-0263` review update).
- `pdm run pytest -q tests/unit/application/auth/test_pr_0262_lifecycle_manifest.py
  tests/unit/web/test_profile_app_continuation_api.py` (pass; 11 tests).
- `pdm run pr-0262-real-lifecycle --huleedu-artifact
  /Users/olofs_mba/Documents/Repos/huledu-reboot/.artifacts/skriptoteket-lifecycle-proof/dev/skriptoteket-lifecycle-proof-apply-20260413T125336Z.json
  --artifact-dir .artifacts/playwright-pr-0262-real-lifecycle/local-nonprod` (pass).
- Manifest inspection: upstream status `ok`, browser callback final path `/editor`, local role
  `contributor`, and all redaction booleans pass; raw proof email/subject/CSRF/context markers
  were absent from the retained manifest.
- `pdm run pytest -q tests/unit/application/auth/test_pr_0262_lifecycle_manifest.py
  tests/unit/web/test_huleedu_identity_context_probe_api.py
  tests/unit/web/test_profile_app_continuation_api.py
  tests/unit/web/test_profile_app_continuation_context_api.py` (pass; 38 tests).
- `pdm run pr-0261-auth-action-matrix` (pass after free-port helper update).
- `pdm run pytest -q tests/unit/application/auth/test_pr_0254_auth_cutover_manifest.py` (pass;
  5 tests).
- `pdm run pytest -q tests/unit/application/auth/test_pr_0262_lifecycle_manifest.py
  tests/unit/application/auth/test_pr_0254_auth_cutover_manifest.py` (pass; 10 tests).
- Real preflight probe against retained artifacts:
  HuleEdu `TASK-0326`, HuleEdu `TASK-0327`, PR-0261, and PR-0262 all returned
  `status=ok` / `validated=true`.
- `pdm run python -m scripts.playwright_pr_0254_auth_cutover --help` (pass).
- `git diff --check` (pass).
- `pdm run lint` (pass).
- `pdm run typecheck` (pass).
- HuleEdu login UI started from sibling repo with
  `pdm run fe-dev -- --host 0.0.0.0 --port 5174`; `http://localhost:5174/login` returned
  `200`, and Gateway `/auth/login?...` redirected to the login UI with the Skriptoteket app/realm.
- Sanitized logout diagnostic before the proof assertion fix: HuleEdu logout returned `200`,
  browser cookies were cleared, and session endpoint returned `200` with unauthenticated payload.
  The proof now accepts HuleEdu `200/authenticated=false` as unauthenticated session state.
- PR-0254 proof-credential rerun passed and retained
  `.artifacts/playwright-pr-0254-auth-cutover/local-nonprod/20260413T154741Z/manifest.redacted.json`.
- `pdm run pytest -q tests/unit/application/auth/test_pr_0254_auth_cutover_config.py
  tests/unit/application/auth/test_pr_0254_auth_cutover_manifest.py` (pass; 8 tests).
- `pdm run ruff check scripts/playwright_pr_0254_auth_cutover.py
  tests/unit/application/auth/test_pr_0254_auth_cutover_config.py` (pass).
- `pdm run ruff format --check scripts/playwright_pr_0254_auth_cutover.py
  tests/unit/application/auth/test_pr_0254_auth_cutover_config.py` (pass).
- Plain `pdm run pr-0254-auth-cutover` passed and retained
  `.artifacts/playwright-pr-0254-auth-cutover/local-nonprod/20260413T154741Z/manifest.redacted.json`.
- `pdm run pr-0254-auth-cutover --include-127-lane --require-127-lane` passed after `PR-0263` and
  retained
  `.artifacts/playwright-pr-0254-auth-cutover/local-nonprod/20260413T160856Z/manifest.redacted.json`.
  Manifest inspection shows both `localhost` and `127` lane summaries `status=ok`.
- Manifest inspection: `status=ok`; all four prerequisites validated; public bootstrap `200`;
  auth entry `/auth/login`; app-continuation `200`; callback final path `/editor`; local role
  `contributor`; missing-CSRF write `403`; CSRF-protected write `200`; logout session status
  `200` with `authenticated=false`; shared session invalidated; redaction checks pass.
- Independent `REV-PR-0263` implementation review updated the retained review record and manually
  inspected the `localhost` + `127` screenshots for visible raw identity/session material.
- `pdm run fe-test -- --run src/api/sharedAuth.spec.ts src/stores/auth.spec.ts
  src/stores/auth.csrf.spec.ts src/stores/auth.logout.spec.ts` (pass; 47 tests, including loopback
  URL parity, logout CSRF header, CSRF fetch-before-logout, stale-CSRF retry, and HuleEdu `200`
  success).
- `pdm run fe-type-check` (pass).
- `pdm run fe-lint` (pass).
- `pdm run docs-validate` (pass for `PR-0264`/`REV-PR-0264` planning docs).
- `pdm run pytest -q tests/unit/observability/test_auth_outcomes.py
  tests/unit/web/test_profile_app_continuation_api.py
  tests/unit/web/test_profile_app_continuation_context_api.py
  tests/unit/web/test_observability_routes.py
  tests/unit/web/test_error_handler_middleware.py` (pass; 48 tests, including non-dependency RBAC
  denial coverage).
- `pdm run pytest -q tests/unit/observability/test_auth_outcomes.py
  tests/unit/web/test_error_handler_middleware.py tests/unit/web/test_profile_app_continuation_api.py
  tests/unit/web/test_editor_inline_completion_api.py
  tests/unit/web/test_editor_edit_ops_preview_apply_api.py
  tests/unit/application/scripting/handlers/test_draft_lock_handler.py` (pass; 38 tests).
- `pdm run pytest -q tests/unit/web -x` (pass; 294 tests).
- `pdm run pytest -q tests/unit/observability` (pass; 49 tests).
- Focused `pdm run ruff check` on touched auth outcome implementation/test files (pass).
- Live backend check after review follow-up: `docker compose up -d db`, `pdm run db-upgrade`,
  `pdm run dev`; `curl http://127.0.0.1:8000/healthz` returned `200` with healthy DB, and
  `POST /api/v1/editor/completions` with `X-Skriptoteket-Eval: 1` returned expected `401`
  `missing_internal_identity_headers` through the live app/error boundary.
- `pdm run docs-validate` (pass for `PR-0264` implementation closeout).
- `pdm run typecheck` (pass; 993 source files).
- `pdm run lint` (pass; includes format, Ruff, migration coverage, hazard guard).
- `git diff --check` (pass).
- `pdm run pr-0254-auth-cutover --include-127-lane --require-127-lane` (pass; retained
  `.artifacts/playwright-pr-0254-auth-cutover/local-nonprod/20260415T092404Z/manifest.redacted.json`).
- `pdm run docs-validate` (pass for `PR-0265` mockup bundle docs-as-code port).
- `pdm run fe-test -- --run src/views/AuthLoginView.spec.ts src/components/auth/AuthLoginPanel.spec.ts`
  (pass; 10 tests).
- `pdm run pr-0261-auth-action-matrix` (pass; manifest now includes anonymous callback retry and
  explicit recovery assertions for `/auth/callback?next=/`).
- `pdm run fe-type-check`, `pdm run fe-lint`, `pdm run lint`, `pdm run typecheck`, and
  `pdm run docs-validate` (pass for `PR-0261` callback remediation).
- `PR-0266` checks passed: focused dev/obs stack dispatch pytest, PR-0254 provider preflight
  pytest, `scripts.dev_stack --help`, `scripts.obs_stack --help`, focused Ruff check/format,
  `pdm run docs-validate`, pyproject stale-alias scan, and `git diff --check`.
- `git diff --check` (pass).
## How to Run
```bash
pdm run docs-validate
pdm run lint
pdm run typecheck
pdm run fe-type-check
pdm run fe-lint
pdm run pr-0261-auth-action-matrix
pdm run pr-0262-real-lifecycle --huleedu-artifact /Users/olofs_mba/Documents/Repos/huledu-reboot/.artifacts/skriptoteket-lifecycle-proof/dev/skriptoteket-lifecycle-proof-apply-20260413T125336Z.json --artifact-dir .artifacts/playwright-pr-0262-real-lifecycle/local-nonprod
pdm run pr-0254-auth-cutover
pdm run pr-0254-auth-cutover --include-127-lane --require-127-lane
pdm run pytest -q tests/unit/application/auth/test_pr_0262_lifecycle_manifest.py tests/unit/web/test_huleedu_identity_context_probe_api.py tests/unit/web/test_profile_app_continuation_api.py tests/unit/web/test_profile_app_continuation_context_api.py
```
## Known Issues / Risks
- Do not reintroduce app-local browser auth, browser-to-Identity calls, raw signed-context echo
  routes, or retained token/session artifacts.
- The PR-0262 proof uses transient raw session subject/email from the HuleEdu artifact only to seed
  and verify local projection; retained Skriptoteket artifacts must stay sanitized.
- For `PR-0264`, keep metric labels enum-like and bounded. Never label by user id, email, raw
  realm subject id, raw URL, signed header payload, cookie, CSRF token, or exception text.
## Next Steps
- Review `REV-EPIC-35`; after approval, start `ST-35-01` / `ST-35-02` to freeze canonical public
  host policy and repair crawler file/status semantics for launch indexing.
