---
type: story
id: ST-28-01
title: "Frontend auth store and API client cutover to HuleEdu session contract"
status: done
owners: "agents"
created: 2026-03-28
updated: 2026-04-30
epic: "EPIC-28"
acceptance_criteria:
  - "Given the shared browser session contract is available at `https://api.hule.education`, when Skriptoteket boots the SPA, then auth bootstrap is loaded from `GET /v1/auth/session` rather than local `/api/v1/auth/me`."
  - "Given the shared browser session contract exposes CSRF separately, when Skriptoteket performs a non-GET API request, then it fetches `GET /v1/auth/csrf` from HuleEdu and sends the required CSRF header."
  - "Given the shared session bootstrap contains richer browser state, when the auth store hydrates, then Skriptoteket preserves its profile, AI policy, role-aware getters, and other app-critical bootstrap semantics rather than downgrading to a minimal user payload."
ui_impact: "Auth bootstrap source changes, but the visible browser UX should remain equivalent or better."
dependencies: ["ADR-0009", "ADR-0030", "ADR-0076", "ADR-0082", "ST-11-05", "ST-28-05"]
---

## Context

`frontend/apps/skriptoteket/src/stores/auth.ts` and
`frontend/apps/skriptoteket/src/api/client.ts` already assume the stronger browser model we want
to keep: cookie credentials, CSRF, and rich bootstrap state. The cutover work is therefore not
"adopt HuleEdu bearer auth"; it is "point the existing stronger contract at HuleEdu-owned session
authority."

## Notes

- Browser auth origin must become `https://api.hule.education`.
- The target contract is `GET /v1/auth/session` plus `GET /v1/auth/csrf`, not browser use of
  `/v1/auth/me`.
- HuleEdu has delivered the provider authority baseline through ADR-0039 and completed the
  `TASK-0308` handoff proof. This story can start after `PR-0250`; implementation must preserve
  Skriptoteket-local role, profile, AI policy, and app authorization semantics without rebuilding a
  local browser auth bridge.
- `PR-0251` is now in progress with the first frontend slice: shared session bootstrap and shared
  CSRF endpoint consumption are implemented behind a HuleEdu contract adapter. App-local AI/profile
  continuation and auth ceremony alignment remain open before the story can be marked done.
- `ADR-0082` is accepted and now governs the continuation boundary for app-local AI/profile state:
  HuleEdu remains the only browser auth bootstrap, while Skriptoteket hydrates AI policy and AI
  preferences through a separate app-local continuation that does not restore `/api/v1/auth/me` or
  local browser session authority.
- The continuation remediation is now review-clean: `PR-0255` moved
  `/api/v1/profile/app-continuation` to signed HuleEdu request context, returns Skriptoteket-local
  `local_user` plus profile/AI policy, keeps HuleEdu provider roles as metadata, and
  `REV-PR-0251` approved the retained implementation re-review. Login/logout ceremony retirement
  remains deliberately split to `PR-0252` / `PR-0253`.

## Status Reconciliation (2026-04-30)

This story is now marked `done`. The later `EPIC-28` closeout already records
that the shared HuleEdu browser-session bootstrap, app-local continuation,
signed-context projection, login/logout ceremony split, cross-app proof, and
auth observability chain all shipped. The lingering `in_progress` frontmatter
was stale after `PR-0255`, `PR-0252`, `PR-0253`, `PR-0254`, `PR-0263`, and
`PR-0264` closed the dependent auth work.
