---
type: pr
id: PR-0299
title: "ST-13-02: auth and critical action feedback toast audit"
status: done
owners: "agents"
created: 2026-05-05
updated: 2026-05-05
stories:
  - "ST-13-02"
  - "ST-13-03"
tags: ["frontend", "ux-copy", "auth", "toast", "system-messages"]
dependencies:
  - "ADR-0037"
  - "REF-toast-system-messages"
  - "EPIC-28"
acceptance_criteria:
  - "Given logout fails from the authenticated shell, when the failure is a transient action failure, then the app shows dismissible toast feedback without inserting a full-width panel into the workspace layout."
  - "Given the logout failure is network-like or timeout-like, when the replacement copy is selected, then the locked Swedish copy starts from the user-preferred candidate `Det gick inte att logga ut just nu. Kontrollera din internetanslutningen och klicka på Logga ut igen.` and the implementation records whether the final shipped copy keeps that exact wording or corrects it after copy review."
  - "Given a logout failure is not network-like, when the app shows recovery copy, then it does not incorrectly blame the user's internet connection and instead uses action-specific retry copy."
  - "Given auth/session/CSRF/bootstrap failures are surfaced to users, when the implementation reviews them, then each message is classified as transient action feedback, blocking system state, or developer-only/internal error before changing the UI channel."
  - "Given similar inline or ad-hoc error panels exist in the SPA, when they are transient user-action failures, then they move to the existing toast failure channel instead of adding layout-shifting chrome."
  - "Given an inline error remains necessary because it blocks page use, validation, lockout, or required setup, when it renders, then it uses the shared dismissible `SystemMessage` primitive or an explicitly documented equivalent near the cause."
  - "Given critical/destructive action failures are non-blocking, when they are displayed, then they use the shared `failure` toast semantics and warm terracotta visual channel rather than raw inline `border-error` panels."
  - "Given the audit finds raw English fallback strings or backend/internal wording in Swedish user-facing UI, when they are in scope for the touched paths, then they are replaced with short Swedish action-and-next-action copy."
---

## Problem

The authenticated shell can render logout failures as a large, non-dismissible,
full-width inline panel above the current workspace. In Klassrumskartan this
creates considerable chrome, shifts the working surface, and competes with the
teacher's task even though logout failure is a button-triggered transient action
failure.

The first traced example is:

- `frontend/apps/skriptoteket/src/stores/auth.ts`: logout timeout copy
- `frontend/apps/skriptoteket/src/App.vue`: catches `auth.logout()` failure
  and stores the raw error message
- `frontend/apps/skriptoteket/src/components/layout/AuthLayout.vue`: renders
  the raw message as an ad-hoc inline panel

The repo already has ADR-0037 and `REF-toast-system-messages`: transient action
feedback belongs in the toast overlay, while blocking/long-lived states remain
inline and dismissible. This slice closes the drift for auth/logout and audits
similar high-impact ad-hoc error surfaces before changing code.

## Goal

Make critical and auth-adjacent user feedback less noisy and more helpful:

- Replace logout transient failures with the existing dismissible failure toast.
- Lock or deliberately revise the logout recovery copy after a small copy review.
- Audit similar inline/ad-hoc action failure panels before migrating them.
- Keep truly blocking errors inline, but use the shared `SystemMessage` contract.
- Ensure critical/destructive non-blocking failures use the same failure-toast
  behavior and warm terracotta visual semantics as the rest of the SPA.

## Non-goals

- Changing HuleEdu logout, session, CSRF, or product-realm behavior.
- Changing backend auth contracts, HTTP status semantics, or Gateway ownership.
- Toastifying blocking page-load failures, form validation errors, lockouts, or
  required provisioning states.
- Redesigning the whole toast system or introducing a second notification store.
- Rewriting every historical `errorMessage` in the SPA; the implementation must
  stop at the audited auth/critical-action surfaces that match ADR-0037.

## Copy and channel review

Start from this user-preferred logout timeout/network candidate:

`Det gick inte att logga ut just nu. Kontrollera din internetanslutningen och klicka på Logga ut igen.`

Before shipping, evaluate and record:

- whether the failure was actually timeout/network-like enough to mention the
  internet connection
- whether the final copy should keep the exact candidate or use the idiomatic
  Swedish form `din internetanslutning`
- whether non-network logout failures should instead use:
  `Det gick inte att logga ut just nu. Klicka på Logga ut igen.`

For every touched message, use the shared recovery-copy rule: name the failed
visible action and the next visible action; do not expose transport details,
service names, field names, exception names, or backend English.

Implementation result:

- Logout timeout/network copy ships with the idiomatic Swedish correction:
  `Det gick inte att logga ut just nu. Kontrollera din internetanslutning och klicka på Logga ut igen.`
- Generic logout failures ship as:
  `Det gick inte att logga ut just nu. Klicka på Logga ut igen.`
- Auth/logout, vault delete/restore, Klassrumskartan share create/revoke,
  historical draft delete, editor maintainer add/remove, sandbox file delete,
  and admin critical action fallback failures now use the failure toast channel
  where the failure is transient and non-blocking.
- Overview/modal destructive confirmations remain inline near the action, but
  use dismissible `SystemMessage` where the user can retry or cancel.

## Implementation plan

1. Inventory current ad-hoc feedback surfaces.
   - Search `frontend/apps/skriptoteket/src` for `logoutError`, `errorMessage`,
     `border-error`, `text-error`, `role=\"alert\"`, `SystemMessage`,
     `toast.failure`, `Failed`, and timeout messages.
   - Classify each touched candidate as transient action, blocking state,
     validation, tool-run output, or internal/developer-only.
   - Keep the implementation list narrow and record explicitly why any visible
     raw inline panel remains.

2. Centralize auth-facing copy for the touched paths.
   - Add a small typed helper/module for auth user messages if the audit shows
     more than one auth message should change.
   - Keep timeout classification separate from generic HTTP/server failures so
     connection advice is not shown for the wrong cause.

3. Move logout transient failures to toasts.
   - Use `useToast().failure(...)` from `App.vue` or a small shell helper.
   - Remove `logoutError` prop drilling and the ad-hoc `AuthLayout` panel when
     no blocking auth-shell case still uses it.
   - Keep `Logga ut` as the visible retry action.

4. Normalize similar critical action failures.
   - Migrate only audited non-blocking critical/destructive action failures to
     failure toasts.
   - Keep blocking errors in flow with `SystemMessage` and a close control.
   - Avoid new full-width banners in dense workspaces.

5. Update tests and proof.
   - Add focused tests proving logout timeout/network-like failure uses a
     dismissible failure toast and does not render the layout-shifting panel.
   - Add tests for non-network logout failure copy if the implementation
     distinguishes causes.
   - Add focused tests for any additional migrated critical action surfaces.

## Test plan

- `pdm run python -m scripts.playwright_pr_0299_logout_failure_toast`
- `pdm run fe-test -- src/App.spec.ts src/components/layout/AuthLayout.spec.ts src/views/apps/classroomPlannerPublicShareFlow.spec.ts src/views/apps/classroomPlannerShareFlow.spec.ts src/views/apps/classroomPlannerRouteShellWorkspace.spec.ts src/components/vault/VaultPanel.spec.ts`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run docs-validate`
- `pdm run handoff-validate` if `.codex/handoff.md` records close-out evidence
- `git diff --check`
- Live browser proof on the authenticated shell:
  `pdm run python -m scripts.playwright_pr_0299_logout_failure_toast` passed
  after applying the pending local DB migration with `pdm run db-upgrade`.
  The proof uses the signed local HuleEdu continuation harness, forces the
  shared logout endpoint past the frontend timeout, verifies the exact failure
  toast copy, verifies the close control, verifies the message is not rendered
  inside `main`, and verifies the Klassrumskartan heading does not shift.
  Screenshot artifact:
  `.artifacts/playwright-pr-0299-logout-failure-toast/logout-failure-toast.png`.

## Rollback plan

Revert the frontend toast/channel changes and any copy helper introduced in this
slice. If rollback is needed after partial migration, keep the shared
`SystemMessage` primitive for any blocking errors already converted, but restore
logout failure handling to the previous shell-level path until the toast failure
path is corrected.
