---
type: story
id: ST-17-03
title: "Prometheus alerting rules"
status: ready
owners: "agents"
created: 2025-12-26
epic: "EPIC-17"
acceptance_criteria:
  - "Given Prometheus is running, when I query for alert rules, then I see rules for ServiceDown, HighErrorRate, HighLatency, SessionFilesQuota"
  - "Given the ServiceDown rule, when skriptoteket-web is unreachable for >1 minute, then the alert fires with severity=critical"
  - "Given the HighErrorRate rule, when 5xx error rate exceeds 10% over 5 minutes, then the alert fires with severity=warning"
  - "Given the HighLatency rule, when P99 latency exceeds 2s for >5 minutes, then the alert fires with severity=warning"
  - "Given the SessionFilesQuota rule, when session files exceed 500MB, then the alert fires with severity=warning"
---

## Context

Prometheus supports alerting rules that fire when conditions are met. Without Alertmanager, alerts are visible in the Prometheus UI at `/alerts` but do not send notifications.

This story establishes baseline alerting rules for service health monitoring.

## Alert Rules

```yaml
groups:
- name: SkriptoteketAlerts
  rules:
  - alert: SkriptoteketDown
    expr: up{job="skriptoteket"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Skriptoteket is down"
      description: "The skriptoteket-web service has been unreachable for more than 1 minute."

  - alert: SkriptoteketHighErrorRate
    expr: |
      rate(skriptoteket_http_requests_total{status_code=~"5.."}[5m]) /
      rate(skriptoteket_http_requests_total[5m]) > 0.1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High 5xx error rate (>10%)"
      description: "More than 10% of requests are returning 5xx errors."

  - alert: SkriptoteketHighLatency
    expr: |
      histogram_quantile(0.99, rate(skriptoteket_http_request_duration_seconds_bucket[5m])) > 2
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "P99 latency exceeds 2 seconds"
      description: "The 99th percentile request latency has exceeded 2 seconds for 5 minutes."

  - alert: SkriptoteketSessionFilesQuota
    expr: skriptoteket_session_files_bytes_total > 524288000
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Session files exceed 500MB quota"
      description: "Session file storage has exceeded the 500MB warning threshold."
```

## Files

Create: `observability/prometheus/rules/skriptoteket-alerts.yml`

Modify: `observability/prometheus/prometheus.yml`
```yaml
rule_files:
  - "/etc/prometheus/rules/*.yml"
```

Modify: `compose.observability.yaml`
```yaml
prometheus:
  volumes:
    - ./observability/prometheus/rules:/etc/prometheus/rules:ro
```

## Notes

- Alerts without Alertmanager are view-only in Prometheus UI
- Future: Add Alertmanager for Slack/email notifications
- Tune thresholds based on observed traffic patterns
