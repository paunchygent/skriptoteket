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
- Date: 2026-04-13
- Branch: `main` + local changes
- Current lane: `PR-0260` remediation is accepted; next cross-repo gate is HuleEdu
  `TASK-0327` before Skriptoteket `PR-0261` / `PR-0262` and final `PR-0254`.
- Production: Full Vue SPA.
- Handoff compaction moved previous auth-cutover history into `docs/reference/ref-development-changelog.md`.
## Status
- `ST-28-06`, `ST-28-07`, `ST-28-08`, and `ST-28-09` are done under `EPIC-28`.
- `ST-28-04` / `PR-0254` is ready as the final realm-aware Docker/operator proof lane.
- `PR-0258` replaces the temporary `(auth_provider, external_id)` bridge with
  `identity_projections(product_identity_realm, realm_subject_id)` and removes `users.external_id`.
- Migration `e7b3a9c4d1f2` creates `identity_projections` and `identity_projection_events`,
  preflights/backfills old HuleEdu rows into `huleedu_school`, and fails ambiguous provider-subject
  data before dropping the legacy field.
- App continuation now requires signed `active_app=skriptoteket`, accepted realm, and
  `realm_subject_id`; invalid product context remains a generic auth ceremony/context error.
- First-login provisioning requires signed `email` and strict `email_verified=true`; newly
  provisioned Skriptoteket users default to local role `user`.
- Matching email without an explicit link fails closed into linking/provisioning-required UX; local
  contributor/admin/superuser remain app-local promotions.
- Runtime `identity_projection_events` now include request correlation ids when available.
- First-login user/projection creation uses no-conflict repository inserts and DB-backed recovery
  tests for same-subject, same-email, and projection unique-conflict races.
- Public "Logga in" actions open the HuleEdu login ceremony directly; `/auth/login?next=...`
  remains only as an auto-handoff/fallback route.
- HuleEdu `TASK-0325` is scaffolded as the provider-owned local shared-auth Gateway lane for
  `PR-0254`: local/non-prod exact loopback origins, HuleEdu login UI on `5174`, protected
  Skriptoteket `/api` traffic through Gateway, and local-only Gateway public-key sharing.
  Browser-visible auth URLs use `http://localhost:8080`; host-run Vite may use
  `VITE_DEV_PROXY_TARGET=http://localhost:8080`, while the normal Docker frontend service uses
  `VITE_DEV_PROXY_TARGET=http://huleedu_api_gateway_service:8080` on `hule-network` and
  `VITE_DEV_BACKEND_PROXY_TARGET=http://skriptoteket_web:8000` so public
  `/api/v1/public/...` routes stay direct to Skriptoteket without a HuleEdu session.
- `PR-0259` implemented public Klassrumskartan Smart `Slumpa` snapshot commits: the public seating
  and grouping Smart flows now commit the visible pre-run workspace and accepted solver workspace
  directly to the browser-owned guest snapshot before success, acknowledge the draft autosave lane,
  and sanitize raw revision-conflict diagnostics to `Det gick inte att slumpa just nu. Klicka på
  Slumpa igen.`
- Shared UI/frontend skills now encode the copy rule from PR-0259: user-facing recovery copy should
  describe the failed visible action and next visible action, not internal state/revision plumbing.
- New 2026-04-13 auth-cutover planning decision: do not bulk import old fake alpha
  education-domain Skriptoteket users as a launch blocker. Focus on provider-owned bootstrap
  identities, real controlled-account lifecycle proof, local projections, and local roles.
- HuleEdu `TASK-0326` is done and deployed at merge commit `92419293`; Hemma production
  bootstrap/export proof verified `skriptoteket-proof-user@hule.education`,
  `skriptoteket-proof-admin@hule.education`, and
  `skriptoteket-proof-superuser@hule.education`.
- Skriptoteket `ST-28-11` / `PR-0260` are done and approved after remediation: production code
  consumes sanitized HuleEdu subject exports into local HuleEdu-owned users,
  `identity_projections`, and `User.role` through a durable subject-export contract/consumer plus
  operator CLI with strict versioned input and durable blocked-mapping audit events.
- Task/proof wording stays in backlog docs, tests, fixtures, runbooks, and artifacts; `src/`
  code is named for the reusable subject-export import/projection capability.
- HuleEdu `TASK-0327` is ready/current; it owns real-inbox
  register/verify/login/forgot/reset/direct-action proof.
- Skriptoteket `ST-28-12` / `PR-0261` / `PR-0262` remain blocked until HuleEdu `TASK-0327`
  is done.
- Direct-action auth links are now an explicit contract in `ST-28-12`, `PR-0261`, `PR-0262`, and
  `PR-0254`: login, create-account, forgot-password, verification, and reset links must land
  directly on the requested action page. Generic HuleEdu pages are fallback-only.
- `PR-0254` remains the final cross-app proof, now gated behind HuleEdu `TASK-0325` through
  `TASK-0327` plus Skriptoteket `PR-0261` / `PR-0262`; `REV-PR-0254` is approved.
## Verification
- `pdm run pytest -q tests/unit/web/test_profile_app_continuation_api.py tests/unit/web/test_profile_app_continuation_context_api.py tests/unit/web/test_profile_app_continuation_dependencies_api.py` (pass; 34 tests).
- `pdm run pytest -q tests/integration/application/test_huleedu_app_projection_concurrency.py` (pass; 3 tests).
- `pdm run pytest -q tests/integration/test_migration_e7b3a9c4d1f2_idempotent.py -m docker --override-ini addopts=''` (pass; 4 tests).
- `pdm run python -m scripts.check_migration_test_coverage` (pass; 67 revisions covered).
- `pdm run fe-gen-api-types` (pass).
- `pdm run fe-test -- --run src/router/index.spec.ts src/views/AuthLoginView.spec.ts src/components/auth/AuthLoginPanel.spec.ts src/components/layout/LandingLayout.spec.ts src/views/HomeView.spec.ts src/views/apps/ClassroomPlannerGuestOverviewView.spec.ts src/composables/auth/authEntryNavigation.spec.ts src/stores/auth.spec.ts` (pass; 66 tests).
- `pdm run typecheck`, `pdm run lint`, `pdm run fe-type-check`, and `pdm run fe-lint` (pass).
- `ARTIFACTS_ROOT=.artifacts/local-tool-artifacts pdm run pr-0258-auth-projection --start-backend --start-vite --gateway-base-url http://127.0.0.1:8000` (pass; artifacts in `.artifacts/playwright-pr-0258-auth-projection/`, including `login-auto-handoff.png`).
- `pdm run docs-validate`, `git diff --check`, and `pdm run precommit-run` (pass).
- Docker dev logs inspected for public Smart seating mismatch: `/seating/smart-run` returned `200`
  then later `409 CONFLICT` on 2026-04-12, confirming backend guard sees stale submitted guest
  snapshot revision after a prior accepted run.
- `pdm run docs-validate` after approving `REV-PR-0259` (pass).
- `PR-0259` / `REV-PR-0259` tightened to cover grouping root-cause parity and sanitized public
  Smart revision-conflict toast copy; `pdm run docs-validate` passed after the update.
- `pdm run fe-test -- --run src/views/apps/usePublicSmartSeatingRun.spec.ts src/views/apps/usePublicSmartGroupingRun.spec.ts src/views/apps/classroomPlannerGuestDraftWorkspace.spec.ts src/views/apps/useDraftPersistenceLane.spec.ts` (pass; 14 tests).
- `pdm run pytest -q tests/unit/application/apps/classroom_planner/test_public_smart_run.py` (pass; 6 tests).
- `pdm run fe-type-check`, `pdm run fe-lint`, `pdm run docs-validate`, and `git diff --check`
  (pass).
- Live public-route proof on Docker dev stack at `http://127.0.0.1:5173/public/apps/classroom.group-seating-studio`:
  seeded a public guest snapshot, clicked Smart `Slumpa` twice in `Sittplatser` and twice in
  `Grupper`; browser observed `/seating/smart-run` `200, 200` and `/grouping/smart-run` `200, 200`,
  no raw `Draft revision mismatch` visible. Artifacts:
  `.artifacts/pr-0259-public-smart-proof/`.
- `docker logs --tail 40 skriptoteket_web` for the same live proof shows two `200` seating
  `/smart-run` responses and two `200` grouping `/smart-run` responses at
  `2026-04-12T21:12:45Z`-`2026-04-12T21:12:46Z`; no 409 appears in that proof tail.
- TASK-0325/PR-0254 local shared-auth live proof after Docker frontend recreate:
  persisted script `pdm run pr-0254-auth-cutover` passed. It first asserts public
  Klassrumskartan bootstrap on `http://localhost:5173/public/apps/classroom.group-seating-studio`
  stays `200` before login, then clicks `Logga in`, confirms the anchor targets
  `http://localhost:8080/auth/login`, observes HuleEdu login on `http://localhost:5174/login`,
  and verifies `/api/v1/profile/app-continuation` `200` with authenticated nav visible.
  Artifacts: `.artifacts/playwright-pr-0254-auth-cutover/`.
- Auth bootstrap/lifecycle docs scaffold validation: Skriptoteket `pdm run docs-validate` and
  `git diff --check` passed. HuleEdu `pdm run run-local-pdm docs-sync`, `docs-validate`,
  `validate-docs`, `validate-backlog`, `index-backlog`, final `docs-validate`, and
  `git diff --check` passed.
- Direct-action link amendment validation: Skriptoteket `pdm run docs-validate` and
  `git diff --check` passed; HuleEdu `docs-sync`, `docs-validate`, `validate-docs`,
  `validate-backlog`, and `git diff --check` passed; skill-repository `pdm run docs-validate` and
  `git diff --check` passed.
- `REV-PR-0254` approval validation: `pdm run docs-validate`, `git diff --check`, and
  `.agents/handoff.md` line-count check passed.
- `REV-PR-0260` / `REV-PR-0261` re-review amendment validation:
  `pdm run docs-validate`, `git diff --check`, and `.agents/handoff.md` line-count check
  passed (`154` lines).
- `REV-PR-0262` requested-change remediation: updated `PR-0262` and review record with exact
  prerequisite gates, identity/projection assertions, `manifest.redacted.json` artifact contract,
  future `scripts/playwright_pr_0262_real_lifecycle.py` / `pdm run pr-0262-real-lifecycle`
  command, HuleEdu local non-production lane, and re-review request; `pdm run docs-validate`,
  `git diff --check`, and `.agents/handoff.md` line-count check passed.
- `PR-0260` remediation verification: focused schema/projection tests, DB-backed audit
  integration, and CLI summary tests passed (`26` tests); local CLI dry-run against
  `tests/fixtures/identity/huleedu_subject_export_v1.json` now prints
  `would_create_users=3`, `would_create_projections=3`, `would_update_users=0` and writes the same
  sanitized counters under `.artifacts/skriptoteket-auth-bootstrap/`.
- `REV-PR-0260` remediation re-review accepted the stricter export boundary and durable
  blocked-audit behavior. Dry-run summary counter polish is now implemented; `pdm run typecheck`,
  `pdm run lint`, `pdm run docs-validate`, `git diff --check`, and `.agents/handoff.md`
  line-count check passed (`161` lines).
## How to Run
```bash
pdm run docs-validate
pdm run lint
pdm run typecheck
pdm run fe-type-check
pdm run fe-lint
pdm run pytest -q tests/unit/web/test_profile_app_continuation_api.py tests/unit/web/test_profile_app_continuation_context_api.py tests/unit/web/test_profile_app_continuation_dependencies_api.py
pdm run pytest -q tests/integration/application/test_huleedu_app_projection_concurrency.py
pdm run pytest -q tests/integration/test_migration_e7b3a9c4d1f2_idempotent.py -m docker --override-ini addopts=''
ARTIFACTS_ROOT=.artifacts/local-tool-artifacts pdm run pr-0258-auth-projection --start-backend --start-vite --gateway-base-url http://127.0.0.1:8000
```
## Known Issues / Risks
- `PR-0254` still owns the final Docker/operator cross-app proof, but should now wait for
  HuleEdu `TASK-0327`, Skriptoteket `PR-0261`, and Skriptoteket `PR-0262` implementation.
- `PR-0259` live proof used a seeded public guest snapshot to focus the Smart `Slumpa` regression;
  it did not rerun the full public roster/template authoring path.
- Local full-auth ceremony livetests must consume HuleEdu `TASK-0325`: use a local or
  non-production HuleEdu Gateway whose allowed return origins include exact dev origins such as
  `http://localhost:5173` and `http://127.0.0.1:5173`; keep public production strict. Do not mix
  `localhost` and `127.0.0.1` within one browser proof.
- Do not reintroduce app-local browser auth or direct browser-to-Identity calls.
## Next Steps
- Implement HuleEdu `TASK-0327`, followed by Skriptoteket `PR-0261`, Skriptoteket
  `PR-0262`, and final `PR-0254`.
- Follow with `ST-28-10` auth outcome observability for gateway/session, realm, lifecycle,
  projection, and local RBAC outcomes.
