---
type: adr
id: ADR-SKRIPT-0021
title: HTTP security headers via nginx reverse proxy
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: accepted
deciders:
- user-lead
retired_ids:
- ADR-0021
---

## Context

Source: `docs/adr/adr-0021-http-security-headers.md`. HTTP security headers via nginx reverse proxy.

The Skriptoteket application serves web pages over HTTPS but lacks standard HTTP security headers. These headers protect against common web vulnerabilities (clickjacking, MIME-sniffing, protocol downgrade attacks). ADR-0009 mentions "baseline security" requirements but doesn't enumerate specific headers. Add HTTP security headers at the **nginx reverse proxy** level, not in the FastAPI application. | Header | Value | Purpose | |--------|-------|---------| | `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Force HTTPS for 1 year | | `X-Frame-Options` | `DENY` | Prevent clickjacking | | `X-Content-Type-Options` | `nosniff` | Prevent MIME-sniffing | | `Referrer-Policy` | `s

## Decision

The migrated ADR preserves the source decision and its accepted boundary. Source evidence is retained below.

## Non-Decisions

No new decision, implementation authority, or terminal-state promotion is introduced by this migration.

## Consequences

### Source evidence

### Context

The Skriptoteket application serves web pages over HTTPS but lacks standard HTTP security headers. These headers protect against common web vulnerabilities (clickjacking, MIME-sniffing, protocol downgrade attacks).

ADR-0009 mentions "baseline security" requirements but doesn't enumerate specific headers.

### Decision

Add HTTP security headers at the **nginx reverse proxy** level, not in the FastAPI application.

### Headers to Add

| Header | Value | Purpose |
|--------|-------|---------|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Force HTTPS for 1 year |
| `X-Frame-Options` | `DENY` | Prevent clickjacking |
| `X-Content-Type-Options` | `nosniff` | Prevent MIME-sniffing |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Limit referrer leakage |
| `Permissions-Policy` | `geolocation=(), camera=(), microphone=()` | Disable unused browser features |

### Deferred: Content-Security-Policy

CSP is deferred to a future phase. It requires careful tuning for:
- HTMX inline event handlers
- CodeMirror dynamic styles
- Google Fonts external resources

Incorrect CSP silently breaks functionality.

### Rationale for nginx Location

### Header Ownership Model

| Header Type | Owner | Direction |
|-------------|-------|-----------|
| Security headers (HSTS, X-Frame, etc.) | nginx | Response outbound |
| Correlation headers (X-Correlation-ID, X-Trace-ID) | App middleware | Request inbound + response echo |
| Proxy headers (X-Real-IP, X-Forwarded-For) | nginx | Request passthrough |

### Benefits of nginx Enforcement

- **Single point:** Applies to all responses including static files
- **Multi-site:** Unified management across `*.hule.education` with per-site overrides
- **Separation:** Security policy separate from application code
- **Performance:** No middleware overhead in app

### Implementation

In `~/infrastructure/nginx/conf.d/skriptoteket.conf`:

```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Frame-Options "DENY" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "geolocation=(), camera=(), microphone=()" always;
```

The `always` directive ensures headers are added to all responses including error pages.

### Consequences

- All responses from Skriptoteket include security headers
- Browsers enforce HSTS, blocking HTTP downgrade attempts
- iframing is prevented (clickjacking protection)
- MIME-sniffing attacks are blocked
- Future CSP implementation will require testing before deployment
