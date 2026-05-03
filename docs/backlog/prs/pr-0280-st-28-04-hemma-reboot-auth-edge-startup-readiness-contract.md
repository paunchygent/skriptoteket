---
type: pr
id: PR-0280
title: "ST-28-04 Hemma reboot auth-edge startup readiness contract"
status: done
owners: "agents"
created: 2026-05-02
updated: 2026-05-02
stories:
  - "ST-28-04"
dependencies:
  - "PR-0254"
  - "PR-0263"
  - "PR-0264"
  - "PR-0272"
  - "HuleEdu TASK-0509"
tags: ["auth", "huleedu", "hemma", "operations", "readiness", "docker"]
acceptance_criteria:
  - "Given Hemma reboots while Docker containers use `restart: unless-stopped`, when services return, then the operator contract no longer treats Docker auto-restart as proof that the HuleEdu auth/API edge started before Skriptoteket auth-dependent surfaces."
  - "Given Skriptoteket public surfaces and health can be self-healthy while `api.hule.education` is unavailable or serving the wrong certificate, when readiness is assessed, then self-health, public availability, and HuleEdu-auth readiness are reported and proven as separate states."
  - "Given public Klassrumskartan/share routes must not depend on a live HuleEdu browser session, when HuleEdu auth is unavailable after reboot, then public Skriptoteket pages either remain available or any intentional coupling is captured as a reviewed product decision before implementation."
  - "Given protected Skriptoteket APIs must enter through `https://api.hule.education/api/...`, when the HuleEdu Gateway is down, missing from the proxy, or fails TLS/SNI proof, then protected/auth-dependent Skriptoteket flows fail closed or show a degraded state without certifying direct app-host protected API access."
  - "Given the fix crosses the Skriptoteket/HuleEdu operational boundary, when HuleEdu auth-edge startup, restart-policy normalization, or provider-side readiness proof must change, then Skriptoteket consumes HuleEdu `TASK-0509` evidence instead of mutating host/systemd state, Docker daemon policy, or HuleEdu startup wrappers from this repo."
  - "Given the remediation is complete, when the post-reboot or simulated-reboot proof runs, then retained evidence includes Docker container state, `api.hule.education` TLS/SNI proof, HuleEdu Gateway health, Skriptoteket public/self-health, at least one canonical public Klassrumskartan/share URL during a HuleEdu-auth outage, and protected app-continuation through the HuleEdu edge."
---

## Problem

Skriptoteket can come back online after a Hemma reboot even when the dependent HuleEdu auth/API edge
has not started cleanly. The immediate cause is Docker host restart behavior: Skriptoteket production
containers use `restart: unless-stopped`, so Docker may restart them directly after boot without
running the repo PDM wrappers or HuleEdu staged startup sequence.

That bypasses the intended cross-repo choreography:

- HuleEdu owns `hule.education`, `api.hule.education`, shared browser auth, CSRF, logout, and
  Gateway-signed InternalIdentityContextV1.
- Skriptoteket owns `skriptoteket.hule.education`, public product surfaces, local identity
  projection, and local RBAC.
- Docker Compose `depends_on` cannot express reliable startup order across the separate HuleEdu and
  Skriptoteket compose projects after a host reboot.

The observed failure mode is therefore broader than app health. Skriptoteket may be healthy on its
own `/healthz` while the HuleEdu Gateway is absent, unhealthy, or not registered correctly in the
shared proxy. In that state, `api.hule.education` can fail TLS/SNI or route incorrectly while
Skriptoteket's public host remains available.

## Goal

Define and implement the smallest safe reboot/readiness contract for the HuleEdu-owned auth edge and
Skriptoteket auth-dependent surfaces on Hemma. The contract must preserve useful public availability,
prove HuleEdu auth readiness separately from Skriptoteket self-health, and make post-reboot operator
proof deterministic.

## Non-goals

- Making Skriptoteket's main web process refuse to boot solely because HuleEdu auth is unavailable.
- Removing public Klassrumskartan/share availability during a provider outage without a reviewed
  product decision.
- Treating Docker Compose `depends_on` as sufficient host reboot orchestration across repos.
- Certifying direct protected API calls to `https://skriptoteket.hule.education/api/...` as a
  fallback for a broken HuleEdu Gateway.
- Mutating Hemma systemd units, Docker daemon policy, or HuleEdu deploy wrappers from this repo
  without an explicit linked HuleEdu/host-operations authority.
- Logging cookies, CSRF tokens, signed headers, signatures, raw subjects, raw emails, or other
  auth-sensitive material in retained proof.

## External Authority Boundary

`PR-0280` is a Skriptoteket-owned readiness, docs, proof, and consumer-behavior slice. It may
define the expected Hemma boot-order contract and the evidence Skriptoteket needs before declaring
auth-dependent readiness, but it does not itself approve host boot orchestration or HuleEdu startup
changes.

HuleEdu `TASK-0509` is the provider-side authority for this gap. It owns the existing
`RUN-hemma-hostwide-startup-and-idle-safety` decision that restart policy must not bypass staged
startup for Tier 1 through Tier 4. Skriptoteket `PR-0280` consumes that evidence and remains scoped
to Skriptoteket-owned docs, readiness checks, degraded/fail-closed behavior, and read-only
wrapper-backed proof.

Provider-side outcome, retained in HuleEdu `TASK-0509`:

- `huleedu-reserved-host-placeholder` is stale; the live Tier 0 default host is
  `hemma-reserved-default-host`.
- HuleEdu restart-policy normalization set `skriptoteket-web`, `skriptoteket-worker`, and
  `sir_convert_a_lot_prod` to `restart=no`, while `nginx-proxy`, `acme-companion`,
  `shared-postgres`, and `hemma-reserved-default-host` remain `restart=unless-stopped`.
- A simulated Docker-runtime restart proved runtime lanes stay stopped while Tier 0 recovers.
- `pdm run run-local-pdm hemma-start-hostwide` then restored Tier 1 Skriptoteket before HuleEdu
  `prod-core`; HuleEdu retained `api.hule.education` TLS/SNI, Gateway `/healthz`, auth ceremony,
  and `https://api.hule.education/api/v1/profile` protected API proof.
- No separate host/systemd task is needed unless future evidence contradicts the
  wrapper/restart-policy contract.

## Implementation Summary

`PR-0280` closed as a docs/proof alignment slice. Skriptoteket did not add a
startup hard dependency on HuleEdu auth and did not mutate host/systemd or
Docker daemon orchestration from this repo.

The retained contract is:

- Skriptoteket `/healthz` remains self-health/liveness only.
- Public Klassrumskartan app, share, preview, PDF, and guest share-helper routes
  stay direct Skriptoteket public surfaces and do not require a HuleEdu browser
  session.
- Protected Skriptoteket APIs remain certified only through the HuleEdu Gateway
  production edge at `https://api.hule.education/api/...`.
- HuleEdu `TASK-0509` owns and completed the provider-side restart-policy,
  host-wide startup, TLS/SNI, Gateway health, auth ceremony, and protected-edge
  proof.
- No separate host/systemd task is needed from the current evidence. Create one
  only if future proof shows the wrapper/restart-policy contract cannot enforce
  post-reboot behavior.

Skriptoteket consumer proof uses focused route tests that run without HuleEdu
Gateway/auth availability:

- `tests/unit/web/test_spa_fallback.py::TestSpaFallbackResponses::test_valid_spa_routes_return_spa_shell`
  covers the canonical public app route
  `/public/apps/classroom.group-seating-studio`.
- `tests/unit/web/test_public_apps_api_routes.py` covers public-safe curated-app
  bootstrap metadata.
- `tests/unit/web/test_public_apps_classroom_planner_shares.py`,
  `tests/unit/application/apps/classroom_planner/test_public_shares.py`, and
  `tests/unit/web/apps/classroom_planner/test_share_pages.py` cover anonymous
  public guest share creation/revocation, public share reads, preview images,
  and share PDF downloads without depending on authenticated HuleEdu context.

## Test Plan

- `pdm run docs-validate`
- `pdm run handoff-validate` if `.codex/handoff.md` changes
- `pdm run skills-validate`
- `pdm run pytest -q tests/unit/web/test_spa_fallback.py::TestSpaFallbackResponses::test_valid_spa_routes_return_spa_shell tests/unit/web/test_public_apps_api_routes.py tests/unit/web/test_public_apps_classroom_planner_shares.py tests/unit/application/apps/classroom_planner/test_public_shares.py tests/unit/web/apps/classroom_planner/test_share_pages.py`
- `git diff --check`

If Skriptoteket runtime code, frontend degraded state, or auth proof helpers change, also run the
focused affected checks plus:

- `pdm run lint`
- `pdm run typecheck`
- `pdm run pr-0254-auth-cutover --include-127-lane --require-127-lane`

Hemma proof must use sanctioned wrappers. For HuleEdu-owned live checks, run from the HuleEdu repo
rather than ad hoc SSH:

- `pdm run run-local-pdm run-hemma -- <read-only status/proof command>`
- `pdm run run-local-pdm hemma-start-staged prod-core` only when the user explicitly approves
  starting/restarting the provider lane.

Retained public-edge proof should include:

- Docker container status for HuleEdu Gateway, Skriptoteket web/worker, shared Postgres, and proxy.
- `api.hule.education` TLS/SNI certificate host proof.
- HuleEdu Gateway `/healthz`.
- Skriptoteket public `/healthz`.
- Canonical public Klassrumskartan app route proof while HuleEdu Gateway/auth is unavailable.
- One existing or fixture public Klassrumskartan share URL proof while HuleEdu Gateway/auth is
  unavailable, or a reviewed product decision artifact if provider coupling is intentionally chosen.
- Protected app-continuation through `https://api.hule.education/api/...`.

## Rollback Plan

Rollback any Skriptoteket-only readiness, UI, or proof-helper change without touching local user,
projection, or session data.

If host boot orchestration changes are made through a linked HuleEdu/host task and prove unsafe,
disable only the new boot orchestration unit or wrapper hook and return to the previous manual
startup procedure. Keep the self-health/auth-readiness distinction in docs unless it is proven wrong.

## Review Notes

Review should focus on operational truth rather than just app tests. The risky false passes are:

- marking Skriptoteket healthy because `/healthz` is green while `api.hule.education` is broken;
- relying on Docker auto-restart as though it reruns HuleEdu staged startup;
- adding a hard Skriptoteket startup dependency that unnecessarily removes public/share availability;
- accepting app-host protected API shortcuts as a workaround for Gateway absence;
- retaining proof artifacts with auth-sensitive material.
