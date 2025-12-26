---
type: review
id: REV-EPIC-17
title: "Review: Observability Visualization and Operations"
status: pending
owners: "agents"
created: 2025-12-26
reviewer: "lead-developer"
epic: EPIC-17
adrs: []
stories:
  - ST-17-01
  - ST-17-02
  - ST-17-03
  - ST-17-04
  - ST-17-05
---

## TL;DR

Extend the observability foundation (EPIC-07) with operational tooling: Grafana dashboards for HTTP metrics, Prometheus alerting rules for service health, and public Jaeger access for trace investigation without SSH tunnels.

## Problem Statement

Operators cannot effectively monitor Skriptoteket health:

1. **No HTTP visibility** - Only session files dashboard exists; no request/error/latency metrics
2. **No alerting** - Must manually check Prometheus; no proactive notification of issues
3. **Jaeger requires SSH** - Trace investigation requires tunnel setup, slowing incident response

## Proposed Solution

1. Verify existing Grafana datasource provisioning works end-to-end
2. Create HTTP metrics dashboard (request rates, error rates, latency percentiles)
3. Define Prometheus alerting rules for critical conditions
4. Expose Jaeger via nginx-proxy with SSL
5. Update runbooks with alerting operations and new access patterns

**Architecture:** Builds on EPIC-07 foundation and ADR-0026 observability stack. No new ADRs required.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/epics/epic-17-observability-visualization-and-operations.md` | Scope in/out, risks | 3 min |
| `docs/backlog/stories/story-17-01-grafana-datasource-verification.md` | Verification criteria | 2 min |
| `docs/backlog/stories/story-17-02-http-metrics-dashboard.md` | Panel definitions, queries | 3 min |
| `docs/backlog/stories/story-17-03-prometheus-alerting-rules.md` | Rule definitions, thresholds | 4 min |
| `docs/backlog/stories/story-17-04-jaeger-public-access.md` | Security implications | 2 min |
| `docs/backlog/stories/story-17-05-runbook-verification.md` | Runbook completeness | 2 min |

**Total estimated time:** ~16 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| No Alertmanager | Keep scope minimal; alerts visible in Prometheus UI; notifications deferred | [ ] |
| Jaeger without auth | Traces are internal operational data; add auth if abuse detected | [ ] |
| 500MB session files threshold | Matches cleanup TTL behavior; prevents disk pressure | [ ] |
| P99 latency > 2s as warning | Generous threshold for initial deployment; tune based on observation | [ ] |

## Review Checklist

- [ ] EPIC scope is appropriate (not too broad, not too narrow)
- [ ] Stories have testable acceptance criteria
- [ ] Alert thresholds are reasonable for production
- [ ] Jaeger public access security is acceptable
- [ ] Risks are identified with mitigations

---

## Review Feedback

**Reviewer:** @[reviewer-name]
**Date:** YYYY-MM-DD
**Verdict:** pending

### Required Changes

[List specific changes needed, or "None" if approved]

### Suggestions (Optional)

[Non-blocking recommendations]

### Decision Approvals

- [ ] No Alertmanager
- [ ] Jaeger without auth
- [ ] 500MB session files threshold
- [ ] P99 latency > 2s as warning

---

## Changes Made

[Author fills this in after addressing feedback]

| Change | Artifact | Description |
|--------|----------|-------------|
