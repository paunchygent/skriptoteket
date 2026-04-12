---
type: story
id: ST-28-09
title: "Realm-aware projection provisioning and local RBAC"
status: blocked
owners: "agents"
created: 2026-04-11
updated: 2026-04-11
epic: "EPIC-28"
acceptance_criteria:
  - "Given a signed Hule Education identity context includes active product realm and app, when Skriptoteket resolves app continuation, then it maps the realm-aware identity to the correct local projection without using realm-ambiguous `sub` alone."
  - "Given signed provisioning claims are sufficient, when first-time Skriptoteket standalone login completes, then projection creation is safe, idempotent, and auditable."
  - "Given signed provisioning claims are insufficient, when an authenticated identity has no projection, then Skriptoteket fails closed and reaches deliberate local-access-required UX without fabricating a user."
  - "Given local RBAC remains Skriptoteket-owned, when the app authorizes contributor/admin/superuser behavior, then authorization uses local `User.role` and not generic HuleEdu provider roles."
data_impact: "May require a realm-aware identity key or projection migration after ADR-0083 is accepted."
dependencies: ["ST-28-06", "ST-28-07", "ST-28-08", "ADR-0083", "PR-0255"]
---

## Context

`PR-0255` resolved existing HuleEdu subjects to local projections using the
current signed context. The product identity realm direction requires a stronger
projection contract that can distinguish HuleEdu school identity from
Skriptoteket standalone identity and future linked identities.

This story owns the app-local projection and authorization work after the
identity realm contract is accepted.

## Notes

- Preserve `AuthProvider.LOCAL` and local identity data until a deliberate data
  migration replaces them.
- Keep missing projection fail-closed.
- Keep app authorization local even when Hule Education supplies session,
  realm, tenant, grants, or feature metadata.
