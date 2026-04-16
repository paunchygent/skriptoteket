---
type: pr
id: PR-0261
title: "ST-28-12 login register reset affordance and redirect contract"
status: done
owners: "agents"
created: 2026-04-13
updated: 2026-04-16
stories:
  - "ST-28-12"
adrs:
  - "ADR-0083"
dependencies:
  - "ST-28-08"
  - "ST-28-09"
  - "ST-28-11"
  - "PR-0260"
  - "HuleEdu TASK-0327"
  - "REV-TASK-0327-01"
tags: ["auth", "frontend", "redirects", "lifecycle"]
acceptance_criteria:
  - "Given `PR-0260` is done and HuleEdu `REV-TASK-0327-01` is approved, when implementation starts, then this PR consumes the accepted provider contract and exposes the Skriptoteket consumer probe route needed by HuleEdu `TASK-0327` final live apply."
  - "Given a signed-out user opens Skriptoteket, when they reach the auth entry page, then they can choose to sign in, create an account, or reset a password using clear user-facing Swedish copy."
  - "Given the user chooses any auth action, when Skriptoteket builds the HuleEdu URL, then it targets the action-specific page directly, sends `app=skriptoteket`, `product_identity_realm=skriptoteket_standalone`, the approved callback, and a safe `next` value."
  - "Given the user clicks login, create account, forgot password, verification, or reset links, when the first interactive page loads, then it is the requested action page and not a generic HuleEdu landing, product hub, or chooser page."
  - "Given HuleEdu Gateway calls the Skriptoteket consumer probe through the same-origin Gateway proxy, when signed `InternalIdentityContextV1` headers are valid, then Skriptoteket returns only sanitized decoded claim proof and never echoes raw signed headers, signatures, cookies, CSRF, session ids, JWT material, or token-bearing values."
  - "Given a hostile, looping, or cross-origin `next` is supplied, when the auth URL is built, then Skriptoteket drops it and returns to a safe app route."
  - "Given HuleEdu completes registration, verification, login, or reset, when the browser returns to `/auth/callback`, then Skriptoteket resumes the intended route through shared-session bootstrap."
  - "Given an anonymous or interrupted browser lands directly on `/auth/callback`, when no HuleEdu session is present, then Skriptoteket retries the HuleEdu login handoff once and then shows explicit recovery copy with a primary `Logga in igen` action instead of the generic auth-entry fallback."
  - "Given the UI communicates failures, when continuation cannot complete, then the message tells the user what to try next without exposing realm, projection, token, or provider diagnostics."
---

## Problem

Provider lifecycle routes exist, but the product-facing auth entry must be
shaped for real users. The app should not expose implementation words, route
users through generic HuleEdu pages, or leave users guessing whether they need
to sign in, create an account, or reset a password.

## Goal

Make Skriptoteket's auth entry and redirect contract production-ready for the
HuleEdu-owned standalone lifecycle while preserving safe `next` continuation.

## Non-goals

- Creating HuleEdu registration, verification, or reset handlers.
- Creating local projection bootstrap accounts; that belongs to `PR-0260`.
- Proving the whole real-inbox lifecycle end to end; that belongs to `PR-0262`.
- Reintroducing local Skriptoteket browser-auth APIs.

## Implementation Gate

Implementation started because:

- Skriptoteket `PR-0260` is implemented and its local proof role matrix exists.
- HuleEdu `REV-TASK-0327-01` is approved, so the provider implementation
  contract is accepted.

This gate is now resolved. HuleEdu reran `TASK-0327` live apply against the
Skriptoteket probe route added by this PR and retained a final `status=ok`
artifact:

```text
/Users/olofs_mba/Documents/Repos/huledu-reboot/.artifacts/skriptoteket-lifecycle-proof/dev/skriptoteket-lifecycle-proof-apply-20260413T125336Z.json
```

The HuleEdu artifact covers rerun-safe account handling, reset delivery and
consumption, login, `GET /v1/auth/session`, direct action landing, and the
approved sanitized signed-context probe shape from
`/api/v1/diagnostics/huleedu-internal-identity`. It does not require raw
signed-context email or raw `realm_subject_id` in the retained signed-context
proof.

If the final HuleEdu rerun changes any path, required field, or token rule
below, update this PR and request re-review before closing it.

## HuleEdu Action Matrix

All browser-navigable lifecycle links must target the HuleEdu Gateway/UI
origin. The default public origin is `https://api.hule.education`; local proofs
may replace only the origin through the approved HuleEdu local Gateway lane.
Every action sends `app=skriptoteket`,
`product_identity_realm=skriptoteket_standalone`, and
`return_to=<Skriptoteket origin>/auth/callback`. Safe `next` is a same-origin
Skriptoteket route string; hostile, cross-origin, protocol-relative, login, or
callback loops are dropped.

| Action | Skriptoteket source | HuleEdu path | Token rule | Expected first interactive page |
|--------|---------------------|--------------|------------|---------------------------------|
| Login | `/auth/login` auto-handoff and visible login buttons | `/auth/login` | No token accepted or forwarded | Login form/page for the Skriptoteket app realm |
| Create account | `/register` and "Skapa konto" affordances | `/auth/register` | No token accepted or forwarded | Registration form/page for the Skriptoteket app realm |
| Password-reset request | `/forgot-password` and "Glömt lösenordet?" affordances | `/auth/password-reset` | No token in product-originating request links | Password-reset request form/page |
| Password-reset completion | `/reset-password?token=<redacted>` and reset email links | `/auth/password-reset` | `token` is required for completion, forwarded to HuleEdu, and redacted from artifacts | New-password completion form/page |
| Email verification | `/verify-email?token=<redacted>` and verification email links | `/auth/email-verification` | `token` is required for verification, forwarded to HuleEdu, and redacted from artifacts | Email-verification action/confirmation page |

No canonical link in this matrix may target local browser endpoints under
`/api/v1/auth/*` or HuleEdu API endpoints under `/v1/auth/*`. Generic HuleEdu
landing pages, product hubs, or chooser pages are fallback-only for
interruptions, invalid context, expired links, or unsupported actions.

## Consumer Probe Route

Add a hidden diagnostic API endpoint under the normal Skriptoteket API surface:

```text
GET /api/v1/diagnostics/huleedu-internal-identity
```

The route exists only so HuleEdu `TASK-0327` can prove the accepted provider
contract against a real Skriptoteket consumer route through the Gateway proxy.
It is not a product feature and must not be linked from user-facing UI.

The endpoint must:

- use the same HuleEdu signed internal identity verifier as protected
  Skriptoteket APIs
- validate `active_app=skriptoteket`, an accepted product identity realm, and a
  nonblank `realm_subject_id`
- avoid local projection resolution, user provisioning, local role mutation, or
  any other persistence side effect
- return only decoded sanitized claim proof, such as status, context version,
  issuer, audience, active app, active product identity realm, booleans for
  subject/email/session claim presence, `email_verified`, roles, grants, feature
  flags, policy version, and issued/expires timestamps
- never return raw signed headers, raw encoded context, raw signatures, cookies,
  CSRF values, session ids, `jti`, raw `sub`, raw `realm_subject_id`, raw
  email addresses, verification/reset tokens, magic links, or other
  token-bearing values

Invalid or unsupported context must fail through the normal unauthorized error
mapping; it must not downgrade into a public fallback response.

## Implementation Plan

1. Audit the current auth-entry, callback, and legacy lifecycle route surfaces.
2. Update UI affordances so the visible choices map to user tasks:
   `Logga in`, `Skapa konto`, and `Glömt lösenordet?`.
3. Keep all auth actions browser-navigated through the exact action matrix
   above with `app=skriptoteket` and
   `product_identity_realm=skriptoteket_standalone`; do not send deliberate
   clicks to a generic HuleEdu landing, product hub, chooser page, local
   `/api/v1/auth/*`, or provider `/v1/auth/*` endpoint.
4. Make direct action anchors external HuleEdu action URLs. Compatibility
   routes such as `/register`, `/forgot-password`, `/reset-password`, and
   `/verify-email` may remain, but they must auto-handoff so the first
   interactive page for the deliberate action is the HuleEdu action page, not a
   local Skriptoteket interstitial.
5. Add the no-side-effect consumer probe route described above so HuleEdu can
   rerun `TASK-0327` live apply against real signed context.
6. Preserve the existing safe `next` sanitizer and extend tests for register
   and reset continuation where needed.
7. Ensure callback recovery opens the intended Skriptoteket route through the
   shared session and local projection flow.
8. Replace user-facing failure copy that names internal mechanics with plain
   action guidance, for example: "Inloggningen kunde inte slutföras. Försök igen
   eller ladda om sidan."
9. Add focused frontend tests and, where backend callback behavior is touched,
   focused backend tests.

## Test Plan

- Run the focused frontend URL-builder, lifecycle handoff, auth-entry, router,
  and recovery tests:
  `pdm run fe-test -- --run src/api/sharedAuth.spec.ts src/views/AuthLifecycleHandoffView.spec.ts src/views/AuthLoginView.spec.ts src/components/auth/AuthLoginPanel.spec.ts src/composables/auth/authEntryNavigation.spec.ts src/router/index.spec.ts`.
- The retained `pdm run pr-0261-auth-action-matrix` proof must also assert
  anonymous `/auth/callback?next=/`: first entry auto-retries HuleEdu login
  once, and a repeated anonymous callback shows `Inloggningen slutfördes inte`
  with only the primary `Logga in igen` recovery action.
- Run the focused backend probe and signed-context tests:
  `pdm run pytest -q tests/unit/web/test_huleedu_identity_context_probe_api.py tests/unit/web/test_profile_app_continuation_context_api.py`.
- Run `pdm run fe-type-check` if frontend types change.
- Run `pdm run fe-lint` if frontend code changes.
- Run `pdm run typecheck` and `pdm run lint` because this PR adds a backend API
  route.
- Run `pdm run docs-validate`.
- Run `git diff --check`.
- Implementation must add or update a live Playwright proof exposed through a
  named PDM command, expected as `pdm run pr-0261-auth-action-matrix`, that
  uses the local non-production HuleEdu Gateway lane and stores sanitized
  browser evidence under `.artifacts/playwright-pr-0261-auth-action-matrix/`.
- Live-check the auth entry in the dev SPA and record in `.codex/handoff.md`
  the observed first interactive page for login, create account,
  forgot-password, verification, and reset.
- Browser-check that login, create account, forgot password, verification, and
  reset links land directly on their action pages, allowing generic pages only
  for interruption or invalid/expired-link fallback.
- Inspect retained screenshots/manifests to confirm no raw verification tokens,
  reset tokens, magic links, cookies, credentials, or signed identity payloads
  are retained.
- HuleEdu `TASK-0327` final live apply has passed against this route. Before
  this PR closes, confirm the retained HuleEdu artifact above remains the
  accepted upstream input for `PR-0262`.

## Production Callback Remediation 2026-04-14

Production investigation found that the normal `Logga in` link still targets
the correct HuleEdu login ceremony, but stale or interrupted direct entry to
`/auth/callback?next=/` could render the same generic auth-entry page while
`GET /v1/auth/session` was anonymous. That made the callback fallback look like
an obsolete local login surface.

The remediation keeps `/auth/login` as the explicit HuleEdu handoff route and
treats `/auth/callback` as completion/recovery. Anonymous callback entry now
auto-retries HuleEdu login once with session-scoped loop protection. If the
browser returns anonymous again, Skriptoteket shows explicit recovery copy:
`Inloggningen slutfördes inte. Logga in igen för att fortsätta.` The retained
PR-0261 Playwright proof now records this anonymous callback assertion in
`manifest.redacted.json`.

## Production Provisioning-Route Remediation 2026-04-16

Production logs for a freshly recreated standalone account showed successful
HuleEdu login, `auth.projection.resolved` with `provisioned` and then
`resolved`, and `GET /api/v1/profile/app-continuation` returning `200`. The
browser was still carrying the stale continuation
`/auth/provisioning-required?from=/`, which could loop between
`/auth/provisioning-required` and `/auth/login` after the local projection was
ready.

The remediation makes `/auth/provisioning-required` a transient recovery page,
not a valid auth `next` destination. Once the user is no longer in
`provisioning_required`, the router exits to the sanitized `from` route or `/`.
Anonymous direct visits still go through `/auth/login`, but with the original
sanitized `from` route instead of the recovery route itself.

## Rollback Plan

Revert the UI and redirect helper changes, leaving the HuleEdu provider
lifecycle contract untouched. Keep `ST-28-12` open until the user-facing entry
is corrected.
