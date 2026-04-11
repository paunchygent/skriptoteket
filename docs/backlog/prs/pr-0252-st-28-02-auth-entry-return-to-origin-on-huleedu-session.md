---
type: pr
id: PR-0252
title: "ST-28-02 auth entry return-to-origin on HuleEdu session"
status: ready
owners: "agents"
created: 2026-04-10
updated: 2026-04-10
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

- Run focused router/auth-entry tests.
- Run `pdm run fe-type-check`.
- Run `pdm run docs-validate`.

## Rollback Plan

Revert the interruption/handoff changes and keep the cutover behind the existing local auth-entry
contract until the shared-session flow is corrected.
