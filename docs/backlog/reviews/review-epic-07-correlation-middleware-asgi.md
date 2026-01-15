---
type: review
id: REV-EPIC-07
title: "Review: ASGI correlation middleware for access-log correlation"
status: approved
owners: "agents"
created: 2026-01-15
reviewer: "lead-developer"
epic: EPIC-07
adrs:
  - ADR-0061
stories:
  - ST-07-06
---

## TL;DR

Switch correlation to a pure ASGI middleware so `correlation_id` is present in `uvicorn.access` logs for successful and
streaming requests (not only warnings/errors), while keeping the public `X-Correlation-ID` contract stable.

## Problem Statement

Today, correlation is bound using `BaseHTTPMiddleware` and cleared immediately after `call_next(...)` returns a
`Response`. In our pinned Uvicorn (`0.40.0`), `uvicorn.access` is emitted when the server sends `http.response.start`
(response headers). For normal responses and especially for streaming/SSE, this happens after `call_next(...)` returns,
so the access log is missing `correlation_id`.

## Proposed Solution

Implement ADR-0061 and ST-07-06:

- Use pure ASGI middleware to bind `correlation_id` for the full request lifecycle (including streaming).
- Inject `X-Correlation-ID` into response headers at `http.response.start`.
- Clear contextvars only after the downstream ASGI app returns (after the final body for streaming responses).
- Ensure middleware ordering so tracing/metrics/error handling can read `request.state.correlation_id`.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/adr/adr-0061-asgi-correlation-middleware.md` | ASGI strategy, lifecycle/ordering, consequences | 10 min |
| `docs/backlog/stories/story-07-06-asgi-correlation-middleware.md` | Acceptance criteria | 5 min |
| `docs/backlog/prs/pr-0032-asgi-correlation-middleware.md` | Implementation + test plan | 5 min |

**Total estimated time:** ~20 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Pure ASGI middleware (not `BaseHTTPMiddleware`) | Keeps contextvars bound through `http.response.start` and streaming lifecycles | [x] |
| Preserve current public contract (`X-Correlation-ID`, `request.state.correlation_id`) | Avoids breaking callers + existing middleware | [x] |
| Make correlation outermost middleware | Lets tracing/metrics/error handler read `request.state.correlation_id` and keeps it available for `uvicorn.access` | [x] |
| Hybrid test approach (ASGI-level automated + manual smoke) | Avoids flaky “real server” tests while still validating end-to-end behavior | [x] |
| Reopen EPIC-07 for ST-07-06 follow-up | Keeps observability work discoverable and consistent with story linkage | [x] |

## Review Checklist

- [x] ADR defines clear contracts (ASGI lifecycle, header semantics, ordering)
- [x] Story acceptance criteria are testable and match runtime logging behavior
- [x] Implementation plan aligns with existing patterns (contextvars, `scope["state"]`, middleware ordering)
- [x] Risks are identified with reasonable mitigations

---

## Review Feedback

**Reviewer:** @user-lead
**Date:** 2026-01-15
**Verdict:** approved

### Required Changes

None.

### Suggestions (Optional)

- Make the middleware “never-throw”: treat invalid/missing `X-Correlation-ID` as “generate new” and always clear context
  in `finally`.
- Guard non-HTTP scopes (`lifespan`, `websocket`) explicitly to avoid accidental context binding.
- Add a cancellation/disconnect test case if feasible (ensure `clear_contextvars()` runs on exceptions).

### Decision Approvals

- [x] Middleware type: pure ASGI (not `BaseHTTPMiddleware`)
- [x] Public contract: keep `X-Correlation-ID` + `request.state.correlation_id`
- [x] Middleware ordering: correlation outermost
- [x] Tests: hybrid (ASGI-level automated + manual smoke)
- [x] Epic linkage: reopen EPIC-07 for ST-07-06

### Verification

- `pdm run docs-validate`

```text
docs-validate: OK
```

---

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | ADR-0061 | Corrected access-log timing (`http.response.start` in Uvicorn 0.40.0) and accepted the ADR |
| 2 | ST-07-06 | Updated streaming/SSE acceptance criterion to match access-log timing |
| 3 | PR-0032 | Updated acceptance criteria and test plan (ASGI-level automated + manual smoke) |
| 4 | EPIC-07 | Reopened epic and added missing story links (ST-07-05) + ST-07-06 |
