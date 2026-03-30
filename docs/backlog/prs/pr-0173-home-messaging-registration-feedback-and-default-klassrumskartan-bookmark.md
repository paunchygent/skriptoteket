---
type: pr
id: PR-0173
title: "Home messaging, registration feedback, and default Klassrumskartan bookmark"
status: in_progress
owners: "agents"
created: 2026-03-30
updated: 2026-03-30
stories:
  - "ST-02-08"
  - "ST-11-24"
  - "ST-16-09"
tags: ["frontend", "identity", "personalization", "curated-apps"]
acceptance_criteria:
  - "Klassrumskartan is bookmarked by default for existing and newly registered users, while still remaining removable."
  - "The unauthenticated home page speaks honestly about the current alpha role model and emphasizes the curated teacher library rather than universal self-service creation."
  - "The registration page surfaces email-domain and password feedback before submit and adds visible password toggles."
---

## Problem

Three small but user-visible trust problems are stacked together right now:

1. the flagship classroom app is too easy to miss unless a user bookmarks it manually,
2. the landing page still oversells self-service script creation for ordinary users, and
3. the registration form waits too long before explaining why an email domain or password is
   unacceptable.

## Goal

Ship one focused UX polish slice that:

1. defaults the most important curated classroom app into bookmarks,
2. resets the landing page to the current curated-library reality, and
3. gives registration users immediate, clear, inline feedback.

## Non-goals

- A new contributor-application workflow or admin approval form.
- Broad redesign of the authenticated dashboard shell.
- Reworking the underlying role model.
- Changing the final backend registration authority away from the existing handler.

## Implementation plan

### 1. Docs and planning

- Add one story per tweak area (`ST-02-08`, `ST-11-24`, `ST-16-09`).
- Update the relevant epic references and `docs/index.md`.

### 2. Default Klassrumskartan bookmark

- Backfill a persisted curated-app favorite row for existing users.
- Add the same favorite on future registration.
- Keep remove/unfavorite behavior unchanged so the default remains opt-out.

### 3. Landing-page reset

- Rewrite the unauthenticated hero/supporting copy in `HomeView.vue`.
- Emphasize login, trusted teacher tools/apps, colleague sharing, and GDPR-safe handling.
- Remove copy that implies normal users can create tools immediately.

### 4. Registration preflight feedback

- Add an anonymous registration-validation endpoint for field-level preflight checks.
- Wire the register view to debounce email checks, show inline field messages, and expose password
  visibility toggles.
- Keep submit-time backend validation authoritative.

## Test plan

### Backend

- Registration handler/unit coverage for default favorite creation.
- Validation handler/route coverage for domain, duplicate-email, and password outcomes.
- Migration/idempotency coverage for the default-favorite backfill.

### Frontend

- Home-view unit coverage for the updated pre-login content.
- Register-view or composable coverage for inline validation and password toggles.

### Manual proof

- Run local backend + SPA.
- Confirm Klassrumskartan is initially bookmarked for an existing user, then removable.
- Confirm the unauthenticated landing page no longer promises universal script creation.
- Confirm `/register` shows domain/password feedback before submit and allows password visibility
  toggles.

## Rollback plan

- Revert the home/register SPA changes.
- Remove the default-favorite registration hook.
- Downgrade the backfill migration if the default bookmark decision needs to be withdrawn.
