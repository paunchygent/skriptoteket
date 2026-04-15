---
type: pr
id: PR-0263
title: "ST-28-04 loopback origin parity for auth cutover closeout"
status: done
owners: "agents"
created: 2026-04-13
updated: 2026-04-13
stories:
  - "ST-28-04"
adrs:
  - "ADR-0083"
dependencies:
  - "PR-0254"
  - "REV-PR-0254"
  - "HuleEdu TASK-0325"
  - "HuleEdu TASK-0326"
  - "HuleEdu TASK-0327"
  - "PR-0261"
  - "PR-0262"
  - "REV-PR-0261"
  - "REV-PR-0262"
tags: ["auth", "playwright", "local-dev", "gateway"]
acceptance_criteria:
  - "Given `ST-28-04` closeout now requires both loopback lanes, when implementation resumes, then the current 127 failure is treated as a browser-origin contract issue rather than a one-off Playwright assertion."
  - "Given local auth cookies are host-scoped, when Skriptoteket is served from `http://127.0.0.1:5173`, then every browser-visible HuleEdu auth surface used by the ceremony, session bootstrap, CSRF, and logout resolves to the matching `127.0.0.1` Gateway/login origin without changing production URLs."
  - "Given Skriptoteket is served from `http://localhost:5173`, when the same helpers run, then they continue to resolve to the canonical `localhost` Gateway/login origin."
  - "Given protected Skriptoteket reads and writes are in scope, when `/api/v1/profile/app-continuation` and `/api/v1/profile/ai-settings` run, then they still travel through the HuleEdu Gateway proxy and never through a direct backend shortcut or Skriptoteket-owned browser auth API."
  - "Given HuleEdu owns the browser session and CSRF contract, when logout runs, then Skriptoteket may call only the HuleEdu shared-auth logout endpoint with HuleEdu CSRF and must not create local browser session cookies."
  - "Given the local proof is rerun, when `pdm run pr-0254-auth-cutover --include-127-lane --require-127-lane` completes, then both `localhost` and `127` lane summaries are `status=ok` in `manifest.redacted.json`."
  - "Given retained proof artifacts are produced, when they are inspected, then no raw URLs with sensitive query values, cookies, CSRF, JWT/signature material, signed headers, raw subject, or raw email are retained."
---

## Problem

`PR-0254` proved the canonical `localhost` lane, but closeout now requires the separate
`127.0.0.1` lane to be green as well. The failed 127 proof exposed a larger local-origin issue:
the cross-app browser contract had multiple independent URL decisions instead of one coherent
loopback policy.

The relevant browser-visible surfaces are:

- Skriptoteket auth ceremony links to HuleEdu Gateway `/auth/*`.
- HuleEdu Gateway redirects to the HuleEdu login UI.
- Skriptoteket bootstraps HuleEdu-owned `/v1/auth/session`, `/v1/auth/csrf`, and
  `/v1/auth/logout`.
- Protected Skriptoteket `/api/...` traffic must remain relative and Gateway-proxied.

Because browser cookies are host-scoped, a session established on `127.0.0.1` cannot be proven by a
later request to `localhost`. Fixing only the visible login link would leave the same class of bug in
session bootstrap, CSRF, or logout.

## Goal

Make the final local cutover proof origin-consistent across both required loopback lanes while
preserving the architecture:

- HuleEdu owns browser login, session cookies, CSRF, and logout.
- Skriptoteket owns only app continuation, local projection, local `User.role`, and local RBAC.
- HuleEdu Gateway owns protected browser `/api` proxying into Skriptoteket.

## Non-goals

- Reintroducing Skriptoteket local password/session authority.
- Calling HuleEdu Identity directly from Skriptoteket browser code.
- Adding local auth API gates in Skriptoteket.
- Making public `/api/v1/public/...` require HuleEdu Gateway/session.
- Weakening production allowlists or rewriting non-loopback production hosts.
- Retaining raw URL, cookie, CSRF, token, signed-header, subject, or email evidence.

## Review Gate

Implementation must not continue until `REV-PR-0263` is approved. The review must explicitly check
that this is a loopback-origin policy fix, not a local-auth workaround.

## Implementation Plan

1. Assess the failed required 127 proof from retained logs and browser observations. Record whether
   the failure occurs at ceremony link construction, HuleEdu login redirect, HuleEdu shared-session
   API bootstrap, Gateway-proxied app-continuation, CSRF write, or logout.
2. Introduce one Skriptoteket loopback-host alignment policy for browser-visible HuleEdu URLs:
   configured `localhost` and `127.0.0.1` HuleEdu hosts may be matched to the current Skriptoteket
   browser origin when both sides are loopback; scheme, port, path, query rules, and production hosts
   must remain unchanged.
3. Apply that policy to HuleEdu ceremony entry URLs and HuleEdu shared-auth API base URLs only.
   Leave `APP_CONTINUATION_PATH` and other protected Skriptoteket API calls relative so Vite/Gateway
   proxying remains the only protected browser `/api` lane.
4. Keep the HuleEdu Gateway redirect policy aligned with the validated `return_to` origin for local
   loopback frontend URLs, without broadening public production origins.
5. Add focused unit tests for both `localhost` and `127.0.0.1` URL resolution, including a negative
   assertion that non-loopback configured hosts are not rewritten.
6. Rerun focused Skriptoteket and HuleEdu tests for the touched URL-policy surfaces.
7. Rerun `pdm run pr-0254-auth-cutover --include-127-lane --require-127-lane` and retain the new
   `manifest.redacted.json` with both lane summaries green.
8. Update `PR-0254`, `ST-28-04`, EPIC-28, the HuleEdu launch/auth topology reference, and
   `.codex/handoff.md` only after the two-lane proof is green.

## Test Plan

- `pdm run fe-test -- --run src/api/sharedAuth.spec.ts src/components/auth/AuthLoginPanel.spec.ts`
- HuleEdu focused Gateway auth ceremony tests for local return-origin behavior.
- `pdm run pr-0254-auth-cutover --include-127-lane --require-127-lane`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run docs-validate`
- `git diff --check`

## Rollback Plan

If the loopback-origin policy weakens production URL handling or reintroduces local auth authority,
revert the implementation and keep `PR-0263` open. `PR-0254` remains green only for the canonical
`localhost` lane until the 127 lane is fixed architecturally.

## Implementation Summary (as of 2026-04-13)

`PR-0263` is complete. The retained review gate `REV-PR-0263` approved the architectural shape before
implementation continued. Skriptoteket now applies one local loopback host-parity policy to
browser-visible HuleEdu ceremony URLs and HuleEdu shared-auth API base URLs, while keeping protected
Skriptoteket `/api/...` calls relative so they continue through the HuleEdu Gateway proxy. HuleEdu
Gateway login/lifecycle redirects preserve the validated loopback `return_to` host for local
`localhost` and `127.0.0.1` lanes.

The two-lane proof is green and retained at:

```text
.artifacts/playwright-pr-0254-auth-cutover/local-nonprod/20260413T160856Z/manifest.redacted.json
```

The manifest records both `localhost` and `127` lane summaries as `status=ok`, with public bootstrap
`200`, callback final path `/editor`, missing-CSRF write `403`, CSRF-protected write `200`, logout
session status `200`, and all redaction checks passing.
