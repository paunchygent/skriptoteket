---
type: pr
id: PR-0171
title: "ST-09-08 Hemma edge observability and reserved-host lockdown"
status: ready
owners: "agents"
created: 2026-03-30
updated: 2026-03-30
stories:
  - "ST-09-08"
tags: ["ops", "security", "deploy", "nginx", "observability"]
acceptance_criteria:
  - "Hemma deploys the repo-side hardening patch and production env values for `ALLOWED_HOSTS` plus the exact trusted nginx-proxy CIDR/IP."
  - "The live public edge no longer exposes `/metrics` anonymously."
  - "Reserved hosts `hule.education`, `api.hule.education`, and `ws.hule.education` no longer fall through to the Skriptoteket backend."
  - "Post-deploy curl proofs are captured for `/docs`, `/openapi.json`, `/metrics`, `/healthz`, and the reserved hosts."
---

## Problem

The local code hardening slice is not enough on its own. Hemma still needs the
deploy/runtime follow-through: correct production env values, observability edge
restriction, and explicit reserved-host ownership at nginx-proxy.

## Goal

Turn the verified repo-side hardening into actual live edge protection on Hemma
and record the before/after evidence.

## Non-goals

- Reworking the app/runtime hardening logic already covered by ST-09-07
- Expanding into unrelated identity allowlist work or planner feature work
- Changing the approved observability policy away from "public minimal
  healthz + protected metrics" without a new decision checkpoint

## Implementation plan

1. Deploy the current repo-side hardening patch to Hemma.
2. Set explicit production env values for:
   - `ALLOWED_HOSTS`
   - `TRUST_PROXY_HEADERS`
   - `TRUSTED_PROXY_CIDRS`
   - `HEALTHZ_DETAILED_RESPONSE=false`
   - `METRICS_IDENTITY_GAUGES_ENABLED=false`
3. Move `/metrics` behind the chosen edge protection model.
4. Add placeholder ownership for the reserved hosts so they do not route to the
   Skriptoteket container by accident.
5. Re-run the original public-edge verification curls and record the results in
   `.agents/handoff.md`.

## Test plan

- `ssh hemma 'cd ~/apps/skriptoteket && docker compose -f compose.prod.yaml config >/dev/null'`
- `ssh hemma 'cd ~/apps/skriptoteket && docker compose -f compose.prod.yaml up -d --build web worker'`
- Public-edge verification:
  - `curl -sS -D - -o /dev/null https://skriptoteket.hule.education/docs`
  - `curl -sS -D - -o /dev/null https://skriptoteket.hule.education/openapi.json`
  - `curl -sS -D - -o /dev/null https://skriptoteket.hule.education/metrics`
  - `curl -sS https://skriptoteket.hule.education/healthz`
  - `curl -k -sS -D - -o /dev/null https://hule.education`
  - `curl -k -sS -D - -o /dev/null https://api.hule.education`
  - `curl -k -sS -D - -o /dev/null https://ws.hule.education`

## Rollback plan

- Restore the previous Hemma compose/env state and nginx-proxy placeholder
  claims if the deploy blocks legitimate traffic.
- Keep the repo-side patch intact; only roll back live edge changes that prove
  incompatible during the post-deploy check.
