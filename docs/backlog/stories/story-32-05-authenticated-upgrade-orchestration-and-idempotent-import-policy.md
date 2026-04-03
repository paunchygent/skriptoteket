---
type: story
id: ST-32-05
title: "Authenticated upgrade orchestration and idempotent import policy"
status: ready
owners: "agents"
created: 2026-04-03
updated: 2026-04-03
epic: "EPIC-32"
dependencies: ["ST-32-04", "ADR-0079", "EPIC-27"]
acceptance_criteria:
  - "Given a local guest snapshot exists for an upgrade-capable curated app, when a real authenticated session is established, then the user receives an explicit prompt to import, discard, or postpone the local guest work."
  - "Given registration does not create a logged-in session cookie in the current auth model, when a new user registers, then migration is deferred until the first authenticated session instead of running automatically."
  - "Given guest work is imported, when the server processes the request, then one authenticated orchestration boundary uses stable snapshot identity plus per-entity fingerprints, returns created/reused/skipped/conflicted mappings, and behaves idempotently on repeat submission of the same snapshot."
  - "Given local guest rosters or templates collide with existing account-owned assets, when conflicts are handled, then exact-content matches reuse existing assets and same-name/different-content assets import non-destructively as separate assets."
  - "Given local guest grouping or seating drafts collide with an existing active account draft of the same roster and kind, when conflicts are handled, then the guest draft imports as historical by default and replacing the current active draft is an explicit opt-in path only."
  - "Given guest checkpoints collide with existing account checkpoints, when conflicts are handled, then checkpoints import additively with fingerprint dedupe rather than replacing existing history."
  - "Given migration succeeds or fails, when local guest storage is updated, then local guest state clears only after durable success and remains intact after failed or cancelled imports."
ui_impact: "Adds a first-auth-session guest import prompt and post-import summary behavior for upgrade-capable apps."
data_impact: "Likely requires authenticated import receipts/mapping data later; this story only locks the contract and conflict rules."
---

## Context

Guest-to-account continuity is the biggest place where a browser-owned guest
model can accidentally turn into a destructive or duplicate-heavy import flow.
That boundary therefore needs to be explicit before implementation begins.

## Notes

- This story applies only to upgrade-capable profiles such as Klassrumskartan's
  planned `public_browser_workspace_with_upgrade` profile.
- Undo/redo stacks are editing-state noise by default, not durable imported
  history.
- The import contract must be non-destructive by default and transactionally
  safe from the user's perspective.
- For Klassrumskartan-style planners, the one-active-draft-per-kind rule must
  be preserved; guest import must not silently replace the user's current active
  grouping or seating draft.
