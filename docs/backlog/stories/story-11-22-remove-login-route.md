---
type: story
id: ST-11-22
title: "Remove /login route (modal-only login)"
status: done
owners: "agents"
created: 2025-12-23
epic: "EPIC-11"
acceptance_criteria:
  - "Given a user visits /login, then they are returned to / and the login modal opens"
  - "Given an unauthenticated user triggers auth guards, then the login modal opens (no route change)"
  - "Given an unauthenticated visitor, then the header and home CTA open the modal (no dedicated /login route)"
ui_impact: "Removes the standalone login page in favor of a single modal-first flow."
dependencies: ["ST-11-05", "ST-11-21"]
---

## Context

Skriptoteket now uses a global login modal for auth-first interactions. The remaining `/login` route is legacy
and should be removed so all login flows are modal-first.

## Scope

- Remove the `/login` route from the SPA router.
- Ensure direct `/login` visits resolve to `/` and open the login modal.
- Keep auth-guard redirects modal-first (no URL change).

## Decision Note (from planning)

3. Remove /login route entirely (modal-only)
   - Pros: no legacy login page.
   - Cons: bigger change, higher risk.

## Implemented (2025-12-23)

- Removed `LoginView.vue` and the `/login` route record (`frontend/apps/skriptoteket/src/router/routes.ts`).
- Router guard treats `/login` as a special-case path: redirects to `/` and opens the login modal.
- Auth-expiry handling is modal-first (no `/login` navigation) in `frontend/apps/skriptoteket/src/App.vue`.
