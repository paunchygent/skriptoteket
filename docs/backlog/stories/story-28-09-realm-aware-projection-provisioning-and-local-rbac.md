---
type: story
id: ST-28-09
title: "Realm-aware projection provisioning and local RBAC"
status: done
owners: "agents"
created: 2026-04-11
updated: 2026-04-12
epic: "EPIC-28"
acceptance_criteria:
  - "Given the old provider-subject shape is ambiguous, when this story completes, then Skriptoteket resolves identity through a dedicated local projection table keyed by `(product_identity_realm, realm_subject_id)` and no production lookup depends on `users.external_id` or `(auth_provider, external_id)`."
  - "Given the legacy `external_id` field exists only because of the old provider-subject model, when the migration lands, then existing HuleEdu-linked provider-subject rows are preflighted/backfilled before `external_id` is removed rather than renamed, repurposed, or left as loose provider metadata."
  - "Given signed provisioning claims are sufficient, when first-time Skriptoteket standalone or accepted HuleEdu-school login completes for `app=skriptoteket`, then projection creation is safe, idempotent, auditable, and defaults the local Skriptoteket role to `user`."
  - "Given signed provisioning claims are insufficient, when an authenticated identity has no projection, then Skriptoteket fails closed and reaches deliberate local-access-required UX without fabricating a user."
  - "Given local RBAC remains Skriptoteket-owned, when the app authorizes contributor/admin/superuser behavior, then authorization uses local `User.role` and not generic HuleEdu provider roles."
  - "Given local livetests need the real auth ceremony, when Docker/local proof runs, then Skriptoteket uses a local or non-production HuleEdu Gateway whose allowlist includes the exact dev origins instead of widening production Gateway origins to localhost."
data_impact: "Clean projection migration shipped: dedicated projection table, HuleEdu-linked provider-subject backfill, identity lookup by `(product_identity_realm, realm_subject_id)`, `users.external_id` removal, and no email-inferred linking."
dependencies: ["ST-28-06", "ST-28-07", "ST-28-08", "ADR-0083", "PR-0255", "PR-0256", "PR-0257", "PR-0258", "REV-PR-0258"]
---

## Context

`PR-0255` resolved existing HuleEdu subjects to local projections using the
current signed context. The product identity realm direction requires a stronger
projection contract that can distinguish HuleEdu school identity from
Skriptoteket standalone identity and future linked identities.

This story implemented the app-local projection and authorization work after the
identity realm contract, login ceremony, and standalone lifecycle handoff were
accepted. Retained `REV-PR-0258` approved the migration/provisioning contract;
`PR-0258` now carries the concrete signed provisioning fields in
`InternalIdentityContextV1` and keeps first-login creation fail-closed when those
claims are absent or untrusted.

## Notes

- Add a dedicated local projection table instead of stuffing realm identity
  keys into `users`.
- Remove `external_id` now. Do not rename it, repurpose it, or keep it as
  provider metadata.
- Backfill existing `auth_provider=huleedu` + nonblank `external_id` rows into
  `huleedu_school` projections before dropping `external_id`; fail the
  migration on ambiguous provider-subject data.
- Keep the local `users` record as Skriptoteket-owned profile/RBAC state.
- Keep contributor/admin/superuser as local promotions. Provider roles are
  metadata only.
- First-login provisioning may create a local user/projection only when the
  signed HuleEdu context includes `active_app=skriptoteket`, an accepted
  `product_identity_realm`, `realm_subject_id`, `email`, and verified email
  state.
- A HuleEdu teacher identity may auto-provision a normal Skriptoteket `user`
  projection for `huleedu_school` without a second login when the signed
  context is sufficient.
- Matching email must never be treated as account linking. If a signed identity
  collides with an existing local email without an explicit signed/admin link,
  fail closed into provisioning/linking-required UX.
- Existing manually created alpha users keep their local user rows, profiles,
  and roles. Any link to a new HuleEdu realm subject must be explicit, not
  inferred from email.
- Lifecycle completion does not imply authenticated app state. Projection
  resolution/provisioning runs only after the shared session/login ceremony
  provides verified signed context.
- Local Docker ceremony proof must use a local or non-production HuleEdu
  Gateway configured for exact dev origins such as `http://localhost:5173` and
  `http://127.0.0.1:5173`.

## Implementation Summary (as of 2026-04-12)

`PR-0258` shipped the realm-aware projection model. Skriptoteket resolves app continuation through
a dedicated `identity_projections` table keyed by
`(product_identity_realm, realm_subject_id)`, records projection outcomes in
`identity_projection_events`, and removes the legacy `users.external_id` field
after preflight/backfilling old HuleEdu subject rows into `huleedu_school`.

First-login provisioning now creates a local Skriptoteket `user` only when the
signed context proves `active_app=skriptoteket`, an accepted realm, realm
subject, nonblank email, and `email_verified=true`. Missing signed claims,
duplicate email without explicit link, unsupported realm, and missing/inactive
local projections fail closed without inferring account links from email. Runtime projection events
carry request correlation ids, DB-backed tests prove concurrent provisioning and unique-conflict
recovery, invalid product context remains a generic auth ceremony/context error, and user-facing
login actions now open the HuleEdu ceremony directly. The live proof is
`ARTIFACTS_ROOT=.artifacts/local-tool-artifacts pdm run pr-0258-auth-projection --start-backend --start-vite --gateway-base-url http://127.0.0.1:8000`.
