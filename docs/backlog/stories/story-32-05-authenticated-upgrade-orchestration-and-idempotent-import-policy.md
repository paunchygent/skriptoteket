---
type: story
id: ST-32-05
title: "Authenticated upgrade orchestration and idempotent import policy"
status: done
owners: "agents"
created: 2026-04-03
updated: 2026-04-08
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
data_impact: "Ships authenticated guest-upgrade receipts, durable imported-draft identity lookup, and end-to-end preservation of imported planner draft metadata such as `task_entry_classroom_selection_mode`."
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
- `PR-0221` shipped the initial authenticated upgrade boundary, but live
  authenticated proof on 2026-04-07 also surfaced a pre-existing
  template-bearing preview failure inside the exact-template reuse/remap seam.
  That corrective lane is now explicitly owned by `PR-0233` rather than being
  worked around from `ST-32-06`.
- Live authenticated proof on 2026-04-08 surfaced a separate frontend truth-gap:
  an empty browser snapshot can still trigger the prompt and an all-zero
  guest-upgrade receipt can still render the `import complete` summary while
  the route shell simultaneously reopens an already-existing backend roster.
  That UI reconciliation lane is now explicitly owned by `PR-0245`.
- Live testing later on 2026-04-08 clarified a product-policy correction:
  Klassrumskartan guest-upgrade is intended to be a one-time onboarding bridge
  from browser-owned guest work into a first authenticated account session in
  one browser, not a repeatable logged-out/logged-in import loop. That
  one-time-consumption and repeat-import suppression lane is now explicitly
  owned by `PR-0246`.
- The current recommended `PR-0246` direction is not browser-only suppression.
  It is a hybrid model: one backend-owned canonical consumption fact per
  user/app plus one browser-owned authoring-closure marker for same-browser
  stale snapshot cleanup and public guest re-entry suppression. This keeps the
  product rule reviewable as a durable backend fact instead of inferring it
  from planner drafts or browser state alone.
- `REV-PR-0246` narrows that recommendation in two important ways before
  implementation:
  - the backend canonical fact is for authenticated policy/debugging only, not
    for public-host decisions
  - suspicious all-zero `200` receipts must remain non-consuming so the
    truthful zero-effect guard from `PR-0245` is preserved

## Planned PR slices

- [PR-0221: ST-32-05 authenticated upgrade orchestration and idempotent import
  policy foundation](../prs/pr-0221-st-32-05-authenticated-upgrade-orchestration-and-idempotent-import-policy-foundation.md)
- [PR-0233: ST-32-05 follow-up: authenticated guest-upgrade template reuse and
  seat-remap hardening](../prs/pr-0233-st-32-05-follow-up-authenticated-guest-upgrade-template-reuse-and-seat-remap-hardening.md)
- [PR-0245: ST-32-05 follow-up: empty guest snapshot and zero-effect import UI
  reconciliation](../prs/pr-0245-st-32-05-empty-guest-snapshot-and-zero-effect-import-ui-reconciliation.md)
- [PR-0246: ST-32-05 follow-up: one-time guest-upgrade consumption and
  repeat-import suppression](../prs/pr-0246-st-32-05-one-time-guest-upgrade-consumption-and-repeat-import-suppression.md)
- [PR-0249: ST-32-05 follow-up: singular login-first blocked state for closed
  public guest mode](../prs/pr-0249-st-32-05-singular-login-first-blocked-state-for-closed-public-guest-mode.md)

## References

- Epic parent:
  [EPIC-32](../epics/epic-32-public-curated-app-access-foundation-and-klassrumskartan-demo.md)
- Public curated-app access boundary:
  [ADR-0079](../../adr/adr-0079-public-curated-app-access-profiles-and-guest-state-boundaries.md)
- Browser-owned guest-state foundation:
  [ST-32-04](story-32-04-browser-owned-guest-state-profiles-and-snapshot-contracts.md)
- Related guest continuity consumer:
  [ST-32-06](story-32-06-klassrumskartan-demo-adoption-on-the-public-browser-workspace-profile.md)
