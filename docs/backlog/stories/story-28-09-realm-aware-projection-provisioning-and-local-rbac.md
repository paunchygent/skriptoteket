---
type: story
id: ST-28-09
title: "Realm-aware projection provisioning and local RBAC"
status: ready
owners: "agents"
created: 2026-04-11
updated: 2026-04-12
epic: "EPIC-28"
acceptance_criteria:
  - "Given the old provider-subject shape is ambiguous, when this story completes, then Skriptoteket resolves identity through a dedicated local projection table keyed by `(product_identity_realm, realm_subject_id)` and no production lookup depends on `users.external_id` or `(auth_provider, external_id)`."
  - "Given the legacy `external_id` field exists only because of the old provider-subject model, when the migration lands, then `external_id` is removed rather than renamed, repurposed, or left as loose provider metadata."
  - "Given signed provisioning claims are sufficient, when first-time Skriptoteket standalone or accepted HuleEdu-school login completes for `app=skriptoteket`, then projection creation is safe, idempotent, auditable, and defaults the local Skriptoteket role to `user`."
  - "Given signed provisioning claims are insufficient, when an authenticated identity has no projection, then Skriptoteket fails closed and reaches deliberate local-access-required UX without fabricating a user."
  - "Given local RBAC remains Skriptoteket-owned, when the app authorizes contributor/admin/superuser behavior, then authorization uses local `User.role` and not generic HuleEdu provider roles."
  - "Given local livetests need the real auth ceremony, when Docker/local proof runs, then Skriptoteket uses a local or non-production HuleEdu Gateway whose allowlist includes the exact dev origins instead of widening production Gateway origins to localhost."
data_impact: "Requires a clean projection migration: create a dedicated projection table, move identity lookup to `(product_identity_realm, realm_subject_id)`, remove `users.external_id`, and avoid email-inferred linking."
dependencies: ["ST-28-06", "ST-28-07", "ST-28-08", "ADR-0083", "PR-0255", "PR-0256", "PR-0257"]
---

## Context

`PR-0255` resolved existing HuleEdu subjects to local projections using the
current signed context. The product identity realm direction requires a stronger
projection contract that can distinguish HuleEdu school identity from
Skriptoteket standalone identity and future linked identities.

This story owns the app-local projection and authorization work now that the
identity realm contract, login ceremony, and standalone lifecycle handoff are
accepted.

## Notes

- Add a dedicated local projection table instead of stuffing realm identity
  keys into `users`.
- Remove `external_id` now. Do not rename it, repurpose it, or keep it as
  provider metadata.
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
