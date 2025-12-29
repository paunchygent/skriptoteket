---
type: story
id: ST-17-05
title: "Runbook updates and verification"
status: ready
owners: "agents"
created: 2025-12-26
epic: "EPIC-17"
dependencies:
  - "ST-17-01"
  - "ST-17-02"
  - "ST-17-03"
  - "ST-17-04"
acceptance_criteria:
  - "Given the observability runbook, when I read the alerting section, then I understand how to view and interpret alerts in Prometheus"
  - "Given the runbook troubleshooting section, when I follow the steps for 'HighErrorRate' alert, then I can identify the problematic endpoint and correlate with logs/traces"
  - "Given all observability components are deployed, when I make a failing request to Skriptoteket, then I can trace from Grafana dashboard -> Prometheus alert -> Loki logs -> Jaeger trace"
---

## Context

This story integrates all EPIC-17 work by updating runbooks and performing end-to-end verification.

## Runbook Sections to Add

### Alerting Operations

```markdown
## Viewing Alerts

1. Access Prometheus at https://prometheus.hemma.hule.education
2. Navigate to Alerts tab
3. View firing alerts and their current state

### Alert States

| State | Meaning |
|-------|---------|
| Inactive | Condition not met |
| Pending | Condition met, waiting for `for` duration |
| Firing | Alert active, condition met for required duration |
```

### Alert Response Procedures

```markdown
## Alert Response

### SkriptoteketDown (Critical)

1. SSH to server: `ssh hemma`
2. Check container status: `docker ps | grep skriptoteket`
3. View container logs: `docker logs skriptoteket-web --tail 100`
4. Restart if needed: `cd ~/apps/skriptoteket && docker compose -f compose.prod.yaml restart web`

### SkriptoteketHighErrorRate (Warning)

1. Open HTTP metrics dashboard in Grafana
2. Identify endpoint with high error rate
3. Check Loki logs filtered by that endpoint
4. Find trace_id and investigate in Jaeger
```

### Updated Access URLs

```markdown
| Service | URL | Auth |
|---------|-----|------|
| Grafana | https://grafana.hemma.hule.education | admin / GRAFANA_ADMIN_PASSWORD |
| Prometheus | https://prometheus.hemma.hule.education | admin / PROMETHEUS_BASIC_AUTH_PASSWORD |
| Jaeger | https://jaeger.hemma.hule.education | None (anonymous) |
```

## Verification Procedure

1. Verify all datasources connected (ST-17-01)
2. Verify HTTP metrics dashboard loads with data (ST-17-02)
3. Verify alert rules visible in Prometheus (ST-17-03)
4. Verify Jaeger accessible via public URL (ST-17-04)
5. Make a test request with known error, trace end-to-end

## Files

Modify: `docs/runbooks/runbook-observability.md`

## Notes

- Consider adding a "Quick Start" section for new operators
- Include screenshots in runbook if helpful
