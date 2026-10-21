---
type: task
id: TASK-SKRIPT-40-04-22
title: Signing out shows no saved-exam list error
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-21'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- After a teacher signs out, the landing page shows no 'Det gick inte att hämta dina
  sparade prov.' toast and the browser sends no exam workspace list request
story: ST-SKRIPT-40-04
backlog_document_profile: contract-derived
---

## Implementation Contract

Source: Mac staging walk of 2026-10-21, finding F2. After a teacher clicks "Logga ut" in the exam workspace, the landing page shows two "Det gick inte att hämta dina sparade prov." toasts (`LIST_FAILURE_COPY`, saved list from TASK-SKRIPT-40-04-03). Every teacher sees it on every sign-out.

Root cause (fail-first probe, 2026-10-21): `App.vue` renders one `RouterView` inside `LandingLayout` (signed out) and another inside `AuthLayout` (signed in). `auth.logout()` clears the user before `router.push("/")` finishes, so the signed-out frame mounts the still-current protected route again. The remounted exam workspace requests `/exam-workspace/documents` on mount and, with no exam open, opens the Öppna drawer, which requests `/exam-workspace/unreadable-documents`. Both requests get 401 and each shows the list failure toast.

Behaviour:

1. After sign-out, the signed-out frame never mounts a route that needs sign-in, so no exam workspace request is sent and no list failure toast appears.
2. The landing page still arrives after sign-out.

## Contract Inputs

- The router guard in `router/index.ts` already sends a signed-out navigation to a protected route to sign-in; the signed-out frame follows the same rule.

## Core Vertical And Performance

One sign-out from the exam workspace in a real browser on staging, with no list request after the click.

## Validation

- A fail-first App shell spec: a protected page mounts once and unmounts once on sign-out, and the landing page mounts.
- Focused Vitest for the App shell specs, `fe-type-check` and `fe-lint`.

## Stop Conditions

- The fix needs a change in backend session handling or HuleEdu sign-out.
- The fix changes anything the user sees beyond removing these toasts.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D1  | The fix is in the shell: the signed-out frame does not render a route that needs sign-in. The saved-list and unreadable-list error toasts stay as they are for real list failures. |
| D2  | The same rule covers a session that expires on a protected page, which reaches the same remount before the shell sends the teacher to sign-in. |
| D3  | The order in `onLogout` stays: sign out first, then go to the landing page, so a failed sign-out keeps the teacher on the page. |
