---
type: story
id: ST-09-01
title: "HTTP security headers via nginx"
epic: EPIC-09
status: done
owners: "agents"
created: 2025-12-17
acceptance_criteria:
  - "Given any HTTPS response, when headers are inspected, then Strict-Transport-Security is present with max-age=31536000 and includeSubDomains"
  - "Given any HTTPS response, when headers are inspected, then X-Frame-Options is present and set to DENY"
  - "Given any HTTPS response, when headers are inspected, then X-Content-Type-Options is present and set to nosniff"
  - "Given any HTTPS response, when headers are inspected, then Referrer-Policy is present and set to strict-origin-when-cross-origin"
  - "Given any HTTPS response, when headers are inspected, then Permissions-Policy is present and disables geolocation, camera, and microphone"
  - "Given nginx error responses, when headers are inspected, then the security headers are still present (nginx add_header always)"
---

## Goal

Add standard HTTP security headers at the nginx reverse proxy level to protect against common web vulnerabilities.

## Acceptance Criteria

- [ ] `Strict-Transport-Security: max-age=31536000; includeSubDomains` present on all HTTPS responses
- [ ] `X-Frame-Options: DENY` present (clickjacking protection)
- [ ] `X-Content-Type-Options: nosniff` present (MIME-sniffing protection)
- [ ] `Referrer-Policy: strict-origin-when-cross-origin` present
- [ ] `Permissions-Policy: geolocation=(), camera=(), microphone=()` present
- [ ] Headers apply to all responses including error pages (`always` directive)
- [ ] ADR-0021 documents the decision

## Implementation

Add to `~/infrastructure/nginx/conf.d/skriptoteket.conf` inside the HTTPS server block:

```nginx
# Security headers (ADR-0021)
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Frame-Options "DENY" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "geolocation=(), camera=(), microphone=()" always;
```

## Verification

```bash
curl -sI https://skriptoteket.hule.education/login | grep -iE 'strict|x-frame|x-content|referrer|permissions'
```

Expected output:
```
strict-transport-security: max-age=31536000; includeSubDomains
x-frame-options: DENY
x-content-type-options: nosniff
referrer-policy: strict-origin-when-cross-origin
permissions-policy: geolocation=(), camera=(), microphone=()
```

## Notes

- CSP deferred to ST-09-02 (requires HTMX/CodeMirror testing)
- Header ownership model documented in ADR-0021
