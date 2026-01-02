---
type: epic
id: EPIC-09
title: "Security hardening for production deployment"
status: active
owners: "agents"
created: 2025-12-17
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
