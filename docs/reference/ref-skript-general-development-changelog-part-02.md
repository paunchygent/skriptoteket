---
type: reference
id: REF-SKRIPT-GENERAL-development-changelog-PART-02
title: Development changelog — part 02
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
root: REF-SKRIPT-GENERAL-development-changelog
part: 2
---

- Review `PR-0231` implementation locally against `REV-PR-0231`, then docs-close the PR/story records if the code review stays green.
- Execute `PR-0232` next as the remaining `ST-32-06` guest-mode bridge slice: guest local undo/redo parity, direct-download export, and account-only history/recovery affordance polish.
- Return to `TASK-SKRIPT-29-11-02` after the guest-mode bridge slices if the planner-toolbar overflow lane is still intended to stay open.
- `REV-PR-0231` is now approved, so `PR-0231` / `PR-0232` can move from planning into implementation without reopening the guest/auth boundary unless the implementation itself discovers a new seam.
- Keep the implementation thin on any follow-up edits: no local deploy-logic duplication, no hidden repo-path discovery, and no second structured log lane beyond the current raw-log + filtered-monitor split.
- Debug the authenticated guest-upgrade import prompt separately from `PR-0226`; the planner shell/layout work is verified independently of that modal failure.
- Decide whether `ST-SKRIPT-29-11` should now be closed as done or whether more dense-control follow-up remains beyond the implemented `PR-0224` / `TASK-SKRIPT-29-11-01` / `PR-0226` set.

### Source: 2026-04-12 PR-0258 handoff compaction dump

Moved from `.codex/handoff.md` during `PR-0258` cleanup so the session handoff stays under the
repo line-count limit.

### Previous Status

- `REV-EPIC-28` approved the auth-cutover spine. `ADR-SKRIPT-0076`, `EPIC-28`, and `ST-28-01` through
  `ST-28-05` remain governing context for the HuleEdu-owned browser session cutover.
- HuleEdu accepted ADR-SKRIPT-0039, completed `TASK-0308`, and publicly proved shared browser-session
  authority after prod redeploy to `432b25ed`: auth readiness passed with `huleedu_session` /
  `huleedu_csrf`, and WebSocket origin admission accepted `https://skriptoteket.hule.education`.
- `PR-0250` / `ST-28-05` shipped as provider conformance ingest; `PR-0251` consumed shared
  `/v1/auth/session` and CSRF client behavior; `REV-PR-0251` later approved after `PR-0255`.
- `PR-0255` shipped signed HuleEdu `InternalIdentityContextV1` verification and temporary
  `(auth_provider, external_id)` projection resolution before the realm-aware migration.
- `PR-0252` shipped `/auth/login?next=...` interruption and return-to-origin behavior on the
  shared session model.
- `PR-0253` / `ST-28-03` shipped local browser-auth authority retirement, removed local session
  surfaces, and preserved missing-projection fail-closed UX.
- Product identity realm direction was recorded in
  `docs/reference/ref-hule-education-product-identity-realms-and-skriptoteket-standalone-identity.md`
  and frozen by `ADR-SKRIPT-0083` / `REV-ST-28-06`.
- `ST-28-07` / `PR-0256` shipped the Hule Education-hosted Skriptoteket login ceremony after
  HuleEdu `TASK-0313` / `TASK-0314`.
- `ST-28-08` / `PR-0257` shipped standalone registration, password reset, and email verification
  handoff surfaces after HuleEdu `TASK-0318`.
- `REV-PR-0258` approved the realm-aware projection/provisioning contract: dedicated projection
  table, HuleEdu legacy backfill, concrete signed email/email_verified claims, UoW idempotent
  provisioning, projection audit events, no email-inferred linking, and local/non-prod Gateway
  proof.

### Previous Verification

- Repeated `pdm run docs-validate` and `git diff --check` passes recorded the docs gates for
  `PR-0250` through `REV-PR-0258` planning/review closeouts.
- `PR-0251` / `PR-0255` frontend gates included `pdm run fe-test -- --run
  src/api/sharedAuth.spec.ts src/stores/auth.spec.ts src/api/client.spec.ts`, `pdm run
  fe-type-check`, and `pdm run fe-lint`.
- `PR-0255` backend/live proof included `pdm run pytest -q
  tests/unit/web/test_profile_app_continuation_api.py`, `pdm run typecheck`, `pdm run lint`,
  `docker compose up -d db`, `pdm run db-upgrade`, and `pdm run pr-0255-auth-bootstrap
  --start-backend --start-vite`.
- `PR-0252` proof included focused auth-entry Vitest suites, `pdm run python -m py_compile
  scripts/_playwright_huleedu_auth.py scripts/playwright_pr_0252_auth_return_to_origin.py
  scripts/playwright_pr_0255_auth_bootstrap.py`, `pdm run db-upgrade`, and
  `ARTIFACTS_ROOT=.artifacts/local-tool-artifacts pdm run pr-0252-auth-return --start-backend
  --start-vite`.
- `PR-0253` proof included focused backend route/contract tests, frontend auth/router tests,
  `pdm run pytest tests/unit/web -q`, Docker migration coverage for `c1d2e3f4a5b6`,
  `pdm run python -m scripts.check_migration_test_coverage`, and
  `ARTIFACTS_ROOT=.artifacts/local-tool-artifacts pdm run pr-0253-auth-retirement --start-backend
  --start-vite`.
- `ST-28-06` / `ADR-SKRIPT-0083` proof included `pdm run docs-validate` and `git diff --check`.
- `PR-0256` proof included focused auth ceremony Vitest suites, `pdm run test
  tests/unit/web/test_profile_app_continuation_api.py`, `pdm run fe-type-check`, `pdm run
  typecheck`, `pdm run fe-lint`, `pdm run lint`, and `pdm run python -m
  scripts.playwright_pr_0256_auth_ceremony --start-backend --start-vite`.
- `PR-0257` proof included focused lifecycle Vitest suites, `pdm run pytest -q
  tests/unit/web/test_pr_0253_auth_retirement_contracts.py`, `pdm run python -m py_compile
  scripts/playwright_pr_0257_auth_lifecycle.py`, `pdm run python -m
  scripts.playwright_pr_0257_auth_lifecycle --start-vite`, `pdm run fe-type-check`, `pdm run
  fe-lint`, `pdm run typecheck`, `pdm run lint`, `pdm run docs-validate`, and `git diff --check`.

### Previous Next Steps

- After `REV-PR-0258` approval, `PR-0258` was the next implementation lane.
- `PR-0254` remained the final Docker/operator cross-app proof after `ST-28-09`.

### Source: 2026-04-13 PR-0262 handoff compaction dump

Moved from `.codex/handoff.md` while closing `ST-28-12` so the session handoff stays under the
repo line-count limit.

### Previous Status

- `ST-28-06`, `ST-28-07`, `ST-28-08`, and `ST-28-09` were done under `EPIC-28`.
- `PR-0258` replaced the temporary `(auth_provider, external_id)` bridge with
  `identity_projections(product_identity_realm, realm_subject_id)` and removed `users.external_id`.
- App continuation requires signed `active_app=skriptoteket`, accepted realm, and
  `realm_subject_id`; invalid product context remains a generic auth ceremony/context error.
- First-login provisioning requires signed `email` and strict `email_verified=true`; newly
  provisioned Skriptoteket users default to local role `user`.
- Matching email without an explicit link fails closed into linking/provisioning-required UX; local
  contributor/admin/superuser remain app-local promotions.
- HuleEdu `TASK-0325` scaffolded the local shared-auth Gateway lane for `PR-0254` with
  Skriptoteket SPA on `5173`, Gateway on `8080`, HuleEdu login UI on `5174`, protected
  Skriptoteket `/api` traffic through Gateway, and local-only signing-key sharing.
- HuleEdu `TASK-0326` was done and deployed at merge commit `92419293`; Hemma production
  bootstrap/export proof verified the Skriptoteket proof user/admin/superuser accounts.
- Skriptoteket `ST-28-11` / `PR-0260` were done and approved after remediation: production code
  consumes sanitized HuleEdu subject exports into local users, `identity_projections`, and
  `User.role`, with strict versioned input and durable blocked-mapping audit events.
- HuleEdu `REV-TASK-0327-01` was approved, then HuleEdu `TASK-0327` reran live apply against the
  `PR-0261` Skriptoteket probe route and retained a final `status=ok` artifact.
- `PR-0261` implemented direct-action auth URLs, auto-handoff lifecycle compatibility routes, and
  the hidden no-side-effect sanitized diagnostics route.
- `PR-0262` implemented the retained Skriptoteket-side lifecycle proof by consuming the HuleEdu
  artifact, validating sanitized claims, proving callback continuation, local projection, local
  role observation, and redaction.

### Previous Verification

- `pdm run fe-gen-api-types` (pass during PR-0261).
- `pdm run fe-test -- --run src/router/index.spec.ts src/views/AuthLoginView.spec.ts
  src/components/auth/AuthLoginPanel.spec.ts src/components/layout/LandingLayout.spec.ts
  src/views/HomeView.spec.ts src/views/apps/ClassroomPlannerGuestOverviewView.spec.ts
  src/composables/auth/authEntryNavigation.spec.ts src/stores/auth.spec.ts` (pass; 66 tests).
- `pdm run typecheck`, `pdm run lint`, `pdm run fe-type-check`, and `pdm run fe-lint` (pass
  during the auth-cutover chain).
- `ARTIFACTS_ROOT=.artifacts/local-tool-artifacts pdm run pr-0258-auth-projection
  --start-backend --start-vite --gateway-base-url http://127.0.0.1:8000` (pass; artifacts in
  `.artifacts/playwright-pr-0258-auth-projection/`).
- `pdm run pr-0261-auth-action-matrix` (pass; actions=5 and sanitized manifest under
  `.artifacts/playwright-pr-0261-auth-action-matrix/`).
- `pdm run pr-0262-real-lifecycle --huleedu-artifact
  <HuleEdu retained lifecycle-proof artifact>
  --artifact-dir .artifacts/playwright-pr-0262-real-lifecycle/local-nonprod` (pass; manifest at
  `.artifacts/playwright-pr-0262-real-lifecycle/local-nonprod/20260413T132801Z/manifest.redacted.json`).
- Focused backend/proof tests passed:
  `pdm run pytest -q tests/unit/application/auth/test_pr_0262_lifecycle_manifest.py
  tests/unit/web/test_huleedu_identity_context_probe_api.py
  tests/unit/web/test_profile_app_continuation_api.py
  tests/unit/web/test_profile_app_continuation_context_api.py` (38 tests).

### Previous Next Steps

- `PR-0254` is now the next auth-cutover proof lane.
- `ST-28-10` follows with auth outcome observability for gateway/session, realm, lifecycle,
  projection, and local RBAC outcomes.

### Source: 2026-04-16 TASK-0376 handoff compaction dump

Moved from `.codex/handoff.md` while closing HuleEdu TASK-0376 live production proof so the
session handoff stays under the repo line-count limit.

### Previous Status

- `PR-0254`, `PR-0261`, `PR-0262`, `PR-0263`, and `PR-0264` completed the local HuleEdu
  browser-session cutover, lifecycle proof, loopback parity remediation, and auth outcome
  observability work for `EPIC-28`.
- `ST-28-10` and `EPIC-28` were marked done after signed-context verification, projection,
  provisioning, and local RBAC metrics/logging landed.
- `PR-0265` ported the HuleEdu mockup-bundle docs-as-code contract into Skriptoteket.
- `PR-0266` consolidated pyproject dev/observability tooling around `pdm run dev-stack` and
  `pdm run obs-stack`.
- `PR-0267` / `PR-0268` implemented launch/SEO public route hardening, and `PR-0269` added the
  search-operations runbook.
- Protected Skriptoteket app APIs must use `https://api.hule.education/api/...`; direct protected
  calls to `https://skriptoteket.hule.education/api/...` bypass HuleEdu Gateway signing.

### Previous Verification

- Auth-cutover and lifecycle proofs retained sanitized manifests under
  `.artifacts/playwright-pr-0254-auth-cutover/`, `.artifacts/playwright-pr-0261-auth-action-matrix/`,
  and `.artifacts/playwright-pr-0262-real-lifecycle/`.
- Focused auth, observability, web, frontend, docs, lint, typecheck, and browser proof commands
  listed in the previous handoff passed for their respective PRs.
- SEO lane verification passed with focused pytest/Ruff, frontend checks, docs validation,
  `git diff --check`, temp curl checklist, PR-0268 Playwright proof, and diagnostics closeout.

## Decisions And Interpretation

The source contains no separate decision ledger; interpretation remains bounded by the recorded source material.
