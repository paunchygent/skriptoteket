---
type: pr
id: PR-0260
title: "ST-28-11 bootstrap projection role matrix contract"
status: done
owners: "agents"
created: 2026-04-13
updated: 2026-04-13
stories:
  - "ST-28-11"
adrs:
  - "ADR-0083"
dependencies:
  - "ST-28-09"
  - "PR-0258"
  - "HuleEdu TASK-0326"
  - "REV-TASK-0326-01"
tags: ["auth", "identity-projections", "bootstrap", "rbac"]
acceptance_criteria:
  - "Given HuleEdu `TASK-0326` is done and deployed, when implementation starts, then this PR consumes the verified sanitized subject export and does not invent local identity data."
  - "Given a sanitized HuleEdu subject export for `skriptoteket_standalone`, when the subject export command runs, then Skriptoteket creates or updates matching local users and `identity_projections` without local password ownership."
  - "Given a subject export record is accepted, when the consumer validates it, then it contains the exact fields `stable_account_key`, `active_app=skriptoteket`, `active_product_identity_realm=skriptoteket_standalone`, `realm_subject_id`, `email`, `email_verified=true`, and `skriptoteket_role_hint`."
  - "Given `huleedu_subject_id` is present in the export, when projections are looked up or created, then the field is treated as diagnostic only and is never used as a projection key without `active_product_identity_realm` plus `realm_subject_id`."
  - "Given a local role matrix is configured, when projections are created, then local `User.role` is assigned from explicit Skriptoteket config and provider roles remain ignored for authorization."
  - "Given the command is rerun with the same input, when it completes, then it is idempotent and records no duplicate users, duplicate projections, or unintended role downgrades."
  - "Given existing alpha users have unrelated fake education-domain addresses, when the consumer runs, then it does not bulk import, infer-link, or rewrite those users."
  - "Given a required exported account cannot be mapped safely, when the command exits, then it fails closed with a sanitized operator message and retained logs that omit credentials and tokens."
---

## Problem

`PR-0258` added realm-aware projection provisioning, but final proof still needs
known role-bearing accounts. Production does not currently have HuleEdu subjects
linked into Skriptoteket projections, and most old Skriptoteket alpha accounts
are not valuable to bulk import because their email addresses were test data.

## Goal

Add the Skriptoteket-owned consumer half of the subject-export contract:
consume the HuleEdu `TASK-0326` subject export only after `REV-TASK-0326-01`
approves its corrected provider schema, create or update local users and
realm-aware projections, and assign the local role matrix needed for dev and
production auth proof.

## Non-goals

- Creating HuleEdu Identity users or password hashes.
- Calling HuleEdu Identity directly from the browser.
- Bulk importing old Skriptoteket alpha users.
- Treating HuleEdu roles, groups, or bootstrap labels as Skriptoteket
  authorization.
- Final login/register/reset proof; that belongs to `PR-0261` and `PR-0262`.

## Provider Gate Resolution

HuleEdu `TASK-0326` is now the completed provider prerequisite for this PR.
`REV-TASK-0326-01` is approved, the provider implementation was merged to
HuleEdu `main` at merge commit `92419293`, and production was redeployed through
`pdm run run-local-pdm hemma-redeploy-prod-core`.

Hemma production proof ran `dry-run`, explicit `apply`, and `verify` against
gitignored artifacts under `.artifacts/skriptoteket-auth-bootstrap/`. The
verified proof accounts are:

- `skriptoteket-proof-user@hule.education`
- `skriptoteket-proof-admin@hule.education`
- `skriptoteket-proof-superuser@hule.education`

This resolved the provider blocker and made `PR-0260` the next Skriptoteket
implementation slice.

The separate per-account public browser ceremony/Gateway profile proof has not
been run yet. That is not a blocker for this projection/role bootstrap PR; keep
it as a later lifecycle/final-proof obligation under HuleEdu `TASK-0327`,
Skriptoteket `PR-0262`, and final `PR-0254`.

## Consumed Export Schema

The accepted input is either the HuleEdu provider envelope with a successful
`status=ok` plus an `export` object, or the fully versioned export object
itself. The consumer must not accept a bare array or synthesize missing
top-level export fields from `{"accounts": [...]}`.

Each exported record must validate exactly against the consumer contract below
before any repository write occurs.

| Field | Required | Consumer rule |
|-------|----------|---------------|
| `stable_account_key` | Yes | Nonblank provider-stable account label; never an email address, password, token, or credential. Used for role-matrix lookup and sanitized operator messages only. |
| `active_app` | Yes | Must equal `skriptoteket`; any other value fails closed before linking or user lookup. |
| `active_product_identity_realm` | Yes | Must equal `skriptoteket_standalone` for this export and is the first half of the projection key. |
| `realm_subject_id` | Yes | Nonblank product-realm subject identifier and the second half of the projection key. |
| `email` | Yes | Provider-owned verified email address used only after the realm subject passes validation; duplicate email never authorizes inferred linking. |
| `email_verified` | Yes | Must be boolean `true`; missing, false, string-like, or nullable values fail closed. |
| `skriptoteket_role_hint` | Yes | Consumer-owned matrix key, validated against the active local role matrix. HuleEdu roles, groups, Gateway grants, and browser-session claims are ignored for `User.role`. |
| `huleedu_subject_id` | Optional | Diagnostic umbrella HuleEdu subject only. It must not be accepted as the Skriptoteket projection key and must not repair a missing realm or `realm_subject_id`. |

Validation must reject missing `active_product_identity_realm` or
`realm_subject_id`, non-`skriptoteket` app values, unsupported role hints,
non-verified email, duplicate subject records, duplicate email records, and any
case where an existing local user would need inferred email-only linking.
Existing local roles are preserved unless the exact `stable_account_key` has an
explicit role-matrix entry that allows a promotion for that exported account.

## Implementation Summary (as of 2026-04-13)

`PR-0260` is implemented and approved after remediation review. The reusable
production capability is named around the durable business function rather than
the task: strict HuleEdu subject export validation lives in
`src/skriptoteket/application/identity/huleedu_subject_export_contract.py`, the
application service that applies it to local `User` rows, roles, and
`identity_projections` lives in
`src/skriptoteket/application/identity/huleedu_subject_export_consumer.py`, and
the operator entrypoint is `pdm run consume-huleedu-subject-export`.

Task/proof language remains in backlog docs, fixtures, runbooks, and retained
artifacts. Production code only owns the reusable import/projection operation:
validate the provider export, reject unsafe inference, create missing
HuleEdu-owned local users with no password hash, create realm-aware projections,
promote roles only through the explicit local matrix, preserve higher local
roles, and retain sanitized results/events.

Post-implementation review requested two corrections before this PR could be
accepted:

- stop accepting synthesized or unversioned export inputs;
- make blocked mapping audit durable rather than merely returning sanitized
  command errors.

The approved remediation now requires explicit top-level `schema_version`,
`active_app`, and `active_product_identity_realm`, rejects bare arrays and
unversioned `accounts` objects, and records blocked apply outcomes in
`identity_projection_events` after rolling back unsafe local user/projection
mutations. Dry-run reporting is also mode-aware: result artifacts include
explicit `would_create_users`, `would_create_projections`, and
`would_update_users` counters, and the CLI dry-run line reports planned actions
instead of concrete `created=0` / `updated=0` write counters.

## Implementation Plan

1. Consume only the exact approved HuleEdu `TASK-0326` export schema documented
   above; reject any input that relies on `huleedu_subject_id` as a projection
   key.
2. Add a small application service or management command that validates the
   export and applies the explicit local role matrix through existing repository/UoW
   patterns.
3. Reuse the realm-aware projection model from `PR-0258`; do not add a parallel
   legacy mapping path.
4. Preserve existing local roles unless an explicit subject role-matrix entry
   allows an update for that exported account.
5. Record sanitized audit/log events for created, updated, skipped, and blocked
   mappings.
6. Add focused tests for schema validation, idempotency, duplicate subject
   handling, duplicate email handling, role preservation, and unsafe inference.
7. Update the operator runbook with the dev/prod handoff from HuleEdu and the
   exact proof evidence expected before `PR-0254`.

## Downstream Dependencies

- HuleEdu `TASK-0327` now follows this PR and proves real-inbox lifecycle plus
  direct-action landing.
- Skriptoteket `PR-0261` should wait for HuleEdu `TASK-0327` and then wire
  auth-entry links to the accepted provider action routes.
- Skriptoteket `PR-0262` should wait for completed `PR-0260`, `TASK-0327`, and
  `PR-0261` before proving the full real-account lifecycle.
- Final `PR-0254` should wait for completed `PR-0260`, `TASK-0327`, `PR-0261`,
  and `PR-0262`.

## Test Plan

- Implementation must introduce and run focused backend and CLI tests with exact paths:
  `pdm run pytest -q tests/unit/application/identity/test_bootstrap_subject_export_schema.py tests/unit/application/identity/test_bootstrap_projection_role_matrix.py tests/unit/cli/test_consume_huleedu_subject_export.py`.
- Run repository/concurrency coverage that proves duplicate subject/email
  handling fails closed without inferred linking:
  `pdm run pytest -q tests/integration/infrastructure/repositories/test_identity_projection_repository.py tests/integration/application/test_huleedu_app_projection_concurrency.py tests/integration/application/test_huleedu_subject_export_consumer_audit.py`.
- Run `pdm run typecheck`.
- Run `pdm run lint`.
- Run `pdm run docs-validate`.
- Run `git diff --check`.
- Run the command locally against a sanitized fixture export that covers the
  required proof roles and stores retained evidence under the gitignored
  `.artifacts/skriptoteket-auth-bootstrap/` directory.
- Manually inspect retained command output and artifact manifests to confirm no
  credentials, reset tokens, verification tokens, raw action URLs, session
  cookies, or raw signed identity payloads are printed or retained.

## Rollback Plan

Revert the command/service and runbook additions. Existing user and projection
data should remain unaffected unless an operator has already run the command; in
that case, use a targeted rollback note listing the created projection IDs
instead of deleting unrelated historical users.
