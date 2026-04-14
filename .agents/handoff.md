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
- Date: 2026-04-14
- Branch: `main` + local changes
- Current lane: `ST-28-10` / `PR-0264` auth outcome observability planning is open; `PR-0264`
  is review-ready and blocked from implementation until `REV-PR-0264` is approved.
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
- `PR-0264` now defines the first `ST-28-10` slice: Skriptoteket-owned auth outcome logs/metrics
  for signed-context verification, app-continuation/projection, provisioning-required/linking
  outcomes, local RBAC decisions, and correlation/runbook handoff to HuleEdu Gateway/session logs.
- `REV-PR-0264` is pending. Do not implement auth observability code until the review approves the
  signal contract and confirms no local browser-session metric is being reintroduced.
- `PR-0265` is done and ports the HuleEdu mockup-bundle docs-as-code contract into Skriptoteket:
  `docs/mockups/INDEX.md`, typed bundle `README.md` docs, and bundle-local `submissions/` /
  `winner/` folders while preserving existing HTML/SVG preview paths.
- `PR-0261` received production callback remediation: anonymous direct entry to
  `/auth/callback?next=/` now auto-retries HuleEdu login once and then shows explicit
  `Inloggningen slutfördes inte` / `Logga in igen` recovery copy instead of the generic
  auth-entry fallback.
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
- `pdm run docs-validate` (pass for `PR-0265` mockup bundle docs-as-code port).
- `pdm run fe-test -- --run src/views/AuthLoginView.spec.ts src/components/auth/AuthLoginPanel.spec.ts`
  (pass; 10 tests).
- `pdm run pr-0261-auth-action-matrix` (pass; manifest now includes anonymous callback retry and
  explicit recovery assertions for `/auth/callback?next=/`).
- `pdm run fe-type-check`, `pdm run fe-lint`, `pdm run lint`, `pdm run typecheck`, and
  `pdm run docs-validate` (pass for `PR-0261` callback remediation).
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
  routes, retained token/session artifacts, or direct backend shortcuts for protected `/api`.
- Do not reintroduce app-local browser auth, browser-to-Identity calls, raw signed-context echo
  routes, or retained token/session artifacts.
- The PR-0262 proof uses transient raw session subject/email from the HuleEdu artifact only to seed
  and verify local projection; retained Skriptoteket artifacts must stay sanitized.
- For `PR-0264`, keep metric labels enum-like and bounded. Never label by user id, email, raw
  realm subject id, raw URL, signed header payload, cookie, CSRF token, or exception text.
## Next Steps
- Review `REV-PR-0264`; after approval, implement the narrow Skriptoteket-owned auth outcome
  recorder/metrics/logs and update the observability runbooks.
