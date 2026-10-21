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
  status: approved
  reviewer: ruthless-reviewer
  decided_at: '2026-10-21'
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

## Progress

### 2026-10-21 (Hemma orchestrator)

- Repair `7b6f17a7` on `codex/st-skript-40-04`: `App.vue` `requiresSignIn(route)` keeps the signed-out frame from rendering a protected route; `App.signOut.spec.ts` (four cases) fails before and passes after; the three App-shell suites pass 18/18, with frontend typecheck, lint and docs validation green (retained root `01a15f58-90ab-7006-b41e-b9d7ee5a13fc`, `evidence/sign-out-*`).
- Pi ruthless-reviewer `4156e084` approved with no findings (`evidence/results/4156e084-7626-4159-82c0-9e6ec84f3453.json`). Non-blocking note: the shell check reads matched records and any `minRole` string, while the router guard reads merged meta and recognised roles; they agree for the current flat route table.
- Merged to main with `--no-ff`. Owed: the staging walk of a real sign-out, then user closure.
- Mac staging walk at `4b321fa1` (Edge, 2026-10-21) passed: with an exam open and with no exam open, "Logga ut" lands on `/` with no saved-list toast, and no request reaches `/exam-workspace/documents` or `/exam-workspace/unreadable-documents` (Mac record `.artifacts/staging-walk-l1c-4b321fa1/walk-record.md`). Waits for user closure.
