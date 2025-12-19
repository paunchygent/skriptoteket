---
type: epic
id: EPIC-09
title: "Security hardening for production deployment"
status: active
owners: "agents"
created: 2025-12-17
outcome: "Skriptoteket is hardened against common web vulnerabilities with defense-in-depth at nginx and application layers."
---

## Scope

- **HTTP security headers** via nginx reverse proxy (HSTS, X-Frame-Options, etc.).
- **Content-Security-Policy** (CSP) tuned for HTMX + CodeMirror + Google Fonts.
- **Firewall hygiene** and removal of stale UFW rules.
- **Docker socket security** review and documentation.
- **Future:** rate limiting, CSRF audit, session hardening.

## Stories

- ST-09-01: HTTP security headers via nginx (HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy)
- ST-09-02: Content-Security-Policy (CSP) implementation for HTMX/CodeMirror
- ST-09-03: Firewall audit and cleanup (remove stale rules)

## ADRs

- ADR-0021: HTTP security headers via nginx reverse proxy

## Risks

- CSP breaking HTMX/CodeMirror functionality (mitigate: browser devtools testing, gradual rollout with report-only mode).
- HSTS lock-in if cert expires (mitigate: certbot auto-renewal verified).
- Docker socket mount blast radius (documented in ADR-0013; future mitigation: dedicated runner service).

## Dependencies

- nginx reverse proxy on home server.
- Let's Encrypt certificate auto-renewal.
- Browser testing for CSP (Phase 2).
