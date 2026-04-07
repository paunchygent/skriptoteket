---
type: story
id: ST-32-06
title: "Klassrumskartan demo adoption on the public browser-workspace profile"
status: done
owners: "agents"
created: 2026-04-03
updated: 2026-04-07
epic: "EPIC-32"
dependencies: ["ADR-0080", "ST-32-02", "ST-32-03", "ST-32-04", "ST-32-05", "EPIC-27", "EPIC-29"]
acceptance_criteria:
  - "Given Klassrumskartan is the first public browser-workspace consumer, when its guest capability matrix is finalized, then guest-allowed, guest-altered, and guest-blocked flows are explicitly documented across rosters, templates, smart rules, drafts, smart runs, history, import preview, and export."
  - "Given guest Klassrumskartan export is supported, when the target design is reviewed, then export is direct-download and Vault/MyFiles-free while the current authenticated export-job/recover/download flows remain unchanged."
  - "Given guest Klassrumskartan still needs import preview and smart runs, when those server-assisted flows are reviewed, then parsing/compute stay server-side through the public helper namespace while durable guest workspace persistence remains browser-owned."
  - "Given EPIC-27 makes `Regler` the dedicated smart-rule authoring home, when guest Klassrumskartan is specified, then smart-rule read/edit behavior, guest-local persistence, upgrade semantics, and blocked authenticated-only deep links/affordances are explicit."
  - "Given a user later signs in, when Klassrumskartan detects local guest work, then the guest snapshot is offered for explicit authenticated upgrade without silently re-homing state during registration or on incidental auth transitions."
  - "Given the demo ships as the first adoption proof, when validation is planned, then guest authoring, guest local-continuity, guest-export, guest-reset, login-upgrade, registration-then-login-upgrade, and unchanged authenticated Klassrumskartan journeys are all enumerated."
ui_impact: "Introduces Klassrumskartan guest/demo entry, local-work notices, blocked authenticated-only affordances, and first-auth-session import prompts."
data_impact: "No guest server persistence; authenticated import/orchestration only after login."
---

## Context

This story converts the cross-app public-access foundation into one concrete,
reviewable first consumer: Klassrumskartan.

## Notes

- Keep the current authenticated Klassrumskartan planner/API model intact.
- Do not turn guest access into a hidden exception inside the existing
  owner-scoped handlers.
- Smart rules are first-class guest scope, not an implied subcase of “smart
  runs” or “history.”
- Guest history semantics must stay honest:
  - undo/redo is local editing state
  - local draft restore/history is local continuity
  - history-based Smart and `use_history` are authenticated-only
- Checkpoint payload note: browser-owned guest snapshots now carry canonical
  importable checkpoint payloads for authenticated upgrade; do not reintroduce
  metadata-only checkpoint compatibility or `skipped` fallback behavior without
  a new explicit docs-as-code decision.
- Guest capability lock for this story:
  - rosters, templates, smart rules, and drafts are fully authorable in the
    browser-owned guest workspace
  - `Regler` and the expandable Smart settings drawer are part of guest parity
  - import preview and solver-based Smart compute may stay server-assisted only
    through stateless public helper flows
  - guest export stays direct-download only
  - account-owned history, recovery, jobs, and other owner-scoped affordances
    stay explicitly blocked or signposted
  - guest mode must not expose `use_history` or treat guest-local checkpoints
    as a Smart-history lane
- Upgrade trigger lock: detect pending guest work only on the first
  authenticated Klassrumskartan visit, not during registration, generic site
  login, or incidental auth changes elsewhere.
- Reset affordance lock: use the user-facing action label `Kasta`
  with plain-language browser/shared-device copy; do not expose internal guest
  storage terminology in the visible UI.
- UI parity lock: guest mode should look and behave like the logged-in
  Klassrumskartan workspace by default, not like a separate demo product.
  Differences should stay minimal and explicit:
  - account-owned affordances may be disabled/greyed out with short tooltips
  - one small system message or banner may explain in plain user Swedish that
    some functions require an account
  - do not introduce a separate guest-specific layout language, large explainer
    cards, or heavy upsell surfaces
- `PR-0223` checkpoint 3 is now verified end-to-end: the public overview shell
  swaps into a dedicated guest planner shell, grouping/seating drafts resume
  from the browser-owned snapshot across overview round-trips and reloads.
- `ADR-0080` now freezes the remaining guest/auth Smart boundary for this
  story:
  - guest parity includes `Regler`, the expandable Smart settings drawer, and
    solver-based Smart runs through public stateless helper seams
  - guest parity excludes history-based Smart and `use_history`
  - guest export checkpoints may support continuity/import later, but they do
    not create a guest Smart-history lane
- The remaining implementation scope is now split into one guest Smart parity
  slice and one guest local-continuity/export slice, so `PR-0223` can stay
  closed around the shipped public browser-workspace baseline.

## Implementation Summary (as of 2026-04-07)

- `PR-0223` shipped the public browser-owned baseline: dedicated public host
  routing, browser-owned guest snapshots, overview-first guest authoring, and
  resumable local grouping/seating drafts.
- `PR-0231` shipped guest `Regler`, solver-backed public Smart helpers, and
  the explicit guest/auth Smart-history boundary from `ADR-0080`.
- `PR-0232` shipped guest-local undo/redo, direct-download public grouping and
  seating exports, export-backed checkpoint persistence on the guest snapshot,
  and continued omission of account-owned history/recovery/job affordances.
- `PR-0233` hardened the authenticated upgrade seam so non-toy template-bearing
  guest snapshots with reused template geometry import cleanly instead of
  reproducing the old template-remap `500`.
- `PR-0234` fixed the public overview -> grouping classroom-context regression
  and the stale enabled `Sittplatser` affordance after classroom context was
  lost.
- `PR-0236` closed the remaining overview action-capability and import-boundary
  proof gaps.
- The pushed review-follow-up pass also locked down direct public export route
  argument forwarding, invalid handler branches, the draft-autosave proof
  surface, and OpenAPI-safe typing for the new public route modules.

## Delivered PR slices

- [PR-0223: ST-32-06 public Klassrumskartan demo capability matrix and
  browser-workspace adoption](../prs/pr-0223-st-32-06-public-klassrumskartan-demo-capability-matrix-and-browser-workspace-adoption.md)
- [PR-0231: ST-32-06 guest Regler workspace, solver-Smart parity, and
  expandable Smart settings drawer](../prs/pr-0231-st-32-06-guest-regler-workspace-solver-smart-parity-and-expandable-smart-settings-drawer.md)
- [PR-0234: ST-32-06 follow-up: guest grouping classroom-context persistence
  and seating affordance hardening](../prs/pr-0234-st-32-06-guest-grouping-classroom-context-persistence-and-seating-affordance-hardening.md)
- [PR-0236: ST-32-06 follow-up: overview action-capability test realignment
  and import-boundary assertions](../prs/pr-0236-st-32-06-overview-action-capability-test-realignment-and-import-boundary-assertions.md)
- [PR-0232: ST-32-06 guest local draft parity, direct-download export, and
  account-only history affordance polish](../prs/pr-0232-st-32-06-guest-local-draft-parity-direct-download-export-and-account-only-history-affordance-polish.md)

## References

- Epic parent:
  [EPIC-32](../epics/epic-32-public-curated-app-access-foundation-and-klassrumskartan-demo.md)
- Public curated-app access boundary:
  [ADR-0079](../../adr/adr-0079-public-curated-app-access-profiles-and-guest-state-boundaries.md)
- Klassrumskartan guest Smart parity boundary:
  [ADR-0080](../../adr/adr-0080-klassrumskartan-guest-smart-parity-and-history-based-smart-boundary.md)
- Authenticated upgrade foundation:
  [ST-32-05](story-32-05-authenticated-upgrade-orchestration-and-idempotent-import-policy.md)
