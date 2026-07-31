---
type: epic
id: EPIC-SKRIPT-09
title: Security hardening for production deployment
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
outcome: Skriptoteket is hardened against common internet threats with defense-in-depth
  at the reverse proxy, OS, and application layers.
retired_ids:
- EPIC-09
---

## Scope

### Source: Scope

- **HTTP security headers** via nginx reverse proxy (HSTS, X-Frame-Options, etc.).
- **Content-Security-Policy** (CSP) tuned for the Vue/Vite SPA + CodeMirror.
- **Firewall hygiene** and removal of stale UFW rules.
- **Bot/probe mitigation** at the edge (cheap drops/denies) + repeat-offender banning (Fail2ban).
- **Admin surface exposure policy**: decide whether SSH and/or observability should be VPN-gated.
- **Docker socket security** review and documentation (runner workflow).

## Epic Contract

The current epic outcome is: Skriptoteket is hardened against common internet threats with defense-in-depth at the reverse proxy, OS, and application layers.

## ADR Coverage

### Source: ADRs

- ADR-SKRIPT-0021: HTTP security headers via nginx reverse proxy
- ADR-SKRIPT-0053: Production security perimeter and VPN gating (proposed)
- ADR-SKRIPT-0081: Hemma deploy entrypoint and script-first local launcher (accepted)

## Contract Inputs

### Source: Dependencies

- nginx reverse proxy on home server.
- Let's Encrypt certificate auto-renewal.
- Browser testing for CSP (Phase 2).
- fail2ban on home server.
- Loki/Promtail for bot/probe analysis.

## Stories

### Source: Stories

- ST-09-01: HTTP security headers via nginx (HSTS, X-Frame-Options,
  X-Content-Type-Options, Referrer-Policy, Permissions-Policy)
- ST-09-02: Content-Security-Policy (CSP) implementation for SPA/CodeMirror
  (superseded by SPA cutover; re-scope CSP for current asset pipeline)
- ST-09-03: Firewall audit and cleanup (remove stale rules)
- ST-09-04: Production perimeter hardening v2 (bots + VPN gating plan)
- ST-SKRIPT-09-05: Content-Security-Policy for Vue/Vite SPA
- ST-09-06: Production curated-app visibility gate
- ST-SKRIPT-09-07: Public-edge app/runtime hardening
- ST-SKRIPT-09-08: Hemma edge observability and reserved-host lockdown
- ST-09-09: Hemma deploy entrypoint and script-first local launcher

## Epic Verification Plan

The source does not record a separate verification plan.

## Exceptions And Follow-Ups

The source records no separate approved exception or follow-up.

## Risks

### Source: Risks

- CSP breaking SPA/CodeMirror functionality (mitigate: browser devtools testing, gradual rollout with report-only mode).
- HSTS lock-in if cert expires (mitigate: certbot auto-renewal verified).
- Docker socket mount blast radius (documented in ADR-SKRIPT-0013; future mitigation: dedicated runner service).
- Locking ourselves out during VPN rollout (mitigate: staged rollout + dual access during migration + documented break-glass plan).
- Over-aggressive banning of legitimate IPs (mitigate: conservative thresholds + internal IP ignores + review via Loki).

## Notes

### Source: Implementation Summary (as of 2026-03-30)

- ST-09-06 is done:
  - PR-0169 added a production-only curated app allowlist in backend settings and
    registry wiring so `demo.counter` and `games.flunk_out_frenzy` no longer
    resolve in production, while approved curated apps such as
    `classroom.group-seating-studio` remain available
  - close-out included focused pytest coverage for registry/favorites/recent-app
    omission behavior, docs validation, and a live HTTP proof against a
    production-configured local backend
- ST-SKRIPT-09-07 is now implemented locally and reviewer-approved:
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
- ST-09-04 is now closed as a perimeter-hardening backfill/current-state record:
  - the story now serves as the canonical write-up of the already-implemented
    bot/probe mitigation posture, Loki/Grafana visibility, and VPN-gating
    decision scaffolding instead of hanging as a `ready` implementation item
- ST-SKRIPT-09-08 is planned as the remaining Hemma/nginx follow-through:
  - deploy the repo-side hardening patch
  - protect `/metrics` at the edge
  - claim reserved hosts explicitly so they no longer fall through to the
    Skriptoteket backend
- ST-09-09 is now planned as the operator-entrypoint hardening follow-up:
  - the accepted `ADR-SKRIPT-0081` decision now keeps the checked-in on-host
    deploy/readiness script as the single source of deploy truth
  - shipped local operator entrypoints now expose canonical
    `pdm run hemma-deploy` and `pdm run hemma-deploy-monitor` commands, with
    detached remote start, PID/log breadcrumbs, and a best-effort filtered
    monitor over the authoritative raw remote log
  - a live April 7, 2026 Hemma run proved the detached launcher on the real
    production lane: PID `1243606`, raw log
    `/home/paunchygent/apps/skriptoteket/.artifacts/hemma-deploy-20260407-092323.log`,
    deployed commit `94be5c23bbfb8294278cf21d3f679ee693277f73`, migrations
    applied, and seating-export smoke passed with artifacts under
    `.artifacts/pr-0146-seat-export-cutover-20260407-092323/`

## Decision And Assumption Ledger

The source does not record a separate decision and assumption ledger.

## Plan Document Review

The source does not include a plan document review record.

## Epic Closeout Review

The source does not include an epic closeout review record.
