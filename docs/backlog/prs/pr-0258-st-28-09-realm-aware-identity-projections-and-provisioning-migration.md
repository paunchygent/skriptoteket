---
type: pr
id: PR-0258
title: "ST-28-09 realm-aware identity projections and provisioning migration"
status: ready
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
tags: ["auth", "backend", "huleedu", "identity", "migration", "playwright"]
acceptance_criteria:
  - "Given the current app continuation still resolves HuleEdu subjects through `(auth_provider, external_id)`, when this PR completes, then production code resolves local users through a dedicated identity projection table keyed by `(product_identity_realm, realm_subject_id)`."
  - "Given `users.external_id` is legacy provider-subject state, when the migration lands, then the column, its index/constraint, domain model field, fixtures, and repository protocol lookup are removed rather than renamed or repurposed."
  - "Given HuleEdu signs sufficient app context for `skriptoteket`, when no projection exists for an accepted realm subject, then Skriptoteket idempotently creates a local user/profile/projection with local role `user` and auditably records the provisioning path."
  - "Given the signed context is missing `active_app`, accepted `product_identity_realm`, `realm_subject_id`, `email`, or verified email state, when no projection exists, then the app fails closed into provisioning-required UX without fabricating or linking a user."
  - "Given an existing local user has the same email as a newly signed HuleEdu identity, when no explicit signed/admin link exists, then Skriptoteket does not infer account linking from email and instead fails closed into linking-required/provisioning-required UX."
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
| Local user | Keep `users` as Skriptoteket profile/RBAC state |
| Default role | Newly provisioned projections create local role `user` |
| Promotions | Contributor/admin/superuser remain local promotions |
| Provider roles | Metadata only; never app authorization |
| Account linking | Explicit signed/admin link only; never email inference |
| Lifecycle completion | Does not imply authenticated app state until shared login/context is proven |
| Local proof | Local/non-production Gateway with exact dev-origin allowlist |

## Implementation Plan

1. Add a realm-aware identity projection domain model and protocol-first repository surface.
2. Add an Alembic migration that creates the projection table with a unique
   `(product_identity_realm, realm_subject_id)` constraint and removes `users.external_id`, its
   index, and the old provider-subject uniqueness constraint.
3. Move app continuation from `get_by_auth_provider_external_id()` to projection lookup by
   signed `active_product_identity_realm` and `realm_subject_id`.
4. Add provisioning logic that creates a local user/profile/projection only from sufficient signed
   context: `active_app=skriptoteket`, accepted realm, realm subject, email, and verified email
   state.
5. Treat duplicate email without explicit link as a fail-closed linking/provisioning-required
   outcome, not an implicit merge.
6. Preserve local RBAC by defaulting new users to `Role.USER` and leaving promotions as local admin
   actions.
7. Update tests, fixtures, admin/user serializers, and docs that still mention `external_id` as a
   `User` field or app-continuation lookup key.
8. Add local Docker ceremony proof that points Skriptoteket at a local or non-production HuleEdu
   Gateway whose return-origin allowlist includes the exact Vite dev origin under test.

## Test Plan

- Alembic migration upgrade/downgrade/idempotency coverage for projection table creation and
  `external_id` removal.
- Repository and handler tests for projection lookup, first-login provisioning, insufficient
  claims, duplicate email without explicit link, and local role defaults.
- Continuation API tests proving accepted realms resolve by `(product_identity_realm,
  realm_subject_id)` and unsupported/missing realm fields fail closed.
- Frontend/store tests for provisioning-required or linking-required UX.
- Local Docker or local/non-production Gateway Playwright proof for the full auth ceremony.
- `pdm run typecheck`
- `pdm run lint`
- `pdm run docs-validate`
- `git diff --check`

## Rollback Plan

If the projection migration exposes an unhandled production data shape, stop before running the
final migration, document the exact rows that need explicit linking, and keep `PR-0254` blocked.
Do not reintroduce `(auth_provider, external_id)` lookup as a compatibility shim.
