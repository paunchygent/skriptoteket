---
type: task
id: TASK-SKRIPT-REP-0023
title: ST-28-04 local auth-edge bootstrap preflight
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_required
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: user closure 2026-07-31
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
- Given Skriptoteket local browser login is HuleEdu-owned, when a developer runs authenticated
  live proof locally, then the proof first verifies the required HuleEdu auth-edge
  services instead of calling the retired `POST /api/v1/auth/login` endpoint.
- Given `.env` contains `BOOTSTRAP_SUPERUSER_EMAIL` and `BOOTSTRAP_SUPERUSER_PASSWORD`,
  when authenticated local browser proof runs, then HuleEdu login accepts those credentials
  and Skriptoteket resolves the resulting Gateway-signed context to a local projected
  `superuser`.
- Given local dev credentials must be durable across the HuleEdu provider and Skriptoteket
  consumer stacks, when the local `.env` files and examples are reconciled, then both
  repos use `superuser@local.dev` / `superuser-password` as the single browser-bootstrap
  superuser account for local-only proof.
- 'Given role-specific proof needs more than the superuser bootstrap account, when
  the auth-edge proof matrix is prepared, then HuleEdu exports and Skriptoteket consumes
  deterministic local proof identities for every active Skriptoteket RBAC tier: `user`,
  `contributor`, `admin`, and `superuser`.'
- Given HuleEdu owns credential truth, when the preflight evaluates the bootstrap
  identity, then it never verifies the `.env` password against Skriptoteket's local
  password hash and never treats a Skriptoteket-local password user as browser-login
  authority.
- Given Skriptoteket owns app-local authorization truth, when app-continuation resolves
  the signed context, then the proof verifies `active_app=skriptoteket`, accepted
  product realm plus `realm_subject_id`, an `identity_projections` mapping, active
  verified local user state, and local `role=superuser`.
- Given the bootstrap email already exists as a Skriptoteket-local password-owner
  user without the required HuleEdu projection, when preflight runs, then it fails
  closed with `bootstrap_identity_conflict` and instructs the operator to run governed
  subject-export/projection bootstrap or reset the local dev DB.
- Given local proof must cover both loopback origins, when closeout runs, then the
  retained auth-cutover proof covers both `localhost:5173 -> localhost:8080 -> localhost:5174
  -> localhost:5173` and `127.0.0.1:5173 -> 127.0.0.1:8080 -> 127.0.0.1:5174 -> 127.0.0.1:5173`.
- Given the HuleEdu local auth edge is missing, not on `hule-network`, not using the
  trusted Gateway signing key, or not seeded with the `.env` bootstrap credentials,
  when preflight runs, then it fails closed with an operator-readable diagnostic and
  does not suggest local Skriptoteket password login.
- Given public Skriptoteket routes do not require HuleEdu auth, when the new preflight
  is absent or fails, then public/share proofs remain allowed and the docs distinguish
  them from authenticated/protected live proofs.
- Given the implementation changes command surfaces or local proof docs, when closeout
  runs, then README/runbook/skill references and `.codex/handoff.md` no longer contain
  runnable-looking stale local login recipes.
---

## Context

## Impact And Escalation

The source task is repository-scoped; impact and escalation remain bounded by the retained source contract.


### Problem

`BOOTSTRAP_SUPERUSER_EMAIL` and `BOOTSTRAP_SUPERUSER_PASSWORD` are currently
ambiguous local facts. In the retired local-auth model they could describe a
Skriptoteket password user. In the current shared-auth model, they can support
browser proof only when HuleEdu Identity owns the credential and Gateway signs
the downstream context consumed by Skriptoteket.

The trap is that a valid Skriptoteket-local password hash does not prove the
current browser login contract. The retired local endpoint
`POST /api/v1/auth/login` correctly returns `405`; authenticated browser proof
must enter through the HuleEdu local Gateway/login UI/session lane.

### Contract

Split "bootstrap account" into two owned facts:

1. HuleEdu owns credential truth.
   `BOOTSTRAP_SUPERUSER_EMAIL` / `BOOTSTRAP_SUPERUSER_PASSWORD` may be used for
   local browser proof only when HuleEdu Identity is seeded with that account
   through a governed provider-side seed scope. The password is verified by the
   HuleEdu login ceremony, never by Skriptoteket.
2. Skriptoteket owns app-local authorization truth.
   Skriptoteket verifies only Gateway-signed context, accepted product realm
   and `realm_subject_id`, `identity_projections`, active verified local user
   state, and local `role=superuser`.

PR-0283 must prove the join between those facts through Gateway. It must not
revive local password identity, introduce a compatibility bridge, auto-link a
legacy local user, or treat a local password hash as browser proof.

### Local Dev Identity Set

The local development identity set should be deterministic and human-usable:

| Purpose | Stable account key | Email | Password source | Skriptoteket role |
|---------|--------------------|-------|-----------------|-------------------|
| Browser-bootstrap and RBAC superuser | `skriptoteket-proof-superuser` | `superuser@local.dev` | `BOOTSTRAP_SUPERUSER_PASSWORD=superuser-password` | `superuser` |
| RBAC proof user | `skriptoteket-proof-user` | `skriptoteket-proof-user@local.dev` | Provider-owned proof-account secret, local default may reuse `BOOTSTRAP_SUPERUSER_PASSWORD` | `user` |
| RBAC proof contributor | `skriptoteket-proof-contributor` | `skriptoteket-proof-contributor@local.dev` | Provider-owned proof-account secret, local default may reuse `BOOTSTRAP_SUPERUSER_PASSWORD` | `contributor` |
| RBAC proof admin | `skriptoteket-proof-admin` | `skriptoteket-proof-admin@local.dev` | Provider-owned proof-account secret, local default may reuse `BOOTSTRAP_SUPERUSER_PASSWORD` | `admin` |

HuleEdu must remain the source of truth for these credentials and exported
realm subjects. Skriptoteket must consume a sanitized HuleEdu subject export and
assign only product-local `User.role` values from its explicit role matrix. The
local account names above replace ad hoc teacher-dashboard smoke credentials for
new local proof; they do not authorize production account mutation or inferred
linking of existing local users.

### Goal

Add the smallest Skriptoteket-owned local preflight/proof lane that makes the
HuleEdu auth-edge dependency explicit and proves the `.env` bootstrap account
works end to end through HuleEdu credential verification, Gateway signing,
Skriptoteket app-continuation, and local RBAC.

The intended successful local state is:

- Skriptoteket stack is up on both `localhost:5173` and `127.0.0.1:5173`.
- HuleEdu Gateway is reachable on `localhost:8080` and `127.0.0.1:8080`.
- HuleEdu login UI is reachable on `localhost:5174` and `127.0.0.1:5174`.
- Vite protected `/api/...` traffic enters Gateway, while public
  `/api/v1/public/...` and `/share/classroom/...` remain direct Skriptoteket
  backend routes.
- The Gateway signing key trusted by `skriptoteket_web` matches the active
  local HuleEdu Gateway.
- HuleEdu login accepts the `.env` bootstrap credentials on both loopback
  lanes.
- Skriptoteket resolves the resulting signed context to the local projected
  superuser via app-continuation.

### Non-goals

- Reintroducing a local Skriptoteket browser password login endpoint.
- Verifying `.env` passwords against Skriptoteket-local password hashes for
  browser proof.
- Using `POST /api/v1/auth/login`, `/api/v1/auth/csrf`, or local session
  cookies as proof shortcuts.
- Auto-linking, silently repairing, or projection-shortcutting legacy
  `auth_provider=local` password users.
- Creating or mutating HuleEdu Identity users from Skriptoteket code.
- Changing production auth semantics, projection keys, role-matrix rules, CSRF
  ownership, logout ownership, or public/share route availability.
- Making public/share proof depend on the HuleEdu auth edge.

### Provider Gate

HuleEdu `TASK-0380` is the provider-side authority for the browser bootstrap
account seed scope. `TASK-0325` owns the local Gateway lane, but it does not by
itself prove that the `.env` bootstrap credentials exist in HuleEdu Identity.
Skriptoteket `PR-0283` consumes `TASK-0380` as the governed provider evidence
for the same `BOOTSTRAP_SUPERUSER_EMAIL` /
`BOOTSTRAP_SUPERUSER_PASSWORD` account.

The provider evidence consumed by this PR must include the retained output for:

- `pdm run run-local-pdm db-lifecycle plan --db identity_db --seed-scope browser-bootstrap`
- `pdm run run-local-pdm db-lifecycle reset-migrate-seed --db identity_db --seed-scope browser-bootstrap --execute`
- `pdm run run-local-pdm db-lifecycle verify --db identity_db`
- a local HuleEdu login proof against the local Identity/Gateway lane using
  `BOOTSTRAP_SUPERUSER_EMAIL` and `BOOTSTRAP_SUPERUSER_PASSWORD`

`TASK-0380` is now closed as `done` with retained review
`REV-TASK-0380-01` approved after remediation. Skriptoteket PR-0283 consumes
that provider evidence; it must not mutate HuleEdu Identity from this repo.

The provider evidence must show that the local HuleEdu credential belongs to
the product realm consumed by Skriptoteket and yields the `realm_subject_id`
used by the local `identity_projections` mapping.

HuleEdu `TASK-0326` remains the supporting subject-export/projection proof
authority for controlled proof accounts, but it is not a substitute for
provider-owned seed evidence for the `.env` browser bootstrap account.

The current retained `TASK-0326` local proof export covers `user`, `admin`, and
`superuser` under `@hule.education` proof addresses. PR-0283 must either consume
an updated HuleEdu local proof export that uses the deterministic `@local.dev`
matrix above and includes `contributor`, or fail closed with a diagnostic that
the local provider export is stale for the current dev identity contract.

### Implementation Recommendation

Implement PR-0283 as a narrow script/preflight extension, not as new runtime
auth behavior:

1. Add a small script-owned module, for example
   `scripts/auth_edge_bootstrap_preflight.py`, for pure probes and diagnostics:
   - environment/credential presence checks for `BOOTSTRAP_SUPERUSER_EMAIL` and
     `BOOTSTRAP_SUPERUSER_PASSWORD`, without logging values;
   - HuleEdu Gateway/login UI reachability checks for both loopback origins;
   - public/share route independence checks against Skriptoteket;
   - Gateway signing-key parity check through a live signed app-continuation
     probe when available, falling back only to active key/JWKS/fingerprint
     comparison;
   - Skriptoteket DB projection/RBAC checks that query local state without
     verifying passwords.
2. Add a thin PDM script entrypoint,
   `auth-edge-bootstrap-preflight`, that reports structured,
   redacted diagnostics and returns non-zero on missing auth-edge prerequisites
   or `bootstrap_identity_conflict`.
3. Extend the retained auth-cutover proof so
   `pdm run auth-cutover-proof --include-127-lane --require-127-lane`
   calls or consumes the new preflight before browser navigation. Keep the
   final browser proof in the retained PR-0254 lane instead of creating a
   second Playwright proof.
4. Keep the preflight read-only on both sides of the boundary:
   - no HuleEdu Identity seeding from Skriptoteket;
   - no local password-hash verification;
   - no auto-linking or silent projection repair;
   - no public/share route dependency on HuleEdu auth readiness.
5. Update local-dev/runbook surfaces that still look runnable for retired
   local auth (`POST /api/v1/auth/login`, `/api/v1/auth/csrf`, or local session
   cookie proof) so authenticated live proof points at the HuleEdu
   Gateway/login lane and public/share proof remains explicitly direct.

Operational command naming:

- use durable capability names for commands developers are expected to run
  after the originating PR closes;
- rename active PR/task-numbered PDM aliases in this auth proof lane to
  capability names as part of PR-0283, starting with
  `pr-0254-auth-cutover` -> `auth-cutover-proof`;
- audit the existing `pr-0252-*`, `pr-0253-*`, `pr-0255-*`, `pr-0258-*`,
  `pr-0261-*`, and `pr-0262-*` aliases in `pyproject.toml`; keep PR numbers
  only for retained one-off evidence commands, artifact paths, module
  docstrings, tests, and governed docs;
- update runnable docs, handoff snippets, and PDM script names together so no
  active operator surface teaches PR-numbered command names.

Recommended module boundaries:

- pure diagnostics/config helpers under `scripts/auth_edge_bootstrap_preflight.py`;
- optional DB read helpers under the same script module unless they become
  generally reusable;
- no changes to `src/skriptoteket/application/identity/huleedu_app_projection.py`
  unless the existing app-continuation route cannot surface the required
  diagnostic without weakening production semantics;
- focused tests under `tests/unit/application/auth/` plus one CLI smoke-style
  test for operator-readable output.

### Implementation Plan

1. Add a small local preflight command, preferably behind a PDM script, that
   checks:
   - Skriptoteket self-health and devstack state;
   - HuleEdu Gateway shared-session contract on both loopback origins;
   - HuleEdu login UI shell on both loopback origins;
   - expected `hule-network` reachability for Docker frontend-to-Gateway and
     Gateway-to-Skriptoteket protected API traffic;
   - public route independence for at least one public app/share-safe route;
   - trusted signing-key parity, using either a live Gateway-signed
     app-continuation probe or an active Gateway public key/JWKS/fingerprint
     comparison. Do not stop at "file exists."
2. Add a Skriptoteket authorization-state verifier that checks the projected
   local user, not credential truth:
   - signed context has `active_app=skriptoteket`;
   - product realm is accepted;
   - `realm_subject_id` maps through `identity_projections`;
   - local user is active and email-verified;
   - local user role is `superuser`;
   - local user is not being used as a legacy password-owner shortcut.
3. Add explicit `bootstrap_identity_conflict` detection. If the bootstrap email
   exists only as a Skriptoteket-local password user, or if a password-owning
   local user would be used without the required HuleEdu projection, fail
   closed with a diagnostic:
   `bootstrap_identity_conflict: email exists as Skriptoteket-local password user; browser proof requires HuleEdu-projected identity. Run the governed subject-export/projection bootstrap or reset the local dev DB.`
4. Extend the retained `PR-0254` proof lane instead of creating a parallel
   browser proof. Prefer extending the durable
   `pdm run auth-cutover-proof --include-127-lane --require-127-lane` command
   so it calls or consumes the new preflight, then proves browser login and
   app-continuation for both loopback lanes.
5. Update README/local-devops/runbook surfaces so authenticated live proof says
   "start/verify HuleEdu auth edge first" and no longer implies that
   `BOOTSTRAP_SUPERUSER_*` can be used against a Skriptoteket-local login API.
6. Keep public/share verification docs explicit: public routes can still be
   proven with Skriptoteket web/frontend/DB only.

### Test Plan

- Unit-test preflight diagnostics for:
  - missing HuleEdu Gateway;
  - missing HuleEdu login UI;
  - missing or mismatched signing-key trust;
  - missing `identity_projections` mapping;
  - inactive local user;
  - unverified local user;
  - wrong local role;
  - `bootstrap_identity_conflict`;
  - valid projected active verified local superuser.
- Unit-test that the preflight never calls or recommends
  `POST /api/v1/auth/login`.
- Run the retained auth-cutover proof with both loopback lanes:
  `pdm run auth-cutover-proof --include-127-lane --require-127-lane`.
  Expected result: HuleEdu login accepts the `.env` credentials on both lanes,
  returns to Skriptoteket, and app-continuation resolves the projected local
  superuser.
- Run the preflight with the HuleEdu edge absent or misconfigured:
  expected result is a fail-closed diagnostic naming the missing auth-edge
  prerequisite.
- Run docs and code gates:
  - `pdm run lint`
  - `pdm run typecheck`
  - focused backend/script tests added by this PR
  - `pdm run docs-validate`
  - `pdm run handoff-validate`
  - `git diff --check`

### Rollback Plan

Revert the new preflight/proof command and docs changes. Do not change or
delete local users, identity projections, HuleEdu provider accounts, or stored
password hashes as part of rollback.

### Review Notes

Review should reject any implementation that makes the proof pass by bypassing
HuleEdu Gateway, accepting unsigned identity headers, restoring local browser
sessions, using local password hashes for browser proof, or documenting
`POST /api/v1/auth/login` as a valid local login path.

The proof must show the `.env` bootstrap account working through the active
auth contract:

- HuleEdu proves credentials, session, CSRF, and signing.
- Skriptoteket proves projection, local RBAC, and public-route independence.
- Container diagnostics prove the local auth-edge dependency is present and
  trusted without reopening local auth authority.

## Decision And Assumption Ledger

The source material below remains authoritative for this section.

## Story Contract Slice

The source material below remains authoritative for this section.

## Contract Inputs

The source material below remains authoritative for this section.

## Plan

The source material below remains authoritative for this section.

## Implementation Steps

The source material below remains authoritative for this section.

## Proof

Verification expectations remain in the retained source material below.

## Validation

Verification expectations remain in the retained source material below.

## Stop Conditions

The source boundaries and recovery limits remain preserved below.

## Lessons Learned

The source material below remains authoritative for this section.

## Notes

The source material below remains authoritative for this section.

## Readiness

Readiness is governed by the inline readiness review in frontmatter.

## Closeout

Closeout is governed by the inline closeout review in frontmatter.

## Plan Document Review

The source material below remains authoritative for this section.

## Implementation Review

The source material below remains authoritative for this section.
