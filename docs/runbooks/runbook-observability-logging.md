---
type: runbook
id: RUN-observability-logging
title: "Runbook: Observability Logging"
status: active
owners: "olof"
created: 2025-12-16
updated: 2026-01-01
system: "skriptoteket"
---

How to debug Skriptoteket using structured logs and correlation IDs.

Reference: `docs/reference/reports/ref-external-observability-integration.md`.

## Configuration

Environment variables:

- `SERVICE_NAME` (default: `skriptoteket`)
- `ENVIRONMENT` (default: `development`)
- `LOG_LEVEL` (default: `INFO`)
- `LOG_FORMAT` (`json` or `console`)

Recommended defaults:

- Local dev: `LOG_FORMAT=console`
- Production: `LOG_FORMAT=json`

## Correlation ID

Skriptoteket accepts `X-Correlation-ID` on incoming requests and echoes it on responses. The value is bound as
`correlation_id` for logs emitted during request handling.

### Local example

```bash
CID="$(python -c 'import uuid; print(uuid.uuid4())')"
curl -i -H "X-Correlation-ID: ${CID}" http://127.0.0.1:8000/login
```

Search logs for the correlation id:

```bash
docker logs skriptoteket_web | rg "${CID}"
```

## JSON log shape (HuleEdu)

Required fields:

- `timestamp` (RFC 3339 / ISO 8601)
- `level` (`debug|info|warning|error|critical`)
- `event` (human-readable message)
- `service.name`
- `deployment.environment`

Optional fields (when available):

- `correlation_id`
- `trace_id`, `span_id` (when OpenTelemetry is enabled)

## Where to view logs

Local:

```bash
docker logs -f skriptoteket_web
```

Home server:

```bash
ssh hemma "sudo docker logs -f skriptoteket-web"
```

Grafana + Loki: see `docs/runbooks/runbook-observability-grafana.md`.

## nginx-proxy bot/probe analysis (Loki)

`nginx-proxy` access logs are shipped to Loki via Promtail. We label only low-cardinality fields:

- `vhost` (Host header / vhost)
- `client_ip` (nginx `$remote_addr`)
- `method`, `status`

Grafana dashboard (provisioned):

- `Skriptoteket nginx-proxy Security` (`observability/grafana/provisioning/dashboards/skriptoteket-nginx-proxy-security.json`)

Examples (LogQL metrics):

```logql
# Top probed vhosts (24h)
topk(10, sum by (vhost) (count_over_time({container="nginx-proxy",method=~".+"}[24h])))

# Top client IPs (24h)
topk(10, sum by (client_ip) (count_over_time({container="nginx-proxy",method=~".+"}[24h])))

# Scanner/probe patterns (24h)
sum(count_over_time({container="nginx-proxy",method=~".+"} |= "/.env" [24h]))
sum(count_over_time({container="nginx-proxy",method=~".+"} |~ "\\.git" [24h]))
sum(count_over_time({container="nginx-proxy",method=~".+"} |~ "(?i)wp-" [24h]))
sum(count_over_time({container="nginx-proxy",method=~".+"} |~ "\\.php" [24h]))
sum(count_over_time({container="nginx-proxy",method="PROPFIND"}[24h]))
```

Avoid labeling full paths (high cardinality). Use query-time filters (`|=` / `|~`) instead.

## Sensitive Data Policy

Skriptoteket handles school-related data. Observability must not become a data leakage vector.

### What MAY be logged

- User IDs, role names (e.g., `user`, `contributor`, `admin`)
- Tool IDs, tool version IDs, run IDs
- Request paths, methods, status codes
- Correlation IDs, trace IDs, span IDs
- Error types and non-sensitive error messages
- Timestamps and durations

### What MUST NOT be logged

- Passwords, tokens, secrets, API keys
- Email addresses (PII)
- Student names, personal data, school identifiers
- File contents from uploads
- Session cookies or bearer tokens
- Raw request/response bodies containing user data

### Automatic Redaction

The structlog configuration includes a redaction processor that replaces values for sensitive keys with `[REDACTED]`.
Keys matching these patterns are redacted (case-insensitive):

- `password`, `token`, `secret`
- `api_key`, `api-key`, `x-api-key`
- `authorization`, `credential`, `bearer`
- `cookie`, `session`

### Security Review Checklist

When adding new log statements, verify:

- [ ] No PII (emails, names, student data) in log events
- [ ] Sensitive data uses keys that trigger automatic redaction
- [ ] No raw request/response body logging
- [ ] Error messages don't expose internal system details
- [ ] File paths don't reveal user-specific information
