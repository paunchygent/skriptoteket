---
type: pr
id: PR-0254
title: "ST-28-04 cross-app auth cutover smoke and runbook proof"
status: ready
owners: "agents"
created: 2026-04-10
updated: 2026-04-10
stories:
  - "ST-28-04"
tags: ["auth", "playwright", "runbook", "smoke"]
acceptance_criteria:
  - "Given the shared auth cutover is implemented, when the retained smoke runs against the target environment, then a browser can authenticate through the canonical Skriptoteket `/auth/login` handoff or HuleEdu-owned equivalent and open HuleEdu authenticated from the same session."
  - "Given the shared session is active, when Skriptoteket performs a CSRF-protected write, then the write succeeds through the shared session and CSRF contract."
  - "Given logout is session-authority behavior, when the user logs out from either app, then both Skriptoteket and HuleEdu become unauthenticated after refresh."
  - "Given operators need repeatable proof, when this PR completes, then the runbook records commands, environment assumptions, artifacts, failure interpretation, and links to the HuleEdu teacher-dashboard smoke evidence."
---

## Problem

Unit and component tests cannot prove the cross-app browser contract. The cutover needs one retained
smoke and operator runbook proof that spans Skriptoteket and HuleEdu.

## Goal

Add the final Playwright and runbook proof lane for the shared browser-session cutover.

## Non-goals

- Implementing earlier bootstrap, handoff, or deletion work.
- Certifying the superseded modal-first auth-entry surface.
- Treating the smoke as a replacement for focused tests in `PR-0251` through `PR-0253`.

## Implementation Plan

1. Add or update a dedicated Skriptoteket auth-cutover Playwright smoke.
2. Prove bootstrap, protected-route recovery, CSRF write, websocket/session admission if applicable,
   and logout invalidation.
3. Update the operator runbook with exact commands, required hosts, expected artifacts, and failure
   triage.
4. Record the HuleEdu teacher smoke evidence that pairs with the Skriptoteket proof.

## Test Plan

- Run the new Playwright cutover smoke against the intended local or Hemma target.
- Run focused auth tests affected by the smoke helper changes.
- Run `pdm run docs-validate`.

## Rollback Plan

Revert the smoke/runbook additions if they encode an incorrect contract, then keep `ST-28-04`
open until the cross-app proof path is corrected.
