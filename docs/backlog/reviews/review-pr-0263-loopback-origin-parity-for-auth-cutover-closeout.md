---
type: review
id: REV-PR-0263
title: "Review: PR-0263 loopback origin parity for auth cutover closeout"
status: approved
owners: "agents"
created: 2026-04-13
updated: 2026-04-13
reviewer: "lead-developer"
prs:
  - PR-0263
links:
  - EPIC-28
  - ST-28-04
  - PR-0254
  - REV-PR-0254
  - PR-0261
  - PR-0262
  - HuleEdu TASK-0325
---

## TL;DR

`PR-0263` is approved as the follow-up task that makes `ST-28-04` closeout mean both loopback lanes
are green. The approved design treats the 127 failure as a shared browser-origin contract problem,
not as a reason to add Skriptoteket-local API authentication.

## Problem Statement

The failed `127.0.0.1` proof shows that local closeout cannot rely on only the canonical
`localhost` lane. Browser cookies are scoped by host, and the final proof uses multiple
browser-visible HuleEdu surfaces. If one surface resolves to `127.0.0.1` and another resolves to
`localhost`, the proof can authenticate in one host bucket and bootstrap session state in another.

## Proposed Solution

Approve a narrow loopback-origin policy:

- Match HuleEdu browser ceremony entry URLs to the current Skriptoteket loopback host when both are
  local loopback hosts.
- Match HuleEdu shared-auth API base URLs to the current Skriptoteket loopback host when both are
  local loopback hosts.
- Keep protected Skriptoteket `/api/...` paths relative so they continue to enter the HuleEdu Gateway
  proxy.
- Keep production and non-loopback configured hosts unchanged.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0263-st-28-04-loopback-origin-parity-for-auth-cutover-closeout.md` | Scope, ownership boundaries, proof obligations | 10 min |
| `docs/backlog/prs/pr-0254-st-28-04-cross-app-auth-cutover-smoke-and-runbook-proof.md` | Existing final proof contract and blocked 127 lane | 5 min |
| `frontend/apps/skriptoteket/src/api/sharedAuth.ts` | HuleEdu URL policy surface to implement after approval | 5 min |
| HuleEdu Gateway auth ceremony code | Provider redirect surface to keep aligned with validated `return_to` | 5 min |

**Total estimated time:** ~25 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Treat 127 closeout as required | Browser host-scoped cookies make localhost and 127 distinct proof lanes | [x] |
| Centralize loopback host parity for HuleEdu URLs | Fixes the class of failures across ceremony, session, CSRF, and logout | [x] |
| Keep Skriptoteket protected APIs relative | Ensures protected reads/writes still prove Gateway proxying, not local auth | [x] |
| Do not rewrite non-loopback hosts | Avoids weakening production or custom deployment URL contracts | [x] |

## Review Checklist

- [x] Scope is bounded to local loopback origin parity.
- [x] Acceptance criteria require both lane summaries green.
- [x] The structural fault line is named: host-scoped browser cookies across multiple HuleEdu
      browser-visible surfaces.
- [x] The verification plan proves the final cross-process contract and redaction guarantees.
- [x] The design does not introduce Skriptoteket-local browser session authority or API-gated auth.

## Review Feedback

**Reviewer:** lead-developer
**Date:** 2026-04-13
**Verdict:** `approved`

### Required Changes

None. The task correctly identifies the larger architecture issue and keeps ownership boundaries
intact. Implementation may proceed only within the approved shape: HuleEdu owns browser
session/CSRF/logout, HuleEdu Gateway owns protected `/api` proxying, and Skriptoteket owns app
continuation plus local projection/RBAC.

### Suggestions (Optional)

When implementing, include a negative test proving a non-loopback configured HuleEdu URL is not
rewritten. This guards against a future "helpful" resolver accidentally mutating production or
staging origins.

### Decision Approvals

- [x] Required 127 lane closeout
- [x] Loopback URL parity policy
- [x] No direct backend shortcut for protected `/api`
- [x] No Skriptoteket-local browser auth authority

### Independent Implementation Review (2026-04-13)

**Reviewer:** Codex independent ruthless review
**Verdict:** `approved`

Scope reviewed:

- `frontend/apps/skriptoteket/src/api/sharedAuth.ts`
- `frontend/apps/skriptoteket/src/stores/auth.ts`
- `frontend/apps/skriptoteket/src/api/sharedAuth.spec.ts`
- `frontend/apps/skriptoteket/src/stores/auth.spec.ts`
- `frontend/apps/skriptoteket/src/stores/auth.csrf.spec.ts`
- `frontend/apps/skriptoteket/src/stores/auth.logout.spec.ts`
- `scripts/playwright_pr_0254_auth_cutover.py`
- `scripts/_pr_0254_auth_cutover_browser.py`
- `scripts/_pr_0254_auth_cutover_manifest.py`
- `tests/unit/application/auth/test_pr_0254_auth_cutover_config.py`
- `tests/unit/application/auth/test_pr_0254_auth_cutover_manifest.py`
- Retained manifest:
  `.artifacts/playwright-pr-0254-auth-cutover/local-nonprod/20260413T160856Z/manifest.redacted.json`
- Retained screenshots:
  `.artifacts/playwright-pr-0254-auth-cutover/local-nonprod/20260413T160856Z/localhost-editor-after-callback.png`
  and
  `.artifacts/playwright-pr-0254-auth-cutover/local-nonprod/20260413T160856Z/127-editor-after-callback.png`

Required changes: none.

The implementation matches the approved shape. Skriptoteket aligns only loopback HuleEdu
ceremony/session/CSRF/logout URLs to the current browser host, leaves non-loopback configured hosts
unchanged, and keeps protected Skriptoteket `/api/...` calls relative. The live proof executes the
same browser assertions for `localhost` and `127`, and the retained manifest records both lane
summaries as `status=ok`. The protected app-continuation and AI-settings paths remain backed by
signed HuleEdu-derived FastAPI dependencies, so a direct backend shortcut would fail closed rather
than silently certify local browser auth.

Evidence checked:

- Playwright's context-bound API request contract shares browser-context cookies, so the post-logout
  HuleEdu session probe is a valid session-authority check.
- The retained manifest validates HuleEdu `TASK-0326`, HuleEdu `TASK-0327`, Skriptoteket `PR-0261`,
  and Skriptoteket `PR-0262` prerequisites before browser evidence.
- The retained manifest records public bootstrap `200`, app-continuation `200`, callback final path
  `/editor`, local role `contributor`, missing-CSRF write `403`, CSRF-protected write `200`, logout
  session status `200`, and both loopback lane summaries as `status=ok`.
- Manual screenshot inspection found no visible raw email, token, cookie, CSRF, subject, signed
  context, or URL material in the retained images.

Non-blocking auditability note:

- `scripts/playwright_pr_0254_auth_cutover.py` writes the manifest `command` field as
  `pdm run pr-0254-auth-cutover` even when the retained closeout was run with
  `--include-127-lane --require-127-lane`. The behavior is still proven by
  `loopback_lane_assertions.127.status=ok`, but the next manifest-hardening pass should record the
  effective lane flags in the manifest and cover that with a focused unit test.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `PR-0263` | Created reviewed follow-up task for both-lane auth cutover closeout |
| 2 | `REV-PR-0263` | Approved the architecture-aligned loopback-origin parity design |
| 3 | `REV-PR-0263` | Added independent implementation review, retained artifact inspection, and non-blocking manifest auditability note |
