---
type: runbook
id: RUN-observability
title: "Runbook: Observability Overview"
status: active
owners: "olof"
created: 2025-12-29
updated: 2025-12-29
system: "skriptoteket"
---

Entry point for observability in Skriptoteket. This runbook links to focused guides for logging, metrics, tracing, and
Grafana usage.

Reference: `docs/reference/reports/ref-external-observability-integration.md`.

## Access (Home Server)

| Service | URL | Notes |
|---------|-----|-------|
| Grafana | https://grafana.hemma.hule.education | Credentials in `~/apps/skriptoteket/.env` |
| Prometheus | https://prometheus.hemma.hule.education | Basic auth password in `~/apps/skriptoteket/.env` |
| Jaeger | https://jaeger.hemma.hule.education | Basic auth (user `admin`, password `JAEGER_BASIC_AUTH_PASSWORD`) |

For container lifecycle (start/stop/restart), see `docs/runbooks/runbook-home-server.md`.

## Triage Flow (Fast Path)

1) **Health check**: confirm `/healthz` is responsive.
2) **Metrics**: check request rate/latency and session file gauges.
3) **Logs**: filter by correlation ID and error code.
4) **Trace**: if enabled, jump to Jaeger and inspect spans.

## Alerts (Prometheus)

Prometheus rules are loaded, but there is no Alertmanager in this stack yet. Alerts are visible in the Prometheus UI:

1) Open https://prometheus.hemma.hule.education
2) Go to **Alerts**
3) Inspect **Pending/Firing** alerts and their labels/annotations

### Alert response (quick playbooks)

- `SkriptoteketDown` (critical): check `docker ps`, inspect `skriptoteket-web` logs, restart via `compose.prod.yaml` if needed.
- `SkriptoteketHighErrorRate` (warning): use Grafana HTTP dashboard to identify endpoint → pivot to Loki logs by `correlation_id`/`trace_id` → open Jaeger trace.
- `SkriptoteketHighLatency` (warning): identify slow endpoint in Grafana → inspect trace spans in Jaeger for the slow path → correlate to logs.
- `SkriptoteketSessionFilesQuota` (warning): confirm `skriptoteket_session_files_bytes_total` and run the session-file cleanup commands if appropriate.

## End-to-End Verification (Grafana ↔ Loki ↔ Jaeger)

Notes:

- `/healthz` and `/metrics` are excluded from tracing; use an API route (e.g. `/api/v1/auth/me`) when you need a trace.
- Grafana correlation depends on pinned datasource UIDs: `prometheus`, `loki`, `jaeger` (see provisioning).

Minimal smoke (from `hemma`):

```bash
CID="$(python3 -c 'import uuid; print(uuid.uuid4())')"
curl -sS -o /dev/null -w "%{http_code}\n" -H "X-Correlation-ID: ${CID}" \
  https://skriptoteket.hule.education/api/v1/auth/me
```

Then in Grafana Explore:

1) Search Loki logs for `${CID}`.
2) Click **View Trace** on the extracted `trace_id` field → Jaeger opens.
3) In Jaeger, click **View Logs** → Loki opens with the trace filter.

## Runbooks

- Logging + correlation: `docs/runbooks/runbook-observability-logging.md`
- Metrics + Prometheus: `docs/runbooks/runbook-observability-metrics.md`
- Grafana dashboards + data sources: `docs/runbooks/runbook-observability-grafana.md`
- Tracing + Jaeger: `docs/runbooks/runbook-observability-tracing.md`
