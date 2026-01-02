---
type: story
id: ST-09-02
title: "Content-Security-Policy for SPA/CodeMirror"
epic: EPIC-09
status: done
owners: "agents"
created: 2025-12-17
acceptance_criteria:
  - "Given any HTTPS response, when headers are inspected, then Content-Security-Policy is present and enforced"
  - "Given the UI is a Vue/Vite SPA, when key flows are exercised, then navigation and API calls work without CSP errors"
  - "Given the editor uses CodeMirror, when loaded and edited, then CodeMirror works without CSP errors"
  - "Given fonts/assets are loaded, when pages load, then they load without CSP errors"
  - "Given browser devtools console, when using the product, then there are no CSP violations logged"
  - "Given CSP rollout, when first deployed, then report-only mode is validated before enforcing mode"
---

## Resolution (superseded)

This story predates the finalized SPA asset pipeline and editor runtime. Now that the Vue/Vite cutover is complete,
the CSP policy must be re-scoped to the actual build artifacts and runtime behaviors. Closing as superseded; a new
SPA-first CSP story should be created once the current asset pipeline is confirmed.

## Goal

Implement Content-Security-Policy (CSP) header tuned for Skriptoteket's frontend stack (Vue/Vite SPA + CodeMirror).

## Acceptance Criteria

- [ ] CSP header present on all HTTPS responses
- [ ] SPA functionality preserved (Vue Router, API calls, static assets)
- [ ] CodeMirror editor works (syntax highlighting, dynamic styles)
- [ ] No CSP violations in browser console
- [ ] Report-only mode tested before enforcement

## Challenges

1. **SPA**: Must allow same-origin scripts, assets, and API calls (`connect-src`).
2. **CodeMirror**: May inject dynamic `<style>` elements (often requires `style-src 'unsafe-inline'`).
3. **External assets (optional)**: Fonts/images/CDNs require explicit allowlisting if used.

## Proposed CSP (starting point)

```
Content-Security-Policy:
  default-src 'self';
  script-src 'self';
  style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
  font-src 'self' https://fonts.gstatic.com;
  img-src 'self' data:;
  connect-src 'self';
  frame-ancestors 'none';
```

Note: avoid `'unsafe-inline'` for scripts in production. If inline styles are needed for CodeMirror, keep them scoped to
`style-src` only. Future improvement: use nonces/hashes.

## Implementation Steps

1. Add CSP in report-only mode first: `Content-Security-Policy-Report-Only`
2. Test all pages in browser (check console for violations)
3. Tune policy based on violations
4. Switch to enforcing mode

## Dependencies

- ST-09-01 completed (basic security headers in place)
- Browser testing environment
