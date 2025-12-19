---
type: story
id: ST-09-02
title: "Content-Security-Policy for HTMX/CodeMirror"
epic: EPIC-09
status: pending
owners: "agents"
created: 2025-12-17
---

## Goal

Implement Content-Security-Policy (CSP) header tuned for Skriptoteket's frontend stack (HTMX, CodeMirror, Google Fonts).

## Acceptance Criteria

- [ ] CSP header present on all HTTPS responses
- [ ] HTMX functionality preserved (inline event handlers, dynamic content)
- [ ] CodeMirror editor works (syntax highlighting, dynamic styles)
- [ ] Google Fonts load correctly
- [ ] No CSP violations in browser console
- [ ] Report-only mode tested before enforcement

## Challenges

1. **HTMX**: Uses `hx-*` attributes and may inject inline scripts
2. **CodeMirror**: Injects dynamic `<style>` elements
3. **Google Fonts**: Requires whitelisting `fonts.googleapis.com` and `fonts.gstatic.com`

## Proposed CSP (starting point)

```
Content-Security-Policy:
  default-src 'self';
  script-src 'self' 'unsafe-inline';
  style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
  font-src 'self' https://fonts.gstatic.com;
  img-src 'self' data:;
  connect-src 'self';
  frame-ancestors 'none';
```

Note: `'unsafe-inline'` for scripts/styles reduces CSP effectiveness but is required for HTMX/CodeMirror. Future improvement: use nonces.

## Implementation Steps

1. Add CSP in report-only mode first: `Content-Security-Policy-Report-Only`
2. Test all pages in browser (check console for violations)
3. Tune policy based on violations
4. Switch to enforcing mode

## Dependencies

- ST-09-01 completed (basic security headers in place)
- Browser testing environment
