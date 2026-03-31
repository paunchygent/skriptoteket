---
type: story
id: ST-16-09
title: "Default Klassrumskartan bookmark"
status: done
owners: "agents"
created: 2026-03-30
updated: 2026-03-31
epic: "EPIC-16"
acceptance_criteria:
  - "Given an existing user account when this slice is applied, then `Klassrumskartan` appears as a bookmarked curated app in the user's favorites surfaces without requiring a manual first bookmark."
  - "Given a newly registered user account, when registration succeeds, then `Klassrumskartan` is bookmarked for that account by default."
  - "Given a user removes the default `Klassrumskartan` bookmark from home or browse, when they refresh or revisit the app later, then the bookmark stays removed for that account."
  - "Given catalog, home favorites, and recent-items surfaces render the curated app after this slice, when they resolve favorite state, then all surfaces agree on the same bookmarked/unbookmarked state."
dependencies: ["ST-16-01", "ST-16-02", "ST-16-07"]
ui_impact: "Klassrumskartan appears pre-bookmarked in existing favorites-aware surfaces for current and future users."
data_impact: "One-time backfill of curated-app favorites for existing users plus default favorite creation during future registrations."
---

## Context

Teachers should be able to discover the most important curated apps immediately. Right now the
favorite/bookmark system is opt-in only, which makes flagship curated apps easy to miss even when
they are already first-class product modules.

## Implementation notes

### Default bookmark behavior

- Treat `classroom.group-seating-studio` / `Klassrumskartan` as the first default-curated bookmark.
- Persist the default as a normal favorite row instead of a frontend-only illusion so opt-out is
  stable across devices and sessions.

### Existing + future users

- Backfill the default bookmark for current users via a one-time migration/data step.
- Add the same favorite automatically when a new user self-registers.
- Keep the operation idempotent; duplicate rows must not fail.

### Opt-out

- Unbookmarking should delete the persisted favorite row and must not be re-added automatically on
  the next page load for that account.

### Verification

- Favorites handler/repository tests proving the curated app remains removable after the backfill.
- Registration handler coverage proving new users receive the default favorite.
- Migration/idempotency coverage for the one-time backfill.
- Manual proof in local dev that:
  - Klassrumskartan shows up in `Dina favoriter` for a current user
  - removing the bookmark hides it immediately
  - reloading preserves the removal
