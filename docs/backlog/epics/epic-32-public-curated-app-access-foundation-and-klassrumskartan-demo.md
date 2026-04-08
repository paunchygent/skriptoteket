---
type: epic
id: EPIC-32
title: "Public curated-app access foundation and Klassrumskartan demo"
status: active
owners: "agents"
created: 2026-04-03
updated: 2026-04-08
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
- [ST-32-07: Public landing entry hierarchy and mockup-grounded CTA cutover](../stories/story-32-07-public-landing-entry-hierarchy-and-mockup-grounded-cta-cutover.md)
- [ST-32-08: Featured public-app showcase and authenticated-value previews](../stories/story-32-08-featured-public-app-showcase-and-authenticated-value-previews.md)
- [ST-32-09: Canonical public-route recovery and SPA unmatched state](../stories/story-32-09-canonical-public-route-recovery-and-spa-unmatched-state.md)
- [ST-32-10: Dedicated auth-entry page and redirect-preserving login handoff](../stories/story-32-10-dedicated-auth-entry-page-and-redirect-preserving-login-handoff.md)

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

## Implementation Summary (as of 2026-04-08)

- `ST-32-05` is now shipped through `PR-0221`: authenticated
  Klassrumskartan host entry is gated behind an explicit guest-upgrade prompt,
  the authenticated `/api/v1/apps/classroom.group-seating-studio/guest-upgrade`
  boundary now server-recomputes snapshot/entity fingerprints before import
  decisions, repeat commits dedupe imported historical drafts through the
  durable `guest_import_identity` lookup seam, and the frontend now keeps the
  local guest snapshot when commit receipts contain conflicts while showing a
  dismissible post-import summary after durable success. `PR-0233` is now also
  shipped, so the earlier exact-template reuse/remap defect for non-toy
  template-bearing snapshots is closed without changing the approved
  guest/public boundary shape. A further 2026-04-08 follow-up now narrows the
  product contract again through `PR-0246`: the browser guest-upgrade bridge is
  being converted into a one-time onboarding import, not a reusable
  logged-out/logged-in repeat-import loop.
- `ST-32-06` is now shipped as the first full
  `public_browser_workspace_with_upgrade` adoption proof for a real curated
  app:
  - `PR-0223` established the public host/bootstrap boundary and browser-owned
    guest workspace baseline
  - `PR-0231` added guest `Regler`, solver-backed public Smart helpers, and the
    explicit guest/auth Smart-history split from `ADR-0080`
  - `PR-0232` added guest-local undo/redo, direct-download public grouping and
    seating exports, and export-backed checkpoint continuity without reopening
    authenticated export-job/history/recovery seams
  - `PR-0234` fixed the public overview -> grouping classroom-context drop and
    stale seating affordance enablement
  - `PR-0236` closed the remaining overview capability and import-boundary test
    gaps
  - the pushed review-follow-up pass then tightened direct public export route
    forwarding, invalid export-handler branch coverage, autosave proof
    strength, OpenAPI-safe route typing, and the SPA Vitest path-normalization
    wrapper
- Follow-up planning after `ST-32-06` is now split into explicit story-level
  implementation units instead of one catch-all container:
  - `ST-32-07` is now shipped through `PR-0237` and `PR-0238`:
    - `PR-0237` locked the public landing blueprint around
      `docs/mockups/st-32-07-public-landing-discoverability/index.html`
    - `PR-0238` shipped the signed-out header/hero cutover, restored in-place
      login redirect semantics for public-host and auth-only signed-out routes,
      and extracted the landing classroom illustration into a dedicated home
      component without pulling `ST-32-08` showcase scope into the slice
  - `ST-32-08` is now shipped through `PR-0239`:
    - the generic signed-out landing highlight cards were replaced with a
      featured `Klassrumskartan` showcase and an authenticated-only ledger
      preview, both grounded in the locked `PR-0237` layout direction
    - the showcase keeps the hero's single strong CTA discipline by using a
      quieter public-app text link below the fold rather than adding a second
      competing CTA treatment
    - the authenticated preview footer still reuses the current in-place login
      modal seam for this launch slice, but a follow-up PR task should replace
      that overloaded signed-out auth entry with a dedicated redirect-friendly
      auth page that is better aligned with future HuleEdu SSO needs
  - `ST-32-09` owns malformed public-route recovery and visible SPA unmatched
    state handling
  - `ST-32-10` now captures the planned auth-entry follow-up after `PR-0240`:
    a dedicated page-based login handoff that replaces the overloaded
    signed-out modal entry seam without reviving the old legacy `/login`
    behavior
