---
type: epic
id: EPIC-17
title: "Observability visualization and operations"
status: proposed
owners: "agents"
created: 2025-12-26
outcome: "Operators can monitor Skriptoteket health via Grafana dashboards, receive alerts for critical issues, and trace requests via public Jaeger UI"
---

## Scope

**In scope:**

- Grafana datasource provisioning verification (Prometheus, Loki, Jaeger with correlation)
- HTTP metrics dashboard (request rates, error rates, latencies by endpoint)
- User session metrics (active sessions, login rates, users by role)
- Login events audit trail (superuser-only account history, 90-day retention)
- Prometheus alerting rules (service availability, error rate thresholds, disk usage)
- Jaeger public access via nginx-proxy with SSL (jaeger.hemma.hule.education)
- Runbook updates for alerting operations

**Out of scope:**

- Alertmanager deployment (manual notification for now; Alertmanager is future enhancement)
- Custom business metrics dashboards (defer to feature-specific EPICs)
- Log-based alerting (Loki ruler requires additional infrastructure)

## Stories

- ST-17-01: Grafana datasource verification
- ST-17-02: HTTP metrics dashboard
- ST-17-03: Prometheus alerting rules
- ST-17-04: Jaeger public access
- ST-17-05: Runbook updates and verification
- ST-17-06: User session metrics
- ST-17-07: Login events audit trail

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Alert fatigue from noisy rules | Medium | Medium | Start with critical alerts only; tune thresholds after observation |
| Jaeger memory usage with public access | Low | Medium | Monitor memory; add auth if abuse detected |
| Dashboard complexity | Low | Low | Follow existing session-files dashboard pattern |

## Dependencies

- EPIC-07 (done): Observability foundation (logging, metrics endpoints, tracing)
- ADR-0026 (accepted): Observability stack infrastructure
- nginx-proxy + acme-companion (deployed): SSL and reverse proxy
