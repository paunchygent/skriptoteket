---
type: epic
id: EPIC-28
title: "Skriptoteket auth authority cutover to HuleEdu"
status: done
owners: "agents"
created: 2026-03-28
updated: 2026-04-15
outcome: "Skriptoteket no longer owns browser auth authority locally; it consumes a HuleEdu-owned cookie-session + CSRF browser contract through the intended launch topology where `hule.education` is the HuleEdu landing page, `api.hule.education` is the shared browser auth/API edge, and `skriptoteket.hule.education` remains the Skriptoteket app host while preserving richer bootstrap and dedicated redirect-preserving auth-entry handoff."
dependencies:
  - "ADR-0009"
  - "ADR-0011"
  - "ADR-0030"
  - "ADR-0076"
  - "ADR-0082"
  - "ADR-0083"
  - "REF-huleedu-launch-surface-and-shared-auth-topology-2026-04-08"
  - "REF-hule-education-product-identity-realms-and-skriptoteket-standalone-identity"
  - "HuleEdu ADR-0039"
  - "HuleEdu TASK-0308"
  - "HuleEdu TASK-0325"
  - "HuleEdu TASK-0326"
  - "HuleEdu TASK-0327"
---

## Scope

- Cut Skriptoteket browser auth over to a HuleEdu-owned session contract exposed at
  `https://api.hule.education`.
- Freeze the cross-repo launch topology and host ownership assumptions before local cutover work:
  `hule.education` = HuleEdu landing page, `api.hule.education` = shared auth/API edge,
  `skriptoteket.hule.education` = Skriptoteket app host.
- Preserve the stronger existing Skriptoteket browser semantics:
  - cookie-session + CSRF
  - rich bootstrap document
  - dedicated `/auth/login` entry and redirect-preserving auth handoff UX
- Replace browser bootstrap from local `/api/v1/auth/me` with shared
  `/v1/auth/session`.
- Remove Skriptoteket-local browser auth ownership and assumptions once the shared contract is in
  place.
- Add an explicit cross-app smoke lane proving shared login/logout/session behavior across
  Skriptoteket and HuleEdu after the Skriptoteket product identity realm contract is accepted.
- Add explicit bootstrap proof identity and lifecycle proof lanes so final cutover does not depend
  on bulk importing fake alpha users.

## Out of scope

- OIDC provider integration as the first blocker for the cutover
- a bearer-browser transitional contract
- a permanent app-local auth proxy or bridge in Skriptoteket
- keeping two browser auth contracts alive indefinitely
- implementing the HuleEdu landing page or gateway itself inside this repo
- bulk importing the old Skriptoteket alpha education-domain users as a launch blocker

## Risks

- HuleEdu may initially deliver a session document that is too thin to preserve Skriptoteket's
  bootstrap semantics.
- Cross-origin cookie and CORS handling on `.hule.education` can break login/logout or CSRF if
  not treated as one first-class contract.
- WebSocket auth can regress into a second token lifecycle if not explicitly tied to the shared
  browser session authority.
- If local auth ownership is only partially removed, the repo can drift into a hidden dual-mode
  contract.
- If the cross-repo launch topology is not frozen first, later landing, gateway, SSO, and SEO work
  can harden around contradictory host assumptions.
- If `ST-28-04` runs before the product identity realm contract is accepted, it can accidentally
  certify a HuleEdu-school-only login path as final Skriptoteket login.
- If final proof lacks provider-owned bootstrap identities and a Skriptoteket-owned local role
  matrix, operators can pass a login-only smoke while admin/superuser access remains unproven.

## Stories

- [ST-28-05: Cross-repo launch surface and shared auth dependency freeze](../stories/story-28-05-cross-repo-launch-surface-and-shared-auth-dependency-freeze.md)
- [ST-28-01: Frontend auth store and API client cutover to HuleEdu session contract](../stories/story-28-01-frontend-auth-store-and-api-client-cutover-to-huleedu-session-contract.md)
- [ST-28-02: Auth interruption and protected-route handoff on HuleEdu-owned session](../stories/story-28-02-auth-interruption-and-protected-route-handoff-on-huleedu-owned-session.md)
- [ST-28-03: Remove local auth ownership and regenerate client contracts](../stories/story-28-03-remove-local-auth-ownership-and-regenerate-client-contracts.md)
- [ST-28-06: Product identity realm ADR and contract freeze](../stories/story-28-06-product-identity-realm-adr-and-contract-freeze.md)
- [ST-28-07: Hule Education-hosted Skriptoteket login ceremony](../stories/story-28-07-hule-education-hosted-skriptoteket-login-ceremony.md)
- [ST-28-08: Skriptoteket standalone registration and password lifecycle](../stories/story-28-08-skriptoteket-standalone-registration-and-password-lifecycle.md)
- [ST-28-09: Realm-aware projection provisioning and local RBAC](../stories/story-28-09-realm-aware-projection-provisioning-and-local-rbac.md)
- [ST-28-11: Bootstrap proof identities and projection role matrix](../stories/story-28-11-bootstrap-proof-identities-and-projection-role-matrix.md)
- [ST-28-12: Real standalone lifecycle and auth entry proof](../stories/story-28-12-real-standalone-lifecycle-and-auth-entry-proof.md)
- [ST-28-04: Cross-app auth cutover smoke and operator runbook proof](../stories/story-28-04-cross-app-auth-cutover-smoke-and-operator-runbook-proof.md)
- [ST-28-10: Auth outcome observability for realm cutover](../stories/story-28-10-auth-outcome-observability-for-realm-cutover.md)

## Implementation PR Backlog

- [PR-0250: ST-28-05 HuleEdu provider conformance ingest and cutover readiness](../prs/pr-0250-st-28-05-huleedu-provider-conformance-ingest-and-cutover-readiness.md)
- [PR-0251: ST-28-01 session bootstrap API client cutover](../prs/pr-0251-st-28-01-session-bootstrap-api-client-cutover.md)
- [PR-0252: ST-28-02 auth entry return-to-origin on HuleEdu session](../prs/pr-0252-st-28-02-auth-entry-return-to-origin-on-huleedu-session.md)
- [PR-0253: ST-28-03 local auth authority retirement and contract regeneration](../prs/pr-0253-st-28-03-local-auth-authority-retirement-and-contract-regeneration.md)
- [PR-0256: ST-28-07 Hule Education-hosted Skriptoteket login ceremony provider contract](../prs/pr-0256-st-28-07-hule-education-hosted-skriptoteket-login-ceremony-provider-contract.md)
- [PR-0257: ST-28-08 standalone registration/password lifecycle provider contract](../prs/pr-0257-st-28-08-standalone-registration-password-lifecycle-provider-contract.md)
- [PR-0258: ST-28-09 realm-aware identity projections and provisioning migration](../prs/pr-0258-st-28-09-realm-aware-identity-projections-and-provisioning-migration.md)
- [PR-0260: ST-28-11 bootstrap projection role matrix contract](../prs/pr-0260-st-28-11-bootstrap-projection-role-matrix-contract.md)
- [PR-0261: ST-28-12 login register reset affordance and redirect contract](../prs/pr-0261-st-28-12-login-register-reset-affordance-and-redirect-contract.md)
- [PR-0262: ST-28-12 real lifecycle proof smoke and runbook](../prs/pr-0262-st-28-12-real-lifecycle-proof-smoke-and-runbook.md)
- [PR-0254: ST-28-04 cross-app auth cutover smoke and runbook proof](../prs/pr-0254-st-28-04-cross-app-auth-cutover-smoke-and-runbook-proof.md)
- [PR-0263: ST-28-04 loopback origin parity for auth cutover closeout](../prs/pr-0263-st-28-04-loopback-origin-parity-for-auth-cutover-closeout.md)
- [PR-0264: ST-28-10 auth outcome observability for HuleEdu cutover](../prs/pr-0264-st-28-10-auth-outcome-observability-for-huleedu-cutover.md)

## Dependencies

- ADR-0009 defines the current local cookie-session baseline.
- ADR-0011 provides the earlier federation foundation but is too permissive for the final browser
  contract.
- ADR-0030 keeps the SPA aligned to cookie-session + CSRF expectations.
- ADR-0076 defines the new hard-break HuleEdu-owned browser auth target.
- ADR-0083 is proposed as the product identity realm correction required before final
  Skriptoteket login proof; it prevents the browser-session cutover from collapsing standalone
  Skriptoteket identity into HuleEdu school registration.
- Skriptoteket must land the dedicated `/auth/login` route contract through
  `ST-32-10` / `PR-0242` before `ST-28-02` can complete; this epic consumes that
  route contract rather than owning it.
- HuleEdu has accepted ADR-0039, completed `TASK-0308`, published the shared browser-session
  consumer conformance handoff, and publicly proved `https://skriptoteket.hule.education` against
  `https://api.hule.education` plus `wss://ws.hule.education/ws`. Skriptoteket ingested that
  provider gate through `PR-0250`; `PR-0251` may now start the consumer implementation.
- HuleEdu `TASK-0325` now owns the local/non-production shared-auth Gateway lane that `PR-0254`
  must consume before local Docker/operator proof: HuleEdu login UI on `5174`, exact dev origins
  only, protected Skriptoteket `/api` traffic through Gateway, browser-visible auth URLs on
  `http://localhost:8080`, Docker frontend proxy target
  `http://huleedu_api_gateway_service:8080` on `hule-network`, direct Docker backend target
  `http://skriptoteket_web:8000` for public `/api/v1/public/...` bootstrap traffic, and
  local-only public signing-key sharing.
- HuleEdu `TASK-0326` now owns provider proof identity bootstrap and sanitized subject export for
  Skriptoteket. Skriptoteket consumes that export in `ST-28-11` / `PR-0260` and keeps role
  assignment local. `TASK-0326` is done and deployed at HuleEdu merge commit `92419293`;
  Skriptoteket `PR-0260` is approved after remediation of the stricter export boundary and
  blocked-audit behavior.
- HuleEdu `REV-TASK-0327-01` is approved and HuleEdu `TASK-0327` is done after
  rerunning live apply against the `PR-0261` Skriptoteket diagnostics route.
  The final retained HuleEdu artifact has `status=ok` and proves direct-action
  lifecycle, session, and sanitized signed-context diagnostics for
  `skriptoteket_standalone`. Skriptoteket consumes that contract in `ST-28-12`
  / `PR-0261` / `PR-0262`.
- The 2026-04-13 product decision is to avoid bulk importing fake old education-domain alpha
  accounts. One-off legacy linking can be planned later, but it is not a prerequisite for launch
  proof.
- The cross-repo launch topology and upstream edge ownership are now recorded in
  [REF-huleedu-launch-surface-and-shared-auth-topology-2026-04-08](../../reference/ref-huleedu-launch-surface-and-shared-auth-topology-2026-04-08.md).

## Implementation Summary (as of 2026-04-15)

`ST-28-05` shipped through `PR-0250` as the HuleEdu provider conformance ingest and cutover
readiness gate. The upstream HuleEdu `TASK-0308` proof is green, no provider-side blocker remains
for Skriptoteket consumer work, and `PR-0251` is now the active consumer implementation slice under
the retained shared browser-session conformance contract. `REV-PR-0251` approved `ADR-0082`,
initially requested implementation changes for app-continuation user resolution and local
authorization projection, and now approves the `PR-0255` remediation: signed HuleEdu request context
resolves an existing Skriptoteket-local projection, provider roles remain metadata, and the
continuation/bootstrap proof runs through the real backend and Vite `/api` proxy. `ST-28-02` shipped
through `PR-0252` as the narrow auth-entry return-to-origin slice: direct protected entry,
app-local `401` recovery, and top-level return to `/auth/login?next=...` preserve the dedicated
auth-entry contract on the HuleEdu-owned session model. `ST-28-03` shipped through approved
`PR-0253` as the hard-retirement slice: local auth routes/contracts, browser-session
protocols/models/config, local-session CSRF authority, and the `sessions` table are removed;
browser app APIs now depend on signed HuleEdu-derived `require_app_*` dependencies; app-local RBAC
remains based on Skriptoteket `User.role`; missing projections fail closed into
provisioning-required UX; and the live proof exercises the browser `/api` edge through a test
gateway injector. A new product identity realm reference now corrects the planning direction:
Hule Education may own the browser edge while Skriptoteket preserves standalone product identity,
registration meaning, and local authorization. `ST-28-06` is now done through retained review
`REV-ST-28-06`, and `ADR-0083` is accepted as the contract freeze: first accepted realms are
`skriptoteket_standalone` and `huleedu_school`; browser login must use a Hule Education-hosted
`app=skriptoteket` ceremony; final proof requires realm-aware signed context and a projection key
based on `(product_identity_realm, realm_subject_id)`; and local RBAC remains `User.role`-driven.
Cross-app Docker/operator proof remains with `PR-0254` after the identity-realm implementation path
is clear. `PR-0256` / `ST-28-07` are now done after HuleEdu `TASK-0313` / `TASK-0314` cleared the
provider blocker: Skriptoteket points signed-out users at HuleEdu `GET /auth/login` with
`app=skriptoteket`, default `product_identity_realm=skriptoteket_standalone`, callback
`return_to=/auth/callback`, and safe route-level `next`; `/auth/callback` resumes protected routes;
query/hash continuation survives Vue Router normalization; helper-level `next` drops hostile or
looping values; and app continuation requires `active_app=skriptoteket`, a supported realm, and
`realm_subject_id` before projection lookup. Realm-aware projection keys still belong to `ST-28-09`.
`PR-0257` originally opened `ST-28-08` as a provider-contract gate. HuleEdu `TASK-0318` is now done
at commit `cff626aa`: the retained provider contract publishes and publicly proves Gateway-owned
browser lifecycle ceremonies for registration, password reset, and email verification with
`app=skriptoteket`, `product_identity_realm=skriptoteket_standalone`, approved return origins, safe
`next`, and token continuation. `ST-28-08` / `PR-0257` then shipped the consumer handoff surfaces
without direct browser-to-Identity calls or app-local browser auth: old `/register`,
`/forgot-password`, `/reset-password`, and `/verify-email` URLs now hand off to the
provider-approved Gateway ceremonies while preserving app, realm, return, safe `next`, and token
context. `ST-28-09` / `PR-0258` is now done: Skriptoteket has a dedicated local identity projection
table keyed by `(product_identity_realm, realm_subject_id)`, legacy
`auth_provider=huleedu` + `external_id` rows preflight/backfill into `huleedu_school` projections
before `users.external_id` is removed, first-login provisioning only trusts concrete signed HuleEdu
email/verified-email claims, UoW-owned idempotent get-or-create protects concurrent callbacks and
unique-conflict recovery, projection audit events record resolved/provisioned/blocked outcomes with
request correlation ids, newly provisioned users default to local `user`, matching email is never
inferred as account linking, and user-facing login actions open the HuleEdu ceremony directly. The
sequence is now explicit: `PR-0255` stays complete as the signed-context foundation; `ST-28-06`,
`ST-28-07`, `ST-28-08`, and `ST-28-09` are done; HuleEdu `TASK-0325` provides the local
shared-auth Gateway lane for `localhost`/`127.0.0.1` proof without weakening public production;
`ST-28-04` / `PR-0254` then runs as the final realm-aware cross-app Docker/operator proof; and
`ST-28-10` follows with auth outcome observability for gateway/session, realm, projection, and
local RBAC outcomes. On 2026-04-13 the plan was simplified: launch proof no longer depends on
bulk importing old fake alpha education-domain users. HuleEdu `TASK-0326` is now done and
deployed at merge commit `92419293`; its production bootstrap/export proof created and verified
the three approved proof accounts on Hemma. `ST-28-11` / `PR-0260` is now done:
Skriptoteket consumes sanitized HuleEdu subject exports through a production
application service and operator command, creates local HuleEdu-owned users without password
hashes, creates `identity_projections` by `(product_identity_realm, realm_subject_id)`, applies
the explicit local role matrix without bulk alpha import or email-inferred linking, requires
explicit versioned export payloads, and persists blocked apply outcomes in
`identity_projection_events`. HuleEdu `REV-TASK-0327-01` is approved, and
HuleEdu `TASK-0327` is now done after rerunning live apply against the `PR-0261`
no-side-effect consumer probe route. `PR-0261` owns the user-facing
direct-action auth entry and hidden sanitized diagnostics endpoint. `PR-0262`
now consumes the final HuleEdu artifact as upstream provider proof, then retains
Skriptoteket-side evidence for callback continuation, local projection, and
local role observation before final `PR-0254`.

`ST-28-12` is now done. `PR-0261` and `PR-0262` produced the retained evidence
chain for real standalone lifecycle entry: HuleEdu owns provider lifecycle and
session proof, Skriptoteket exposes only the sanitized consumer diagnostics
surface, and the final local proof demonstrates callback continuation,
realm-aware projection reuse, local contributor role observation, and artifact
redaction.

`ST-28-04` / `PR-0254` / `PR-0263` are now done on both required local loopback lanes. The
final proof consumes retained upstream artifacts, then certifies the browser path
from Skriptoteket public route and auth entry through HuleEdu Gateway/login,
Gateway-proxied protected read/write, signed app-continuation, local projection,
local `User.role` RBAC, CSRF, and shared logout invalidation. The latest retained
manifest is
`.artifacts/playwright-pr-0254-auth-cutover/local-nonprod/20260413T160856Z/manifest.redacted.json`.
It records both `localhost` and `127` lane summaries as `status=ok`.

`ST-28-10` shipped through approved `PR-0264`. Skriptoteket now emits bounded auth outcome
counters and sanitized structured logs for signed internal identity verification,
realm-aware projection/provisioning outcomes, and local RBAC denials. The 2026-04-15
`changes_requested` follow-up is resolved: local RBAC denial recording now lives at the central web
`DomainError` boundary, covering dependency guards and route/application-handler role guards after
`require_app_user_api` without changing authorization behavior. The logging and metrics runbooks
now start auth triage from a known `X-Correlation-ID` and explicitly hand
HuleEdu-owned browser session, CSRF, logout, and provider lifecycle failures back to the Gateway
and session logs. With `ST-28-04`, `ST-28-10`, and the loopback closeout complete, `EPIC-28` is
done as a launch-ready auth authority cutover: Skriptoteket consumes the HuleEdu-owned browser
session/product-realm ceremony while keeping local projection and RBAC ownership observable.
The final post-observability proof retained
`.artifacts/playwright-pr-0254-auth-cutover/local-nonprod/20260415T092404Z/manifest.redacted.json`
with both loopback lanes required and passing.

Post-closeout production edge clarification (2026-04-16): the local proof's
relative `/api` proxy lane is not production host policy. Production protected
Skriptoteket app APIs must enter through the HuleEdu Gateway-owned browser
auth/API edge at `https://api.hule.education/api/...`. The public
`https://skriptoteket.hule.education` host remains the Skriptoteket app and
public product origin; it must not serve signed-context protected API routes
directly unless a future ADR deliberately defines a same-origin Gateway alias.

## Planning note (2026-04-08)

The old modal-first auth-entry language is now superseded for new work by the dedicated `/auth/login`
direction planned in `ST-32-10` / `PR-0242`. This epic should be read with that updated
page-based handoff contract, not with the older modal-only assumption from `ST-11-22`.

## Sequencing note (2026-04-13)

`ST-28-05` is now the cross-repo gating story for this epic. The paced order is:

1. freeze launch topology and shared-edge ownership
2. land the dedicated `/auth/login` route contract through `ST-32-10` / `PR-0242`
3. ingest HuleEdu provider conformance and handoff through `PR-0250` (done)
4. consume the shared browser session contract in Skriptoteket through `PR-0251`
5. preserve `/auth/login` interruption and return-to-origin behavior through `PR-0252`
6. remove local browser auth ownership through `PR-0253`
7. accept the product identity realm contract through `ST-28-06` / `ADR-0083` (done)
8. implement the Hule Education-hosted Skriptoteket login ceremony through `ST-28-07` (done)
9. restore standalone registration/password lifecycle through the shared identity surface in
   `ST-28-08` / `PR-0257` (done)
10. make projection provisioning realm-aware through `ST-28-09` (done)
11. complete HuleEdu `TASK-0325` so local/non-production Gateway proof has exact dev origins,
    HuleEdu login UI on `5174`, Gateway-proxied Skriptoteket `/api` traffic with exact Gateway
    target config, and local-only signing-key sharing
12. complete HuleEdu `TASK-0326` so provider-owned proof identities and sanitized subject exports
    exist for dev and production (done at HuleEdu merge commit `92419293`)
13. consume that export in Skriptoteket through `ST-28-11` / `PR-0260`, creating local
    projections and the explicit local role matrix without bulk alpha import
    (done)
14. consume approved HuleEdu `REV-TASK-0327-01` in Skriptoteket `PR-0261`, including humane
    direct-action auth-entry copy and the hidden no-side-effect consumer probe route
    (implemented; HuleEdu final rerun completed)
15. consume the final HuleEdu `TASK-0327` `status=ok` artifact in `PR-0262`
    without retaining raw signed-context identity values
16. complete retained Skriptoteket lifecycle proof through `ST-28-12` / `PR-0262`
    for callback continuation, local projection, and local role observation
17. prove the cutover cross-app and operator-side through `ST-28-04` / `PR-0254`, then close the
    required 127 lane through `PR-0263` (done; both loopback lanes green)
18. reintroduce auth outcome observability through `ST-28-10`
