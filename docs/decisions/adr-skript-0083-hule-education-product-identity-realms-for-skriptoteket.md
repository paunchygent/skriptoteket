---
type: adr
id: ADR-SKRIPT-0083
title: Hule Education product identity realms for Skriptoteket login
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: accepted
deciders:
- user-lead
retired_ids:
- ADR-0083
---

## Context


`PR-0253` retires Skriptoteket-local browser-session authority: Skriptoteket no
longer owns a browser login form, browser session cookie, local CSRF authority,
or local `/api/v1/auth/*` browser API. That hard break is intentional and keeps
the Hule Education Gateway/Identity layer as the shared browser edge.

The hard break must not collapse Skriptoteket identity into a HuleEdu-school-only
identity. Skriptoteket remains a product with its own account meaning, onboarding
semantics, projection, profile, RBAC, AI preferences, and local authorization.
Users must be able to log in to Skriptoteket without completing HuleEdu school
registration.

`REF-hule-education-product-identity-realms-and-skriptoteket-standalone-identity`
records the reference direction. This ADR is the retained decision package that
should turn that direction into an implementation contract before `ST-28-04` /
`PR-0254` is treated as the final cross-app proof.

## Decision


Hule Education Gateway/Identity is the browser session and login ceremony authority for
Skriptoteket, but it must support product identity realms.

For Skriptoteket, the accepted model is:

- `skriptoteket_standalone` is a distinct product identity realm.
- HuleEdu school identity is a separate realm, not the only Skriptoteket login identity.
- A user may authenticate through the shared Hule Education ceremony for
  Skriptoteket without completing HuleEdu school registration.
- Account linking between HuleEdu school identity and Skriptoteket standalone
  identity is explicit, not implied by matching email or browser session.
- Browser login anchors target a browser-navigable ceremony URL, not a POST-only
  auth API endpoint.
- Downstream signed identity context distinguishes the shared browser session
  from the active product identity realm and active app.
- Skriptoteket resolves local projection and authorization from the signed
  realm-aware identity context, then applies local `User.role` for RBAC.
- `AuthProvider.LOCAL` and existing Skriptoteket-local identity data remain
  valid product-domain concepts until a later data migration explicitly replaces
  them.

### Frozen Terms

The following terms are frozen for downstream stories and PRs:

| Term | Meaning | Owner |
|------|---------|-------|
| Browser session | The umbrella Hule Education browser session and CSRF authority | Hule Education Gateway/Identity |
| Product identity realm | Product account namespace selected for the active login | Hule Education Identity with product input from Skriptoteket |
| Active app | The app that initiated or consumes the ceremony, currently `skriptoteket` | Hule Education Gateway plus downstream app validation |
| Realm subject | Stable subject id inside one product identity realm | Hule Education Identity |
| Skriptoteket projection | Local `User` / `UserProfile` record used by app APIs | Skriptoteket |
| Skriptoteket RBAC | Contributor/admin/superuser authorization decision | Skriptoteket |

The first accepted realms are:

- `skriptoteket_standalone`
- `huleedu_school`

Additional realms or renamed vocabulary require a follow-up ADR or an explicit ADR update before
implementation treats them as stable.

### Browser Ceremony Contract

Skriptoteket browser login actions must target a browser-navigable Hule Education ceremony URL,
not `/v1/auth/login` or any other POST-only JSON/API route.

The ceremony contract must include:

- `app=skriptoteket`, or an equivalent signed/app-registered input understood by the gateway
- a return target that is restricted to allowed Skriptoteket origins and preserves `next`
- a selected or defaulted product identity realm
- explicit account-linking behavior when a browser session can represent more than one realm

Skriptoteket may keep `/auth/login?next=...` as an app-local interruption or transition route, but
it must not collect passwords or become a second local browser-auth ceremony.

### Realm-Aware Signed Context Contract

The current `InternalIdentityContextV1` accepted for `PR-0255` remains valid only as the
HuleEdu-context foundation for existing HuleEdu-linked projections. Realm-aware implementation must
extend or version that context before `ST-28-04` / `PR-0254` can claim final login proof.

The realm-aware signed downstream context must define:

- stable subject id
- active app, such as `skriptoteket`
- active product identity realm
- stable realm subject id, which is the subject inside the active product identity realm
- optional linked identity ids
- optional tenant/org context when the user operates inside a school context
- claims trusted enough for safe first-time Skriptoteket projection creation, if the login ceremony
  provisions access

The gateway context must keep verification semantics from `PR-0255`: signed payload, issuer,
audience, key id, expiry, clock skew, and fail-closed handling remain required.

`org_id` and `tenant_id` cannot remain globally required for the `skriptoteket_standalone` realm
unless the provider explicitly supplies neutral standalone values with documented semantics. School
context is optional product context, not a prerequisite for Skriptoteket standalone login.

### Projection and RBAC Contract

Skriptoteket must resolve projections by a realm-aware identity key, not by realm-ambiguous `sub`
alone. The target projection key is:

```text
(product_identity_realm, realm_subject_id)
```

Until the data model is migrated, existing `AuthProvider.HULEEDU` plus `external_id=<sub>` lookup
may remain as the `huleedu_school` compatibility path accepted by `PR-0255`, but new
Skriptoteket-standalone implementation must not encode `sub` as a universal projection key.

First-time projection creation is allowed only when the signed context carries sufficient
provisioning claims, including at minimum:

- verified email or an explicitly non-email subject policy accepted by the product owner
- email verification or equivalent assurance state
- display/profile fields needed for the local `UserProfile`
- active product identity realm
- active app
- realm subject id

If those claims are missing or untrusted, Skriptoteket must fail closed into deliberate
local-access-required UX and must not fabricate a local user.

Hule Education roles, grants, feature flags, tenant, and org context remain provider/session
metadata unless a later ADR explicitly maps them into Skriptoteket authorization. Contributor,
admin, and superuser checks continue to use local `User.role`.

### Rejected Options

The following options are rejected:

- certifying a HuleEdu-school-only login path as final Skriptoteket login
- reintroducing Skriptoteket-local browser sessions, CSRF, or password collection as a bridge
- using browser bearer storage or direct browser calls to Identity
- linking HuleEdu school and Skriptoteket standalone identities by matching email alone
- deriving Skriptoteket RBAC from generic Hule Education provider roles

## Non-Decisions

No separate non-decisions is stated in the source.

## Consequences


`ST-28-04` / `PR-0254` must not certify a HuleEdu-school-only login path as the
final Skriptoteket login proof. It should wait until this ADR is accepted and
the browser ceremony/projection stories below define what is being proved.

Local `ST-28-04` proof must consume the HuleEdu `TASK-0325` local/non-production
Gateway lane: exact loopback origins, HuleEdu login UI on `5174`, protected
Skriptoteket `/api` traffic routed through Gateway, and local-only Gateway
public-key verification. Host-run Vite may set
`VITE_DEV_PROXY_TARGET=http://localhost:8080` or the all-127 equivalent; the
normal Docker frontend service sets
`VITE_DEV_PROXY_TARGET=http://huleedu_api_gateway_service:8080` and
`VITE_DEV_BACKEND_PROXY_TARGET=http://skriptoteket_web:8000` so public
`/api/v1/public/...` bootstrap routes remain directly served by Skriptoteket.
Public `https://api.hule.education` rejecting loopback `return_to` values
remains the correct production behavior.

Skriptoteket must not reintroduce local browser auth as a bridge. Registration,
password reset, email verification, and account linking remain Skriptoteket
product concerns, but the browser ceremony and session authority live in Hule
Education Gateway/Identity.

Projection and RBAC stay app-local. Hule Education proves browser identity and
active realm; Skriptoteket decides whether that identity has a local projection
and which local role it has.

Observability must move from local browser-session gauges to gateway/session,
identity-realm, projection, and local RBAC outcomes.
