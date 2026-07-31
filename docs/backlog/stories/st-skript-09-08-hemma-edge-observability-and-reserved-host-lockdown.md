---
type: story
id: ST-SKRIPT-09-08
title: Hemma edge observability and reserved-host lockdown
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-09
acceptance_criteria:
- Given Hemma publishes Skriptoteket through nginx-proxy, when the public edge is
  probed for `/metrics`, then the route is no longer anonymously reachable from the
  internet and the chosen protection model matches the documented operator topology.
- Given Hemma keeps `/healthz` public, when the route is requested from the internet
  after deploy, then it returns only the public-safe minimal payload defined by the
  app/runtime hardening story.
- Given `hule.education`, `api.hule.education`, and `ws.hule.education` are reserved
  hosts, when those hosts are requested at the public edge, then they no longer fall
  through to the Skriptoteket backend and instead resolve to explicit placeholder
  ownership or another fail-closed edge behavior.
- Given Hemma trusts forwarded client IPs, when nginx-proxy forwards requests to Skriptoteket,
  then `TRUSTED_PROXY_CIDRS` is set to the exact proxy bridge IP/CIDR rather than
  a broad RFC1918 range.
- Given the deploy is complete, when the March 29, 2026 UTC reproduction curls are
  rerun against the live edge, then the current results and any residual risks are
  recorded in `.codex/handoff.md`.
retired_ids:
- ST-09-08
dependencies:
- ADR-SKRIPT-0053
- ST-SKRIPT-09-07
---

## Context
The same March 29, 2026 UTC drill confirmed that the live Hemma edge still
exposed production surfaces and routing behavior that repo-side code alone
cannot fix:

- `/metrics` returned `200` publicly and leaked sensitive business gauges
- `/healthz` returned `200` with service/version/environment/dependency detail
- reserved hosts such as `hule.education` and `api.hule.education` fell through
  to the Skriptoteket backend when TLS verification was ignored
- the already-landed app hardening patch had not yet been deployed

This story is the deploy/runtime follow-up that turns the local hardening slice
into actual public-edge protection on Hemma.

## Epic Contract Slice
The source record did not define a separate section for this package heading.

## ADR Coverage
The source record did not define a separate section for this package heading.

## Contract Inputs
The source record did not define a separate section for this package heading.

## Live Verification Plan
The source record did not define a separate section for this package heading.

## Non-Goals
The source record did not define a separate section for this package heading.

## Notes
- Use the approved observability direction from the March 30 follow-up:
  - keep `/healthz` public but minimal
  - move `/metrics` behind private/internal access or equivalent edge auth
- Use explicit placeholder host ownership for reserved hosts instead of relying
  on `DEFAULT_HOST` fallthrough
- Re-run the original drill curls verbatim after deploy so the evidence is
  directly comparable to the confirmed March 29 findings

## Decision And Assumption Ledger
The source record did not define a separate section for this package heading.

## Plan Document Review
The source record did not define a separate section for this package heading.

## Story Closeout Review
The source record did not define a separate section for this package heading.
