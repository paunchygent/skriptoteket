---
type: pr
id: PR-0122
title: "Klassrumskartan: seating export production wiring and Hemma deploy orchestration"
status: done
owners: "agents"
created: 2026-03-24
updated: 2026-03-24
stories:
  - "ST-26-01"
tags: ["backend", "ops", "deployment", "klassrumskartan", "export", "sir-convert-a-lot"]
acceptance_criteria:
  - "Production wiring includes the full Sir Convert-a-Lot export dependency contract: base URL, API key, and callback base URL."
  - "A canonical Hemma deploy or bring-up action for Skriptoteket explicitly verifies or restarts Sir Convert-a-Lot before declaring Klassrumskartan seating export ready, and it fails closed if Sir Convert cannot be verified healthy."
  - "Hemma runbooks and env examples document the seating export dependency clearly enough that operators do not discover missing wiring only by clicking `Exportera` in production."
  - "Post-deploy verification includes one mandatory callback-capable seating-export smoke that creates a real export job, reaches terminal success, proves callback completion, and proves Vault-backed download."
---

## Problem

The seating export lane is now a real dependency on Sir Convert-a-Lot, but the
production wiring and deployment flow do not yet treat that dependency as part
of Skriptoteket bring-up. A plain redeploy can therefore leave export disabled
or partially broken even while the main app is healthy.

## Goal

Make Klassrumskartan seating export operationally deployable on Hemma by wiring
the missing production callback configuration and by making Sir Convert-a-Lot a
checked dependency of Skriptoteket deployment/bring-up.

## Current status

- This PR documents the originally shipped Sir Convert-dependent seating export
  rollout.
- Architecture note (2026-03-26):
  - `ADR-0075` supersedes this dependency model for Klassrumskartan-owned PDF
    artifacts
  - the next seating-PDF migration should remove the Sir Convert deploy
    dependency, callback requirement, and webhook reconciliation work from the
    Klassrumskartan export path

## Non-goals

- Moving Sir Convert-a-Lot into Skriptoteket's production compose file.
- Changing the seating export API or teacher-facing export UX.
- Expanding into generic shared infra orchestration beyond what is needed for
  the seating export dependency.

## Locked design decisions

- Sir Convert-a-Lot remains a separate service boundary and is not vendored into
  `compose.prod.yaml` as an in-repo sibling service.
- Skriptoteket-side deployment orchestration should ensure or restart Sir
  Convert-a-Lot before verifying Skriptoteket export readiness.
- The canonical orchestration artifact for this slice must be one Skriptoteket
  repo-owned script or wrapper command, documented as the standard operator
  entrypoint for "bring up Skriptoteket with export dependency checks".
- That canonical deploy/bring-up command must fail closed:
  - if Sir Convert-a-Lot cannot be reached with an authenticated probe after
    restart attempts
  - if the Skriptoteket web container is missing any required Sir Convert env
    vars
  - if the callback-capable export smoke does not complete successfully
- Production config must include
  `SIR_CONVERT_A_LOT_V2_CALLBACK_BASE_URL=https://skriptoteket.hule.education`
  alongside the existing base URL and API key.
- Export readiness is not considered satisfied by generic `/healthz` alone; the
  deployment/runbook path must check the conversion dependency explicitly.
- Export readiness is not considered satisfied by env presence alone; the
  deployment/runbook path must include an authenticated Sir Convert probe plus a
  real callback-capable export smoke.
- Production rollout must include shared-webhook-binding reconciliation:
  the operator flow must either repair stale bindings/subscriptions
  automatically or fail with explicit remediation steps.

## Options considered

### Option 1: Skriptoteket-side deploy wrapper orchestrates both services

Pros:
- One operator command from the Skriptoteket repo satisfies the practical
  "bring up Skriptoteket" requirement.
- Keeps service ownership separate while still making the dependency explicit.
- Fastest path to a reliable Hemma deploy story.

Cons:
- Skriptoteket deploy logic reaches into another service repo/runtime.

### Option 2: Shared Hemma orchestration outside both repos

Pros:
- Cleaner long-term infra ownership if more services join the dependency graph.

Cons:
- Slower to land and less repo-local.
- Weaker discoverability for Skriptoteket operators right now.

## Recommendation

Choose Option 1 for this slice: a thin Skriptoteket-side deploy/bring-up wrapper
that ensures or restarts Sir Convert-a-Lot, then deploys/restarts Skriptoteket,
then runs export-capable verification.

## Canonical operator entrypoint

- This PR must introduce one canonical Skriptoteket-side operator command or
  script, committed in-repo, that is the documented path for:
  - deploy/restart Skriptoteket on Hemma
  - verify/restart Sir Convert-a-Lot as needed
  - run export-capable verification
- The locked execution model for this slice is on-host:
  - the repo-owned script lives in Skriptoteket
  - operators run it directly from `~/apps/skriptoteket` on Hemma after pull
  - it is not a laptop-side SSH wrapper
- The PR implementation must lock:
  - where that artifact lives
  - that it runs directly on Hemma from the checked-out Skriptoteket repo
  - its non-zero exit behavior when Sir Convert or export verification fails
- Ad hoc shell snippets in docs are not sufficient as the primary deploy path.

## Implementation plan

- Add the missing production callback env wiring to `compose.prod.yaml`.
- Add the callback variable to `.env.example.prod` and document the correct
  Hemma values.
- Update the Hemma/home-server runbook so seating export is treated as a
  first-class deploy dependency rather than an optional postscript.
- Add one Skriptoteket-side canonical deploy/bring-up wrapper that:
  - performs an authenticated Sir Convert probe
  - checks Sir Convert-a-Lot health or restarts it
  - deploys/restarts Skriptoteket
  - verifies the Skriptoteket container has the required Sir Convert env vars
  - checks shared-webhook-binding/subscription state and repairs it or fails
    with explicit remediation output
  - runs the mandatory callback-capable seating export smoke
- Record the canonical Hemma verification steps for operators.

## Mandatory export smoke

The readiness proof for this PR must be one canonical scripted smoke with
explicit pass/fail semantics. It must:

- create or reuse a real seating draft
- create a real seating export job
- verify the export reaches terminal `succeeded`
- prove callback completion was exercised rather than only polling fallback
- prove the finished PDF is persisted and downloadable from Vault-backed
  delivery

If this smoke is too heavy for every restart, the implementation may split it
into:

- one authenticated Sir Convert preflight in the deploy wrapper
- one mandatory post-deploy export smoke gate

But the PR must still define both clearly and document which one is mandatory at
which stage.

## Rollout and migration

- The implementation must explicitly cover already-shipped shared webhook
  bindings/subscriptions from `PR-0121`.
- The PR must define:
  - what stale state means
  - how stale bindings/subscriptions are detected
  - that the canonical deploy wrapper repairs legacy/stale seating-export
    subscriptions automatically before the smoke gate
- A production rollout is not considered complete unless this binding
  reconciliation path is exercised or explicitly verified unnecessary.

## Test plan

- Validate the production compose/env wiring locally where possible.
- Verify the Hemma web container exposes
  `SIR_CONVERT_A_LOT_V2_BASE_URL`,
  `SIR_CONVERT_A_LOT_V2_API_KEY`, and
  `SIR_CONVERT_A_LOT_V2_CALLBACK_BASE_URL`.
- Verify Sir Convert-a-Lot is reachable from the production web container with
  an authenticated probe.
- Verify the canonical deploy/bring-up command exits non-zero when Sir Convert
  stays unhealthy.
- Run the mandatory callback-capable seating export smoke on Hemma.
- Verify stale shared-webhook-binding state is repaired or causes a controlled
  failure with documented remediation.
- Run `pdm run docs-validate` after runbook/env doc updates.

## Rollback plan

- Revert the deploy wrapper and production callback wiring while preserving the
  already-shipped export code path behind the configuration guard.

## Supersession note

- This PR remains relevant as historical rollout documentation for the original
  Sir Convert seating-export lane.
- It is no longer the desired end-state for Klassrumskartan exports after
  `ADR-0075`.
