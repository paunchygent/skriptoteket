---
type: pr
id: PR-0253
title: "ST-28-03 local auth authority retirement and contract regeneration"
status: ready
owners: "agents"
created: 2026-04-10
updated: 2026-04-11
stories:
  - "ST-28-03"
tags: ["auth", "backend", "frontend", "contracts"]
acceptance_criteria:
  - "Given Skriptoteket has cut over to the HuleEdu-owned browser-session contract, when local browser-auth surfaces are audited, then routes, models, handlers, and frontend assumptions that only exist to own browser auth locally are removed."
  - "Given shared auth endpoints are now external provider contract surfaces, when client contracts and generated types are refreshed, then Skriptoteket no longer treats local `/api/v1/auth/me` as the browser bootstrap source."
  - "Given `PR-0255` made app continuation HuleEdu-context-derived, when this PR retires local auth authority, then remaining local-session-backed `require_user_api`, `require_contributor_api`, `require_admin_api`, and `require_superuser_api` consumers are either rewired to HuleEdu-derived app-user projection/authorization or explicitly retained as non-browser internal authorization with documented rationale."
  - "Given the repository forbids hidden compatibility bridges, when this PR is reviewed, then remaining auth code is either internal authorization, explicit app-local domain behavior, or documented consumer code for the HuleEdu session contract."
---

## Problem

The cutover is not complete if old local browser-auth ownership remains in the codebase as a
fallback path.

After `PR-0255`, `GET /api/v1/profile/app-continuation` no longer depends on the
local-session-backed `require_user_api` path. Other protected app APIs still do. That includes
profile mutations, editor/admin APIs, my-tools/favorites APIs, curated-app authenticated APIs, and
the role-specific wrappers (`require_contributor_api`, `require_admin_api`,
`require_superuser_api`) that delegate to `require_user_api`.

## Goal

Retire Skriptoteket-local browser auth authority after `PR-0251` and `PR-0252` prove the consumer
path, then regenerate or realign client contracts around the shared session model.

## Non-goals

- Removing internal service authorization checks that still protect app data.
- Removing account-domain concepts that Skriptoteket still legitimately owns.
- Changing visible login UX beyond removing obsolete local authority paths.

## Implementation Plan

1. Inventory local browser-auth endpoints, handlers, frontend imports, generated clients, and tests.
2. Inventory every `require_user_api` and role-wrapper consumer and classify it as HuleEdu-derived
   app-user projection, internal authorization, or obsolete local browser-auth surface.
3. Delete obsolete browser-auth authority surfaces instead of preserving bridge fallbacks.
4. Rewire protected app API dependencies to the HuleEdu-derived app-user projection where browser
   requests are still expected after the shared-session cutover.
5. Regenerate or update client contracts/types through the repo's sanctioned workflow.
6. Update tests to assert the new shared-session source of truth and absence of local bootstrap
   fallback.

## Test Plan

- Run affected backend auth tests.
- Run affected frontend auth/client tests.
- Run `pdm run fe-type-check`.
- Run `pdm run docs-validate`.

## Rollback Plan

Revert the deletion and generated-contract changes if the shared-session implementation cannot yet
cover a required browser behavior, then route the gap back through `PR-0250` and the HuleEdu
handoff target.
