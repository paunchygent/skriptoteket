---
type: epic
id: EPIC-32
title: "Public curated-app access foundation and Klassrumskartan demo"
status: active
owners: "agents"
created: 2026-04-03
updated: 2026-04-07
outcome: "Skriptoteket gains a reusable public curated-app access model with explicit per-app access profiles, separate public/authenticated seams, browser-owned guest-state rules, and authenticated upgrade boundaries; Klassrumskartan becomes the first approved `public_browser_workspace_with_upgrade` consumer without weakening the existing authenticated curated-app host or owner-scoped APIs."
dependencies:
  [
    "ADR-0009",
    "ADR-0023",
    "ADR-0075",
    "ADR-0079",
    "ADR-0080",
    "EPIC-27",
    "EPIC-29",
  ]
---

## Scope

- Introduce a reusable public curated-app access model rather than a
  Klassrumskartan-only auth exception.
- Keep public access opt-in per curated app and fail closed by default.
- Separate public curated-app entry/API seams from the current authenticated
  `/apps/:appId` host and `/api/v1/apps/{app_id}/...` APIs.
- Define the current curated-app classification matrix so future work can open
  additional apps without reopening the platform decision each time.
- Make Klassrumskartan the first consumer with browser-owned guest workspace
  state, direct-download export, server-side helper calls, and authenticated
  upgrade/import later.
- Preserve the current authenticated Klassrumskartan model and history/export
  semantics unless a guest-specific boundary explicitly changes them.
- Define public-route abuse controls, privacy posture, and support/telemetry
  expectations.

## Out of Scope

- Opening every curated app in the same release.
- Weakening `/apps/:appId` or `/api/v1/apps/{app_id}` into mixed guest/auth
  routes.
- Persisting guest rosters, templates, drafts, checkpoints, or similar work in
  owner-scoped account tables before login.
- Giving guest users Vault/MyFiles surfaces or recoverable export jobs.
- Cross-device guest sync.
- Anonymous document-conversion uploads for Conversion Hub.

## Risks

- Shared-device browser storage may expose student names unless privacy cues,
  TTL, and reset affordances are explicit.
- Public upload/compute/export helpers increase anonymous abuse risk.
- If public/app-specific seams are not kept parallel to authenticated seams, a
  future auth-bypass regression becomes more likely.
- Different curated apps may drift into incompatible guest behaviors unless the
  profile matrix is explicit and enforced.
- Guest-to-account import can duplicate or partially import work without clear
  fingerprints and idempotency rules.
- Product/support may over-assume that “public curated apps” means “all apps
  open” unless the initial app matrix is recorded clearly.

## Story Stack

- [ST-32-01: Curated-app public access profiles and current app matrix](../stories/story-32-01-curated-app-public-access-profiles-and-current-app-matrix.md)
- [ST-32-02: Dedicated public curated-app host and bootstrap boundary](../stories/story-32-02-dedicated-public-curated-app-host-and-bootstrap-boundary.md)
- [ST-32-03: Public curated-app API namespace and anonymous abuse controls](../stories/story-32-03-public-curated-app-api-namespace-and-anonymous-abuse-controls.md)
- [ST-32-04: Browser-owned guest-state profiles and snapshot contracts](../stories/story-32-04-browser-owned-guest-state-profiles-and-snapshot-contracts.md)
- [ST-32-05: Authenticated upgrade orchestration and idempotent import policy](../stories/story-32-05-authenticated-upgrade-orchestration-and-idempotent-import-policy.md)
- [ST-32-06: Klassrumskartan demo adoption on the public browser-workspace profile](../stories/story-32-06-klassrumskartan-demo-adoption-on-the-public-browser-workspace-profile.md)

## Notes

- Public curated-app access is a platform capability layered on top of
  curated-app architecture, not a replacement for it.
- `min_role=Role.USER` does not mean an app is public. Public entry must be
  declared explicitly.
- The first planning matrix is:
  - `classroom.group-seating-studio`
    - current_access_profile: `public_browser_workspace_with_upgrade`
  - `games.flunk_out_frenzy`
    - current_access_profile: `authenticated_only`
    - future_target_profile: `public_browser_runtime`
  - `chemistry.reagent_prep_chef`
    - current_access_profile: `authenticated_only`
    - future_target_profile: `public_stateless`
  - `documents.conversion_hub`
    - current_access_profile: `authenticated_only`
  - `demo.counter`
    - current_access_profile: `authenticated_only`
    - operational note: dev/demo-only, not part of the production public-access rollout
- The curated-app registry/definition is the canonical source of truth for the
  public-access profile consumed by router/bootstrap/API decisions.
- Klassrumskartan remains the first implementation target because it has the
  strongest product need and the clearest guest-to-account continuity problem.
- Future app adoption should become “classify + implement app-specific public
  seam” work, not another platform architecture debate.
- This epic requires review approval before implementation begins.

## Implementation Summary (as of 2026-04-07)

- `ST-32-05` is now shipped through `PR-0221`: authenticated
  Klassrumskartan host entry is gated behind an explicit guest-upgrade prompt,
  the authenticated `/api/v1/apps/classroom.group-seating-studio/guest-upgrade`
  boundary now server-recomputes snapshot/entity fingerprints before import
  decisions, repeat commits dedupe imported historical drafts through the
  durable `guest_import_identity` lookup seam, and the frontend now keeps the
  local guest snapshot when commit receipts contain conflicts while showing a
  dismissible post-import summary after durable success. A newly reproduced
  live defect remains in the exact-template reuse/remap seam for non-toy
  template-bearing snapshots; `PR-0233` now owns that focused hardening lane
  without changing the approved guest/public boundary shape.
- `ST-32-06` is now materially advanced through `PR-0223` checkpoints 1-3:
  the public Klassrumskartan route now uses the real browser-owned overview
  shell, guest roster/template authoring persists locally through the public
  seam, and the dedicated guest planner shell now resumes grouping/seating
  drafts across overview round-trips and reloads with passing focused browser
  proof. `PR-0223` is now docs-closed around that delivered baseline, while
  `ADR-0080` freezes the remaining guest Smart/history boundary:
  solver-based Smart parity, `Regler`, and the expandable Smart settings
  drawer remain part of guest parity, but history-based Smart and `Use history`
  stay account-only. The remaining `ST-32-06` work is now split into
  `PR-0231` (guest `Regler` + solver-Smart parity) and `PR-0232`
  (guest local undo/redo + direct-download export + account-only
  history/recovery polish).
