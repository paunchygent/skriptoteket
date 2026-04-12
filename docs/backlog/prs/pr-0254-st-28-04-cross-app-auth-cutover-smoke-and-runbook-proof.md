---
type: pr
id: PR-0254
title: "ST-28-04 cross-app auth cutover smoke and runbook proof"
status: ready
owners: "agents"
created: 2026-04-10
updated: 2026-04-11
stories:
  - "ST-28-04"
adrs:
  - "ADR-0083"
dependencies:
  - "REV-PR-0253"
  - "PR-0253"
  - "ST-28-06"
  - "ST-28-07"
  - "ST-28-08"
  - "ST-28-09"
tags: ["auth", "playwright", "runbook", "smoke"]
acceptance_criteria:
  - "Given `ADR-0083` and the realm-aware login/projection stories are complete, when the retained smoke runs against the target environment, then a browser can authenticate through the Hule Education `app=skriptoteket` ceremony and open Skriptoteket from the returned shared session."
  - "Given Skriptoteket standalone identity is supported, when the smoke uses that realm, then protected Skriptoteket reads and writes succeed through gateway-signed context and local RBAC without HuleEdu school registration."
  - "Given HuleEdu school identity is supported for Skriptoteket, when the smoke uses that realm, then the proof distinguishes school identity, Skriptoteket projection, and local authorization."
  - "Given logout is session-authority behavior, when the user logs out from either app, then both Skriptoteket and HuleEdu become unauthenticated after refresh without recreating local Skriptoteket browser sessions."
  - "Given operators need repeatable proof, when this PR completes, then the runbook records commands, environment assumptions, artifacts, identity realm coverage, failure interpretation, and links to the HuleEdu teacher-dashboard smoke evidence."
---

## Problem

Unit and component tests cannot prove the cross-app browser contract. The cutover needs one retained
smoke and operator runbook proof that spans Skriptoteket and HuleEdu.

After the `PR-0258` realm-aware projection implementation, this PR is the next proof lane. It must
not certify a HuleEdu-school-only login as final Skriptoteket login.

## Goal

Add the final Playwright and runbook proof lane for the shared browser-session cutover, including
the Skriptoteket product identity realm behavior defined by `ADR-0083`.

## Non-goals

- Implementing earlier bootstrap, handoff, or deletion work.
- Certifying the superseded modal-first auth-entry surface.
- Implementing the Hule Education-hosted Skriptoteket login ceremony.
- Implementing standalone registration/password lifecycle.
- Implementing realm-aware projection provisioning.
- Treating the smoke as a replacement for focused tests in `PR-0251` through `PR-0253`.

## Implementation Plan

1. Consume accepted `ADR-0083` and the completed `ST-28-07` through `ST-28-09` login/projection
   contracts.
2. Add or update a dedicated Skriptoteket realm-aware auth-cutover Playwright smoke.
3. Prove browser ceremony entry, protected-route recovery, signed downstream context, projection
   resolution, CSRF write, websocket/session admission if applicable, and logout invalidation.
4. Cover Skriptoteket standalone identity and HuleEdu school identity according to the implemented
   realm matrix; explicitly record any unsupported realm as blocked rather than silently passing.
5. Update the operator runbook with exact commands, required hosts, expected artifacts, identity
   realm coverage, metrics/logs to inspect, and failure triage.
6. Record the HuleEdu teacher smoke evidence that pairs with the Skriptoteket proof.

## Test Plan

- Run the new Playwright cutover smoke against the intended local or Hemma target.
- Run focused auth tests affected by the smoke helper changes.
- Run `pdm run docs-validate`.

## Rollback Plan

Revert the smoke/runbook additions if they encode an incorrect contract, then keep `ST-28-04`
open until the cross-app proof path is corrected.
