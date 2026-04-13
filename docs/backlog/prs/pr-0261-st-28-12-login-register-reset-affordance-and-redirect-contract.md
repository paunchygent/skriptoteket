---
type: pr
id: PR-0261
title: "ST-28-12 login register reset affordance and redirect contract"
status: blocked
owners: "agents"
created: 2026-04-13
updated: 2026-04-13
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
  - "Given `PR-0260` or HuleEdu `TASK-0327` is not done, when implementation is considered, then this PR remains blocked and no auth-entry redirect code starts."
  - "Given a signed-out user opens Skriptoteket, when they reach the auth entry page, then they can choose to sign in, create an account, or reset a password using clear user-facing Swedish copy."
  - "Given the user chooses any auth action, when Skriptoteket builds the HuleEdu URL, then it targets the action-specific page directly, sends `app=skriptoteket`, `product_identity_realm=skriptoteket_standalone`, the approved callback, and a safe `next` value."
  - "Given the user clicks login, create account, forgot password, verification, or reset links, when the first interactive page loads, then it is the requested action page and not a generic HuleEdu landing, product hub, or chooser page."
  - "Given a hostile, looping, or cross-origin `next` is supplied, when the auth URL is built, then Skriptoteket drops it and returns to a safe app route."
  - "Given HuleEdu completes registration, verification, login, or reset, when the browser returns to `/auth/callback`, then Skriptoteket resumes the intended route through shared-session bootstrap."
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

Implementation MUST NOT start until:

- Skriptoteket `PR-0260` is implemented and its local proof role matrix exists.
- HuleEdu `TASK-0327` is implemented and its direct-action lifecycle route
  matrix/proof artifacts are available.

`REV-TASK-0327-01` is approved, so the provider task contract is accepted, but
the provider lifecycle implementation still belongs before this consumer UI
slice. If the implemented provider matrix changes any path, required field, or
token rule below, update this PR and request re-review before implementation.

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

## Implementation Plan

1. Audit the current auth-entry, callback, and legacy lifecycle route surfaces.
2. Update UI affordances so the visible choices map to user tasks:
   `Logga in`, `Skapa konto`, and `Glömt lösenordet?`.
3. Keep all auth actions browser-navigated through the exact action matrix
   above with `app=skriptoteket` and
   `product_identity_realm=skriptoteket_standalone`; do not send deliberate
   clicks to a generic HuleEdu landing, product hub, chooser page, local
   `/api/v1/auth/*`, or provider `/v1/auth/*` endpoint.
4. Preserve the existing safe `next` sanitizer and extend tests for register
   and reset continuation where needed.
5. Ensure callback recovery opens the intended Skriptoteket route through the
   shared session and local projection flow.
6. Replace user-facing failure copy that names internal mechanics with plain
   action guidance, for example: "Inloggningen kunde inte slutföras. Försök igen
   eller ladda om sidan."
7. Add focused frontend tests and, where backend callback behavior is touched,
   focused backend tests.

## Test Plan

- Run the focused frontend URL-builder, lifecycle handoff, auth-entry, router,
  and recovery tests:
  `pdm run fe-test -- --run src/api/sharedAuth.spec.ts src/views/AuthLifecycleHandoffView.spec.ts src/views/AuthLoginView.spec.ts src/components/auth/AuthLoginPanel.spec.ts src/composables/auth/authEntryNavigation.spec.ts src/router/index.spec.ts`.
- Run affected backend callback/auth tests if backend code changes.
- Run `pdm run fe-type-check` if frontend types change.
- Run `pdm run fe-lint` if frontend code changes.
- Run `pdm run docs-validate`.
- Run `git diff --check`.
- Implementation must add or update a live Playwright proof exposed through a
  named PDM command, expected as `pdm run pr-0261-auth-action-matrix`, that
  uses the local non-production HuleEdu Gateway lane and stores sanitized
  browser evidence under `.artifacts/playwright-pr-0261-auth-action-matrix/`.
- Live-check the auth entry in the dev SPA and record in `.agents/handoff.md`
  the observed first interactive page for login, create account,
  forgot-password, verification, and reset.
- Browser-check that login, create account, forgot password, verification, and
  reset links land directly on their action pages, allowing generic pages only
  for interruption or invalid/expired-link fallback.
- Inspect retained screenshots/manifests to confirm no raw verification tokens,
  reset tokens, magic links, cookies, credentials, or signed identity payloads
  are retained.

## Rollback Plan

Revert the UI and redirect helper changes, leaving the HuleEdu provider
lifecycle contract untouched. Keep `ST-28-12` open until the user-facing entry
is corrected.
