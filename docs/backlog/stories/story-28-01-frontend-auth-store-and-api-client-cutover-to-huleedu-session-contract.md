---
type: story
id: ST-28-01
title: "Frontend auth store and API client cutover to HuleEdu session contract"
status: ready
owners: "agents"
created: 2026-03-28
updated: 2026-04-08
epic: "EPIC-28"
acceptance_criteria:
  - "Given the shared browser session contract is available at `https://api.hule.education`, when Skriptoteket boots the SPA, then auth bootstrap is loaded from `GET /v1/auth/session` rather than local `/api/v1/auth/me`."
  - "Given the shared browser session contract exposes CSRF separately, when Skriptoteket performs a non-GET API request, then it fetches `GET /v1/auth/csrf` from HuleEdu and sends the required CSRF header."
  - "Given the shared session bootstrap contains richer browser state, when the auth store hydrates, then Skriptoteket preserves its profile, AI policy, role-aware getters, and other app-critical bootstrap semantics rather than downgrading to a minimal user payload."
ui_impact: "Auth bootstrap source changes, but the visible browser UX should remain equivalent or better."
dependencies: ["ADR-0009", "ADR-0030", "ADR-0076", "ST-11-05", "ST-28-05"]
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
- This story is blocked on HuleEdu delivering the rich shared session document defined by
  ADR-0076.
