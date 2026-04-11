---
type: pr
id: PR-0252
title: "ST-28-02 auth entry return-to-origin on HuleEdu session"
status: done
owners: "agents"
created: 2026-04-10
updated: 2026-04-11
stories:
  - "ST-28-02"
tags: ["frontend", "auth", "routing", "handoff"]
acceptance_criteria:
  - "Given `/auth/login?next=...` is the canonical Skriptoteket auth-entry contract, when a protected route interrupts under the HuleEdu session model, then the intended destination is preserved through the shared auth ceremony and resumed afterward."
  - "Given a HuleEdu-owned session expires or is revoked, when Skriptoteket detects invalid session state, then recovery remains page-based and route-preserving rather than falling back to app-local modal or legacy `/login` behavior."
  - "Given authentication may complete through a HuleEdu top-level handoff, when the browser returns to Skriptoteket, then route sanitization and continuation handling remain governed by the existing `ST-32-10` contract."
---

## Problem

The session authority changes, but Skriptoteket's user-facing interruption and return-to-origin
contract must remain stable.

## Goal

Adapt auth interruption, login continuation, and invalid-session recovery to the HuleEdu-owned
session model without reopening local auth ownership.

## Result

`PR-0252` is implemented as a narrow frontend/routing slice.

The shipped behavior keeps `/auth/login?next=...` as the canonical Skriptoteket auth-entry
contract under the HuleEdu-owned session model:

- direct protected-route entry with an anonymous HuleEdu shared session routes to
  `/auth/login?next=/editor`;
- app-local `401` recovery on a protected route clears local auth state and returns to
  `/auth/login?next=/editor` instead of modal state or `/login`;
- a top-level return to `/auth/login?next=/editor` with an authenticated HuleEdu shared session
  resumes `/editor` after the real app-continuation route hydrates the Skriptoteket-local
  projection.

The live proof uses a real backend, real database projection, signed HuleEdu identity context,
Vite `/api` proxy, and mocked HuleEdu shared-session/CSRF browser edge. Shared Playwright helpers
now live in `scripts/_playwright_huleedu_auth.py` so `PR-0252` and `PR-0255` targeted proofs do
not import from one another or duplicate the signed-context setup.

## Non-goals

- Reintroducing `/login`.
- Reintroducing modal-first auth as the target contract.
- Implementing the HuleEdu authentication ceremony itself.

## Implementation Plan

1. Audit guards, auth-entry helpers, and invalid-session recovery paths created by `ST-32-10`.
2. Wire protected-route interruption to the shared-session state from `PR-0251`.
3. Preserve sanitized `next` handling across the HuleEdu handoff and return.
4. Add focused route/auth tests for direct protected entry, expired-session recovery, and signed-out
   auth-entry detours.

## Test Plan

- `pdm run fe-test -- --run src/router/index.spec.ts src/components/auth/AuthLoginPanel.spec.ts src/views/AuthLoginView.spec.ts src/composables/auth/authEntryNavigation.spec.ts src/App.spec.ts`
- `pdm run fe-test -- --run src/api/sharedAuth.spec.ts src/stores/auth.spec.ts src/api/client.spec.ts`
- `pdm run python -m py_compile scripts/_playwright_huleedu_auth.py scripts/playwright_pr_0252_auth_return_to_origin.py scripts/playwright_pr_0255_auth_bootstrap.py`
- `pdm run fe-type-check`
- `pdm run db-upgrade`
- `ARTIFACTS_ROOT=.artifacts/local-tool-artifacts pdm run pr-0252-auth-return --start-backend --start-vite`
- `pdm run typecheck`
- `pdm run docs-validate`

## Rollback Plan

Revert the interruption/handoff changes and keep the cutover behind the existing local auth-entry
contract until the shared-session flow is corrected.
