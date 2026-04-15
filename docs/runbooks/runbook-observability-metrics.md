---
type: runbook
id: RUN-observability-metrics
title: "Runbook: Observability Metrics (Prometheus)"
status: active
owners: "olof"
created: 2025-12-29
updated: 2026-04-15
system: "skriptoteket"
---

Metrics and health endpoints exposed by Skriptoteket, plus Prometheus scrape guidance.

## Health Check Endpoint

`GET /healthz` returns HuleEdu-standard JSON:

```json
{
  "service": "skriptoteket",
  "status": "healthy|degraded|unhealthy",
  "message": "Service is healthy",
  "version": "0.2.0",
  "environment": "production",
  "checks": {
    "service_responsive": true,
    "dependencies_available": true
  },
  "dependencies": {
    "database": {"status": "healthy"}
  }
}
```

Response codes:

- `200 OK` - Service is healthy
- `503 Service Unavailable` - Service is degraded/unhealthy

Local example:

```bash
curl -s http://127.0.0.1:8000/healthz | jq
```

Production example:

```bash
ssh hemma "curl -s https://skriptoteket.hule.education/healthz" | jq
```

### SMTP down => `/healthz` 503 (prod readiness)

In production we run with `EMAIL_PROVIDER=smtp` and `HEALTHZ_SMTP_CHECK_ENABLED=true` (strict readiness).
If the SMTP provider is unreachable (or credentials are wrong), `/healthz` reports `status: degraded` and returns `503`
with a `dependencies.smtp` error (and the Docker healthcheck in `compose.prod.yaml` fails too).

Quick troubleshooting (from `hemma`):

```bash
# 1) Confirm SMTP is the reason
curl -s https://skriptoteket.hule.education/healthz | jq '.status, .dependencies.smtp'

# 2) Check non-secret SMTP config (do NOT print EMAIL_SMTP_PASSWORD)
rg -n '^(EMAIL_PROVIDER|EMAIL_SMTP_HOST|EMAIL_SMTP_PORT|EMAIL_SMTP_USE_TLS|EMAIL_SMTP_TIMEOUT|HEALTHZ_SMTP_CHECK_ENABLED)=' \
  ~/apps/skriptoteket/.env

# 3) TCP reachability (does not log in)
set -a; source ~/apps/skriptoteket/.env; python3 - <<'PY'
import os, socket
host = os.environ["EMAIL_SMTP_HOST"]
port = int(os.environ.get("EMAIL_SMTP_PORT", "587"))
socket.create_connection((host, port), timeout=5).close()
print("smtp tcp ok", host, port)
PY

# 4) App logs (startup warning + failed sends)
sudo docker logs --since 10m skriptoteket-web | rg -n 'SMTP health check failed|Health check: smtp|Failed to send email|EMAIL_SEND_FAILED'
```

## Prometheus Metrics Endpoint

`GET /metrics` exposes Prometheus metrics for scraping.

### Metrics exposed

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `skriptoteket_http_requests_total` | Counter | method, endpoint, status_code | Total HTTP requests |
| `skriptoteket_http_request_duration_seconds` | Histogram | method, endpoint | Request latency |
| `skriptoteket_session_files_bytes_total` | Gauge | - | Total bytes of stored session files |
| `skriptoteket_session_files_count` | Gauge | - | Count of stored session files |
| `skriptoteket_logins_total` | Counter | status | Login attempts (success/failure) |
| `skriptoteket_users_by_role` | Gauge | role | Active users by role |
| `skriptoteket_auth_context_verifications_total` | Counter | outcome, reason | HuleEdu signed internal identity verification outcomes |
| `skriptoteket_auth_projection_outcomes_total` | Counter | realm, outcome, reason | Realm-aware projection and provisioning outcomes |
| `skriptoteket_auth_rbac_decisions_total` | Counter | decision, required_role, actual_role, route_family | Local RBAC decisions after shared-auth success |

Labels use route patterns (e.g., `/tools/{id}`) to avoid high cardinality.

Session file metrics are computed at scrape time by scanning `ARTIFACTS_ROOT/sessions/` (excluding `meta.json`).

### Auth Metrics After PR-0253

`skriptoteket_active_sessions` is retired with the local browser-session table. Do not recreate
that metric from Skriptoteket-local state in the HuleEdu auth world.

Use these ownership rules for future auth observability:

- HuleEdu Gateway owns browser session counts and shared auth/CSRF ceremony telemetry.
- Skriptoteket may expose signed-context verification and app-projection counters, for example
  accepted/rejected gateway context and missing/ready local projection outcomes.
- Skriptoteket may expose local RBAC inventory gauges such as `skriptoteket_users_by_role` from the
  `users` table when production identity gauges are explicitly enabled.
- Skriptoteket must not infer active browser sessions from stale cookies, removed `sessions` rows,
  or frontend state.

### Auth outcome metrics after PR-0264

`PR-0264` adds the first bounded auth outcome metric surface for the HuleEdu cutover:

| Metric | Labels | Expected values |
|---|---|---|
| `skriptoteket_auth_context_verifications_total` | `outcome`, `reason` | `outcome=accepted|rejected`; reason is a bounded verification code such as `ok`, `missing_internal_identity_headers`, `invalid_internal_identity_signature`, or `internal_identity_expired` |
| `skriptoteket_auth_projection_outcomes_total` | `realm`, `outcome`, `reason` | `realm=skriptoteket_standalone|huleedu_school|unknown`; `outcome=resolved|provisioned|missing|blocked_provisioning|linking_required|unsupported_realm` |
| `skriptoteket_auth_rbac_decisions_total` | `decision`, `required_role`, `actual_role`, `route_family` | `decision=denied`; roles are bounded local role names; route family is a coarse API family such as `admin`, `editor`, `curated_app`, or `profile` |

Forbidden labels remain forbidden here: no user id, email, raw realm subject id, raw URL, path
parameter, correlation id, trace id, signed header payload, cookie, CSRF token, or exception text.

Useful PromQL checks:

```promql
# Signed-context rejection rate by bounded reason
sum by (reason) (rate(skriptoteket_auth_context_verifications_total{outcome="rejected"}[5m]))

# Projection/provisioning failures by outcome
sum by (outcome, reason) (rate(skriptoteket_auth_projection_outcomes_total{outcome!="resolved",outcome!="provisioned"}[5m]))

# Local RBAC denials by coarse API family
sum by (route_family, required_role, actual_role) (rate(skriptoteket_auth_rbac_decisions_total{decision="denied"}[5m]))
```

If an auth incident starts from a browser symptom, use logs with `X-Correlation-ID` for the
individual request, then use these counters to decide whether the failure is systemic. HuleEdu
Gateway/session metrics remain the owner for browser-session counts, CSRF ceremony, logout, and
provider lifecycle outcomes.

### Local example

```bash
curl -s http://127.0.0.1:8000/metrics | head -50
```

### Prometheus scrape config

```yaml
scrape_configs:
  - job_name: 'skriptoteket'
    static_configs:
      - targets: ['skriptoteket-web:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

### PromQL snippets

```promql
# Session files size (MiB)
skriptoteket_session_files_bytes_total / 1024 / 1024

# Session files count
skriptoteket_session_files_count

# 95th percentile latency
histogram_quantile(0.95, sum by (le) (rate(skriptoteket_http_request_duration_seconds_bucket[5m])))
```

Dashboards and data source verification live in `docs/runbooks/runbook-observability-grafana.md`.
