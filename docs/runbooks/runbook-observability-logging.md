---
type: runbook
id: RUN-observability-logging
title: "Runbook: Observability (Logging + Correlation)"
status: active
owners: "olof"
created: 2025-12-16
system: "skriptoteket"
---

How to debug Skriptoteket using HuleEdu-compatible structured logs and correlation IDs.

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
`correlation_id` for application logs emitted during request handling.

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
- `trace_id`, `span_id` (once OpenTelemetry is enabled)

## Home server usage

```bash
# Follow logs
ssh hemma "docker logs -f skriptoteket_web"

# Filter by correlation id
ssh hemma "docker logs skriptoteket_web | rg '<correlation-id>'"
```

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

The structlog configuration includes a redaction processor that automatically replaces values for sensitive keys with `[REDACTED]`. Keys matching these patterns are redacted (case-insensitive):

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

