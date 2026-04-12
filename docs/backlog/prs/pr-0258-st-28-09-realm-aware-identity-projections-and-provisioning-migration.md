---
type: pr
id: PR-0258
title: "ST-28-09 realm-aware identity projections and provisioning migration"
status: done
owners: "agents"
created: 2026-04-12
updated: 2026-04-12
stories:
  - "ST-28-09"
adrs:
  - "ADR-0083"
dependencies:
  - "ST-28-06"
  - "ST-28-07"
  - "ST-28-08"
  - "PR-0255"
  - "PR-0256"
  - "PR-0257"
  - "REV-PR-0258"
tags: ["auth", "backend", "huleedu", "identity", "migration", "playwright"]
acceptance_criteria:
  - "Given the current app continuation still resolves HuleEdu subjects through `(auth_provider, external_id)`, when this PR completes, then production code resolves local users through a dedicated identity projection table keyed by `(product_identity_realm, realm_subject_id)`."
  - "Given `users.external_id` is legacy provider-subject state, when the migration lands, then existing `auth_provider=huleedu` rows are preflighted/backfilled into realm-aware projections before the column, index/constraint, domain model field, fixtures, and repository protocol lookup are removed rather than renamed or repurposed."
  - "Given old HuleEdu-linked rows came from the PR-0255 provider-subject bridge, when they are backfilled, then they are written as `product_identity_realm=huleedu_school`, ambiguous rows fail the migration, and upgraded app continuation still resolves those users by the new projection key."
  - "Given HuleEdu signs sufficient app context for `skriptoteket`, when no projection exists for an accepted realm subject, then Skriptoteket idempotently creates a local user/profile/projection with local role `user` and auditably records the provisioning path."
  - "Given the signed product context is missing, blank, untrusted, or malformed for `active_app`, accepted `product_identity_realm`, or `realm_subject_id`, when app continuation runs, then the app fails closed as a generic auth ceremony/context error without exposing projection internals."
  - "Given the signed provisioning claims are missing, blank, false, untrusted, or malformed for signed `email` or signed `email_verified=true`, when no projection exists, then the app fails closed into provisioning-required UX without fabricating or linking a user."
  - "Given an existing local user has the same email as a newly signed HuleEdu identity, when no explicit signed/admin link exists, then Skriptoteket does not infer account linking from email and instead fails closed into linking-required/provisioning-required UX."
  - "Given two callbacks for the same realm subject or competing subjects with the same email race, when first-login provisioning runs, then UoW-owned get-or-create/upsert handling returns one local user/projection or a fail-closed linking-required outcome and never leaves duplicate or orphan rows or a raw unique-conflict `500`."
  - "Given projection lookup, provisioning, blocked provisioning, duplicate-email, unsupported-realm, and migration-backfill outcomes occur, when this PR records identity events, then the audit surface includes realm, realm subject, user/projection when available, reason code, request correlation id when available, and signed context `jti`."
  - "Given HuleEdu provider roles may exist in signed metadata, when Skriptoteket authorizes app behavior, then contributor/admin/superuser decisions still use local `User.role` and newly provisioned users default to local `user`."
  - "Given local Docker livetests must exercise the real ceremony, when the PR proof runs, then it uses a local or non-production HuleEdu Gateway with exact allowed return origins for `http://localhost:5173` and/or `http://127.0.0.1:5173`, not production Gateway localhost allowlisting."
---

## Problem

`PR-0255` intentionally used the old user-level provider-subject shape as a temporary bridge:
`auth_provider=huleedu` plus `external_id=<context.sub>`. `ADR-0083` and the completed
`ST-28-07` / `ST-28-08` provider ceremonies now make that shape too ambiguous for final
Skriptoteket auth.

The next implementation slice must stop treating the local `users` row as both app user and
external identity projection. Skriptoteket needs a first-class projection model that says exactly
which signed HuleEdu product realm subject maps to which local Skriptoteket user.

## Goal

Implement the clean realm-aware projection model for app continuation, first-login provisioning,
local RBAC preservation, and local Docker ceremony proof.

The target shape is:

```text
HuleEdu signed context
  -> identity projection keyed by (product_identity_realm, realm_subject_id)
    -> Skriptoteket local user/profile/role
```

The PR must remove `external_id` rather than preserve it as legacy provider metadata.

## Non-goals

- Inferring account linking from matching email.
- Promoting users from HuleEdu provider roles.
- Reintroducing Skriptoteket-local browser login, password, registration, reset, or verification
  authority.
- Widening the public production HuleEdu Gateway return-origin allowlist to local development
  origins.
- Running the final operator cross-app smoke; that remains `PR-0254` after this slice.

## Decisions Locked

| Decision | Locked shape |
|----------|--------------|
| Projection storage | Dedicated local projection table, not identity columns on `users` |
| Projection key | Unique `(product_identity_realm, realm_subject_id)` |
| Legacy field | Remove `users.external_id` and old lookup protocols now |
| Legacy backfill | Existing `auth_provider=huleedu` + nonblank `external_id` rows backfill to `huleedu_school` projections before `external_id` is dropped |
| Local user | Keep `users` as Skriptoteket profile/RBAC state |
| Default role | Newly provisioned projections create local role `user` |
| Promotions | Contributor/admin/superuser remain local promotions |
| Provider roles | Metadata only; never app authorization |
| Account linking | Explicit signed/admin link only; never email inference |
| Lifecycle completion | Does not imply authenticated app state until shared login/context is proven |
| Provisioning claims | Concrete signed `email`, `email_verified`, and optional profile/locale fields inside `InternalIdentityContextV1`; missing, false, blank, malformed, or unsigned values fail closed |
| Auditability | Dedicated identity-projection audit/event surface, not an implied login side effect |
| Local proof | Local/non-production Gateway with exact dev-origin allowlist |

## Required Signed Context Contract

First-login provisioning is allowed only from concrete provisioning claims signed by the HuleEdu
Gateway inside `X-Huledu-Identity-Context`. Skriptoteket models those fields explicitly in
`InternalIdentityContextV1` without weakening `extra="forbid"`.

Required signed fields:

| Field | Required Semantics |
|-------|--------------------|
| `active_app` | Must be exactly `skriptoteket` |
| `active_product_identity_realm` | Must be one accepted realm: `skriptoteket_standalone` or `huleedu_school` |
| `realm_subject_id` | Nonblank realm-local subject id used in the projection key |
| `email` | Nonblank normalized email address; unsigned query/session values do not count |
| `email_verified` | Boolean `true`; missing, `false`, null, or string-like values fail closed |
| `given_name` | Optional signed profile source; blank values normalize to absent |
| `family_name` | Optional signed profile source; blank values normalize to absent |
| `display_name` | Optional signed profile source; blank values normalize to absent |
| `locale` | Optional signed locale; defaults to `sv-SE` when absent |

The verifier/model work adds explicit Pydantic fields and validators for these claims. It must not
read provisioning claims from `active_context`, arbitrary extra fields, route query
parameters, local storage, or a non-signed session response.

## Implementation Plan

1. Add a realm-aware identity projection domain model and protocol-first repository surface.
2. Add an Alembic migration that creates the projection table with a unique
   `(product_identity_realm, realm_subject_id)` constraint.
3. Move app continuation from `get_by_auth_provider_external_id()` to projection lookup by
   signed `active_product_identity_realm` and `realm_subject_id`.
4. Add a migration preflight/backfill phase before dropping `users.external_id`:
   - copy existing rows with `auth_provider=huleedu` and nonblank `external_id` into projections as
     `product_identity_realm=huleedu_school`
   - fail the migration on duplicate `(huleedu_school, external_id)` rows, blank external ids,
     unexpected provider/external-id combinations, or any row that cannot be mapped without
     guessing
   - prove upgraded app continuation still resolves backfilled users through the new projection key
5. Only after successful preflight/backfill, remove `users.external_id`, its index, and the old
   provider-subject uniqueness constraint plus the domain/repository protocol lookup.
6. Extend `InternalIdentityContextV1`, verifier fixtures, and provider-contract tests for signed
   `email`, `email_verified`, optional profile-name fields, and optional locale.
7. Add provisioning logic that creates a local user/profile/projection only from sufficient signed
   context: `active_app=skriptoteket`, accepted realm, realm subject, signed email, and signed
   `email_verified=true`.
8. Implement UoW-owned idempotency:
   - first read projection by `(product_identity_realm, realm_subject_id)`
   - create user/profile/projection in one transaction when absent
   - on projection unique conflict, roll back and re-read the projection
   - on email unique conflict with no projection after re-read, fail closed into linking-required
     UX rather than returning `500`
9. Treat duplicate email without explicit link as a fail-closed linking/provisioning-required
   outcome, not an implicit merge.
10. Add a dedicated identity-projection audit/event surface for resolved, provisioned, blocked,
   duplicate-email/linking-required, unsupported-realm, migration-backfilled, and migration-blocked
   outcomes. Include realm, realm subject, local user/projection id when available, reason code,
   correlation id, and signed context `jti`.
11. Preserve local RBAC by defaulting new users to `Role.USER` and leaving promotions as local admin
   actions.
12. Update tests, fixtures, admin/user serializers, and docs that still mention `external_id` as a
   `User` field or app-continuation lookup key.
13. Regenerate OpenAPI and frontend types after API/user contract changes:
   `pdm run fe-gen-api-types`.
14. Add local Docker ceremony proof that points Skriptoteket at a local or non-production HuleEdu
   Gateway whose return-origin allowlist includes the exact Vite dev origin under test.

## Test Plan

- Alembic migration upgrade/downgrade/idempotency coverage for projection table creation and
  `external_id` removal.
- Docker migration coverage:
  `pdm run pytest -q tests/integration/test_migration_e7b3a9c4d1f2_idempotent.py -m docker --override-ini addopts=''`
- `pdm run python -m scripts.check_migration_test_coverage`
- Migration tests proving HuleEdu-linked `(auth_provider=huleedu, external_id=...)` users backfill
  into `huleedu_school` projections and still resolve after upgrade.
- Migration tests proving ambiguous duplicate/blank/unexpected provider-subject rows fail before
  dropping `users.external_id`.
- Repository and handler tests for projection lookup, first-login provisioning, insufficient
  claims, duplicate email without explicit link, and local role defaults.
- Concurrency or unique-conflict regression tests for double callback/get-or-create behavior.
- Signed-context verifier/model tests for missing, blank, false, null, untrusted, extra, and
  malformed provisioning claims.
- Audit/event tests for resolved, provisioned, blocked provisioning, duplicate-email/linking-
  required, unsupported-realm, migration-backfilled, and migration-blocked outcomes.
- Continuation API tests proving accepted realms resolve by `(product_identity_realm,
  realm_subject_id)` and unsupported/missing realm fields fail closed.
- Frontend/store tests for provisioning-required or linking-required UX.
- Local Docker or local/non-production Gateway Playwright proof for the full auth ceremony.
- Exact live proof command and artifacts path must be recorded in `.agents/handoff.md`; expected
  shape: `ARTIFACTS_ROOT=.artifacts/local-tool-artifacts pdm run pr-0258-auth-projection --start-backend --start-vite --gateway-base-url <local-or-nonprod-gateway>`.
- `pdm run fe-gen-api-types`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run typecheck`
- `pdm run lint`
- `pdm run docs-validate`
- `git diff --check`

## Implementation Closeout (2026-04-12)

`ST-28-09` / `PR-0258` is done. The retained implementation review remediation closed the runtime
proof gaps before `PR-0254` starts.

- `src/skriptoteket/domain/identity/projections.py` defines the local projection and projection
  audit domain model.
- `migrations/versions/e7b3a9c4d1f2_identity_projections.py` creates `identity_projections` and
  `identity_projection_events`, preflights/backfills legacy HuleEdu `external_id` rows as
  `huleedu_school`, fails ambiguous data, and removes `users.external_id`.
- `src/skriptoteket/application/identity/huleedu_app_projection.py` now resolves app continuation
  through `(product_identity_realm, realm_subject_id)`, provisions only from signed verified email
  claims, defaults local role to `user`, rejects email-inferred linking, records projection
  outcomes with request correlation ids, and recovers from email/projection unique conflicts with
  repository-owned no-conflict inserts plus re-read/fail-closed handling.
- `InternalIdentityContextV1` now explicitly carries signed provisioning fields: `email`,
  `email_verified`, `given_name`, `family_name`, `display_name`, and `locale`.
- Frontend auth bootstrap and provisioning UX treat missing projection, linking-required, and
  inactive/missing local-user outcomes as local access required, without reviving app-local browser
  auth. Invalid signed product context remains a generic auth ceremony/context error, not local
  provisioning UX.
- `scripts/playwright_pr_0258_auth_projection.py` proves first-login provisioning, idempotent
  projection reuse, fail-closed missing signed email, duplicate-email linking-required behavior, and
  SPA bootstrap through the real app-continuation route. The proof also verifies that user-facing
  login actions open the HuleEdu ceremony directly and `/auth/login?next=...` auto-hands off rather
  than requiring a second CTA.

## Review Remediation Closeout (2026-04-12)

Retained implementation review reopened this PR with `changes_requested`. The remediation is now
closed:

1. App-continuation now passes the request correlation id into the projection resolver and runtime
   `identity_projection_events` persist it.
2. First-login provisioning uses repository-owned no-conflict inserts for user email and projection
   uniqueness; projection conflicts re-read the winner, email conflicts fail closed into
   linking-required, and raw unique-conflict `500`s are covered by DB-backed tests.
3. `tests/integration/application/test_huleedu_app_projection_concurrency.py` proves same-subject
   concurrent provisioning, same-email competing subjects, and projection unique-conflict recovery.
4. Invalid signed product context remains a generic auth ceremony/context error in docs and frontend
   tests; provisioning UX remains reserved for missing projection, linking-required, and
   inactive/missing local user outcomes.
5. Normal user-facing "Logga in" actions open the HuleEdu login ceremony directly; `/auth/login`
   remains only as an auto-handoff/fallback route.
6. Focused backend, migration, frontend, docs, and live `pr-0258-auth-projection` proof gates passed
   after remediation.

## Rollback Plan

If the projection migration exposes an unhandled production data shape, stop before running the
final cross-app proof, document the exact rows that need explicit linking, and keep `PR-0254`
paused.
Do not reintroduce `(auth_provider, external_id)` lookup as a compatibility shim.
