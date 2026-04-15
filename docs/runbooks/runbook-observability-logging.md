---
type: runbook
id: RUN-observability-logging
title: "Runbook: Observability Logging"
status: active
owners: "olof"
created: 2025-12-16
updated: 2026-04-15
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
- `LLM_CAPTURE_ON_ERROR_ENABLED` (default: `false`; platform-only, not logs)

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

## Auth Outcome Triage After HuleEdu Cutover

Skriptoteket no longer owns browser sessions, CSRF ceremony, logout authority, provider
registration, password reset, or email verification telemetry. Start with one known
`X-Correlation-ID`, then decide whether the signal belongs to Skriptoteket or must be handed to
HuleEdu Gateway/session logs.

### Local correlation-first check

```bash
CID="$(python -c 'import uuid; print(uuid.uuid4())')"
curl -i -H "X-Correlation-ID: ${CID}" http://127.0.0.1:8000/api/v1/profile/app-continuation
docker logs skriptoteket_web | rg "${CID}"
```

If running the host dev backend with log piping:

```bash
rg "${CID}" .artifacts/dev-backend.log
```

### Skriptoteket-owned auth log events

| Event | Meaning | Safe fields |
|---|---|---|
| `auth.internal_identity.verified` | HuleEdu signed internal identity context was accepted by Skriptoteket | `outcome`, `reason`, `correlation_id` |
| `auth.internal_identity.rejected` | HuleEdu signed internal identity context failed closed at Skriptoteket | `outcome`, `reason`, `correlation_id` |
| `auth.projection.resolved` | Realm-aware local projection resolved or provisioned | `realm`, `outcome`, `reason`, `correlation_id` |
| `auth.projection.rejected` | Projection/provisioning was missing, blocked, linking-required, or unsupported | `realm`, `outcome`, `reason`, `correlation_id` |
| `auth.rbac.denied` | Skriptoteket-local `User.role` blocked a protected API route | `decision`, `required_role`, `actual_role`, `route_family`, `correlation_id` |

### Failure interpretation

- `auth.internal_identity.rejected`: inspect `reason`. Missing, expired, invalid, unknown-key, or
  trust-not-configured outcomes are Skriptoteket-side verification symptoms, but the upstream
  Gateway may need to confirm which key/session request produced the signed context.
- `auth.projection.rejected` with `outcome=missing`: the HuleEdu context reached Skriptoteket, but
  no local projection existed and trusted provisioning claims were insufficient.
- `auth.projection.rejected` with `outcome=linking_required`: local email collision requires an
  explicit account-linking decision; do not infer linking from email.
- `auth.projection.rejected` with `outcome=blocked_provisioning`: provisioning was refused by a
  bounded local policy reason such as missing verified email or inactive local user.
- `auth.projection.rejected` with `outcome=unsupported_realm`: the signed context selected a realm
  Skriptoteket does not accept.
- `auth.rbac.denied`: shared auth succeeded; the failure is Skriptoteket-local authorization.
- CSRF write rejection, logout invalidation, provider lifecycle, and browser-session validity are
  HuleEdu-owned. Hand off the same correlation id and time window to HuleEdu Gateway/session logs.

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

## Platform-only LLM debug captures (Option A)

Skriptoteket can optionally persist **sensitive** “full model response” debug captures for edit-ops generation and
preview failures.

- This is **NOT observability logging**: normal logs remain metadata-only.
- Captures may include tool code and raw model output; treat them as sensitive platform data.
- Captures are retrievable only via filesystem/SSH (no tool-developer-facing API/UI).

### Enable

- Set `LLM_CAPTURE_ON_ERROR_ENABLED=true` (default is `false`).

### Capture id (correlation id)

- Capture id is the request `X-Correlation-ID` (also logged as `correlation_id`).
- The UI/API appends `Korrelation-ID: <uuid>` on edit-ops/preview/apply failures to make reporting easier.

### Location

Captures are written under:

```text
${ARTIFACTS_ROOT}/llm-captures/<kind>/<capture_id>/capture.json
```

Known kinds:

- `chat_ops_response` (edit-ops generation failures)
- `edit_ops_preview_failure` (preview failures)

### JSON shape

Each `capture.json` is a small envelope:

```json
{
  "version": 1,
  "kind": "<kind>",
  "capture_id": "<uuid>",
  "captured_at": "<iso8601>",
  "payload": { }
}
```

Payload contents are kind-specific and may contain sensitive data (model output, tool code, diffs/snippets).

### Access

- Local dev: inspect `${ARTIFACTS_ROOT}/llm-captures/`.
- Home server (prod): see `docs/runbooks/runbook-home-server.md` for `ssh` + `docker exec` commands.
