---
type: epic
id: EPIC-09
title: "Security hardening for production deployment"
status: active
owners: "agents"
created: 2025-12-17
updated: 2026-03-30
outcome: "Skriptoteket is hardened against common internet threats with defense-in-depth at the reverse proxy, OS, and application layers."
---

## Scope

- **HTTP security headers** via nginx reverse proxy (HSTS, X-Frame-Options, etc.).
- **Content-Security-Policy** (CSP) tuned for the Vue/Vite SPA + CodeMirror.
- **Firewall hygiene** and removal of stale UFW rules.
- **Bot/probe mitigation** at the edge (cheap drops/denies) + repeat-offender banning (Fail2ban).
- **Admin surface exposure policy**: decide whether SSH and/or observability should be VPN-gated.
- **Docker socket security** review and documentation (runner workflow).

## Stories

- ST-09-01: HTTP security headers via nginx (HSTS, X-Frame-Options,
  X-Content-Type-Options, Referrer-Policy, Permissions-Policy)
- ST-09-02: Content-Security-Policy (CSP) implementation for SPA/CodeMirror
  (superseded by SPA cutover; re-scope CSP for current asset pipeline)
- ST-09-03: Firewall audit and cleanup (remove stale rules)
- ST-09-04: Production perimeter hardening v2 (bots + VPN gating plan)
- ST-09-05: Content-Security-Policy for Vue/Vite SPA
- ST-09-06: Production curated-app visibility gate
- ST-09-07: Public-edge app/runtime hardening
- ST-09-08: Hemma edge observability and reserved-host lockdown

## ADRs

- ADR-0021: HTTP security headers via nginx reverse proxy
- ADR-0053: Production security perimeter and VPN gating (proposed)

## Risks

- CSP breaking SPA/CodeMirror functionality (mitigate: browser devtools testing, gradual rollout with report-only mode).
- HSTS lock-in if cert expires (mitigate: certbot auto-renewal verified).
- Docker socket mount blast radius (documented in ADR-0013; future mitigation: dedicated runner service).
- Locking ourselves out during VPN rollout (mitigate: staged rollout + dual access during migration + documented break-glass plan).
- Over-aggressive banning of legitimate IPs (mitigate: conservative thresholds + internal IP ignores + review via Loki).

## Dependencies

- nginx reverse proxy on home server.
- Let's Encrypt certificate auto-renewal.
- Browser testing for CSP (Phase 2).
- fail2ban on home server.
- Loki/Promtail for bot/probe analysis.

## Implementation Summary (as of 2026-03-30)

- ST-09-06 is done:
  - PR-0169 added a production-only curated app allowlist in backend settings and
    registry wiring so `demo.counter` and `games.flunk_out_frenzy` no longer
    resolve in production, while approved curated apps such as
    `classroom.group-seating-studio` remain available
  - close-out included focused pytest coverage for registry/favorites/recent-app
    omission behavior, docs validation, and a live HTTP proof against a
    production-configured local backend
- ST-09-07 is now implemented locally and reviewer-approved:
  - repo-side hardening now keeps production docs/OpenAPI disabled, minimizes
    the public health payload, suppresses identity/session gauges in production
    metrics by default, and narrows login-event client-IP trust to explicit
    proxy peers
  - the follow-up also repaired the Docker-based local dev login path by making
    `skriptoteket_web` a non-production-only allowed host
  - verification included focused pytest/ruff coverage, `compose.prod.yaml`
    validation, bootstrap-superuser login proof through `http://127.0.0.1:5173`,
    and an approved final `skriptoteket_reviewer` pass after one
    `skriptoteket_implementation_specialist` iteration
- ST-09-08 is planned as the remaining Hemma/nginx follow-through:
  - deploy the repo-side hardening patch
  - protect `/metrics` at the edge
  - claim reserved hosts explicitly so they no longer fall through to the
    Skriptoteket backend
