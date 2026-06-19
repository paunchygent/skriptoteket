---
type: epic
id: EPIC-29
title: "Klassrumskartan — desktop-first workspace overhaul"
status: active
owners: "agents"
created: 2026-03-28
updated: 2026-06-18
outcome: "Teachers use the current denser, desktop-first Klassrumskartan workspace with compressed shell chrome, clearer task hierarchy, calmer overview/dashboard behavior, coherent grouping/seating/rules work surfaces, and a mockup-first small-screen companion lane that replaces cramped phone rails with mode-specific reduced layouts."
dependencies:
  [
    "ADR-0069",
    "ADR-0071",
    "ADR-0072",
    "EPIC-24",
    "EPIC-27",
    "REF-group-seating-studio-product-direction-2026-03-21",
    "REF-klassrumskartan-workspace-ui-doctrine-2026-03-28",
  ]
---

## Scope

- Apply the new workspace doctrine to Klassrumskartan as a dedicated redesign lane rather than as
  incidental polish inside export or smart-assignment work.
- Own the desktop-first redesign execution scope that was previously scattered across adjacent
  export-era hardening drafts so the planner does not carry two parallel ready redesign lanes.
- Design desktop and laptop layouts as the canonical product composition for workspace-heavy
  planner flows.
- Introduce and then harden a canonical symbol system and shared planner/site-app control
  primitives around the already-shipped desktop-first workspace.
- Compress the planner shell and remove low-value status/helper bands that delay access to the live
  work surface.
- Record the now-shipped `Översikt`, `Grupper`, `Sittplatser`, and `Regler` desktop-first behavior
  in one canonical epic and keep any remaining work focused on shared primitive, symbol, and
  discoverability tightening instead of reopening the core workspace layouts.
- Define reduced mobile companion layouts through separate mockup-first stories for the shared
  shell and each workspace rather than one generic phone layout.

## Out of Scope

- Changing planner domain behavior, smart-assignment contracts, export contracts, or room/roster
  persistence semantics.
- Reopening the accepted class-first workflow direction from EPIC-24.
- Treating desktop redesign as a reason to force full feature parity onto phone portrait layouts.
- Folding the entire overhaul into EPIC-26 export/import work or EPIC-27 smart-assignment work.

## Risks

- If symbol work and shell work are skipped, workspace redesigns may drift into one-off affordances.
- If mobile parity remains a hidden requirement, the desktop overhaul may collapse back into
  stacked-card compromises.
- If existing ready UX-hardening stories from EPIC-26 are implemented independently without
  reconciliation, the redesign lane could duplicate or conflict with adjacent toolbar/overview
  polish work.

## Viewport Proof Matrix

Use these named review viewports whenever EPIC-29 stories call for browser proof:

- `phone`: `390x844` reduced companion proof below the desktop composition range
- `tablet`: `768x1024` reduced companion proof aligned to the `ADR-0020` tablet breakpoint
- `laptop`: `1366x768` minimum full desktop-composition proof for teacher workspaces
- `desktop`: `1440x900` roomy full desktop-composition proof for teacher workspaces

Desktop-first Klassrumskartan composition must hold at `laptop` and `desktop`. Reduced companion
layouts may appear at `tablet` and `phone`, but they must not push stacked-card compromises back up
into the `laptop` proof width.

## Story Stack

- [ST-29-01: Canonical operation symbols and planner control primitives](../stories/story-29-01-klassrumskartan-canonical-operation-symbols-and-planner-control-primitives.md)
- [ST-29-02: Workspace shell compression and low-value feedback band reduction](../stories/story-29-02-klassrumskartan-workspace-shell-compression-and-low-value-feedback-band-reduction.md)
- [ST-29-03: Shared desktop workspace composition primitives](../stories/story-29-03-klassrumskartan-shared-desktop-workspace-composition-primitives.md)
- [ST-29-04: Overview hierarchy and class-first dashboard redesign](../stories/story-29-04-klassrumskartan-overview-hierarchy-and-class-first-dashboard-redesign.md)
- [ST-29-05: Grouping and seating desktop workspace overhaul](../stories/story-29-05-klassrumskartan-grouping-and-seating-desktop-workspace-overhaul.md)
- [ST-29-06: Rules workspace no-classroom fallback and organized off-map selection](../stories/story-29-06-klassrumskartan-rules-workspace-rail-map-inspector-rebalance.md)
- [ST-29-07: Reduced mobile companion layouts and breakpoint cutover](../stories/story-29-07-klassrumskartan-reduced-mobile-companion-layouts-and-breakpoint-cutover.md) — canceled as a broad implementation surface and split into `ST-29-13` through `ST-29-17`.
- [ST-29-08: Shared custom tooltip system and global hover contract](../stories/story-29-08-klassrumskartan-shared-custom-tooltip-system-and-global-hover-contract.md)
- [ST-29-09: Rule visibility and tool-feedback continuity](../stories/story-29-09-klassrumskartan-rule-visibility-and-tool-feedback-continuity.md)
- [ST-29-10: First-run workspace gating and prerequisite guidance](../stories/story-29-10-klassrumskartan-first-run-workspace-gating-and-prerequisite-guidance.md)
- [ST-29-11: Shared site/app dense-control primitive tightening](../stories/story-29-11-klassrumskartan-shared-site-and-app-dense-control-primitive-tightening.md)
- [ST-29-12: Canonical symbol language and discoverability contract completion](../stories/story-29-12-klassrumskartan-canonical-symbol-language-and-discoverability-contract-completion.md)
- [ST-29-13: Small-screen shell and mode-switcher redesign](../stories/story-29-13-klassrumskartan-small-screen-shell-and-mode-switcher-redesign.md)
- [ST-29-14: Small-screen overview redesign](../stories/story-29-14-klassrumskartan-small-screen-overview-redesign.md)
- [ST-29-15: Small-screen grouping redesign](../stories/story-29-15-klassrumskartan-small-screen-grouping-redesign.md)
- [ST-29-16: Small-screen seating redesign](../stories/story-29-16-klassrumskartan-small-screen-seating-redesign.md)
- [ST-29-17: Small-screen rules redesign](../stories/story-29-17-klassrumskartan-small-screen-rules-redesign.md)

## Notes

- `EPIC-29` is the canonical story/task hub for the Klassrumskartan UI overhaul.
- The core desktop-first workspace/layout lane is represented by shipped behavior in practice.
  The remaining active follow-on work now has two groups: shared primitive/symbol/discoverability
  tightening in `ST-29-08`, `ST-29-11`, and `ST-29-12`, plus the mockup-first small-screen
  companion lane in `ST-29-13` through `ST-29-17`.
- For planner-family workspace shells, layout geometry remains CSS-owned even in follow-on hardening
  work: shell/pane/rail/board/canvas size, position, sticky behavior, overflow ownership, and
  breakpoint cutover should be restored through shared containment and layout tokens rather than
  persistent runtime geometry math.
- `ST-29-08` is intentionally an enhancement follow-up after the remaining primitive and symbol
  definition/tightening lane rather than a blocker on the already-shipped workspace layouts.
- `ST-29-12` now owns the symbol-semantics inventory and decision lane for both shared site/app
  controls and Klassrumskartan domain symbols. Its next task sequence starts with
  `docs/mockups/st-29-12-symbol-inventory/index.html` and continues through `PR-0291` to `PR-0294`
  before runtime icon changes are made.
- `PR-0301` is closed as the `ST-29-11` follow-up for the overview `Dela och exportera` content
  selector: it keeps the `PR-0286` consolidation and replaces the stacked rows with the preferred
  rail toggle plus class-list/classroom draft confirmation.
- `PR-0303` is done as the cross-linked public guest overview wiring remediation; it keeps
  the `ST-29-11` overview rail presentation intact while fixing the `ST-26-06` share/export state
  path for public guest users.
- `ST-29-10` is a bounded reachability-and-copy slice only; it locks prerequisite-state affordances
  and approved Swedish guidance without adding walkthroughs, modals, or extra onboarding chrome.
- Approved small-screen workspace direction lives in
  `docs/mockups/st-29-small-screen-workspace-redesign/`.
- Applicable task decomposition from the earlier EPIC-26 redesign drafts is reassigned here and
  any conflicting story-level backlog docs should be removed rather than left around as dormant
  alternatives.
- This epic requires review approval before implementation begins per the repo review workflow.

## Implementation Summary (as of 2026-04-01)

- `ST-29-01` is now done through `PR-0156` and `PR-0157`: the shared control-language freeze, frontend design-system codemap, dense-tool primitive layer, and first canonical symbol assets are all now present in the SPA and already underpin later planner slices. The old `PR-0158` seating-first follow-up is canceled as stale planning and replaced by the broader follow-on stories `ST-29-11` and `ST-29-12`.
- `ST-29-02` is now implemented locally through `PR-0161`, `PR-0179`, and `PR-0180`: the planner shell is compressed, grouping and seating use detached sticky workspace toolbars that now hug the authenticated topbar seam while scrolling, low-value full-width helper/status bands are removed or localized, and recovered export completion now announces once via toast with `Mina filer` copy instead of reappearing workspace bands.
- `ST-29-09` shipped through `PR-0177`: seating no longer repeats active-rule state through a redundant pill, the room-editor tool palette now exposes clearer active-tool feedback, and grouped student cards preserve the shared smart-rule marker language after assignment.
- `ST-29-03` is now done: `PR-0128` remains the shipped split-pane/local-scroll lane, `PR-0130` remains the shipped seating-toolbar stability lane, and `PR-0129` now codifies the shared zoned `PlannerWorkspaceActionBar` contract with reusable `primary`, `context`, and `secondary` wrappers that grouping, seating, and later `ST-29-06` can share.
- `ST-29-04` is now done through `PR-0127`, `PR-0131`, and `PR-0132`: `Översikt` now behaves as the class-first dashboard the doctrine called for, with bounded roster overflow, clearer management hierarchy, and normalized resume/history affordances.
- `ST-29-05` is now done in practice through the current `ST-29-03`, `ST-29-02`, and `ST-29-09` behavior set: grouping and seating read as desktop work instruments with stable split-pane composition, compact local chrome, detached sticky action surfaces, and less stacked-card overhead.
- `ST-29-06` is now done through `PR-0185`: the no-classroom `Regler` planning-map state now uses the approved classroom guidance copy, off-map students render as an organized selectable roster with visible pending-selection order instead of a loose chip cloud, `Grupper` now uses the approved calmer helper copy, and the live proof is locked at `1366x768` and `1440x900` through `scripts/playwright_pr_0185_rules_no_classroom_fallback_check.py`.
- `ST-29-10` is now done through `PR-0182`, `PR-0183`, and `PR-0184`: first-run workspace reachability is now truthful in the shared selector, `Översikt` shows the approved compact prerequisite guidance plus `Hjälp` affordance copy, and `docs/mockups/st-29-10-first-run-workspace-gating/index.html` remains the canonical mockup/preview path that grounded the slice before the live shell changes.
- `ST-29-11` now has its current planner hardening set implemented through `PR-0224`, `PR-0225`, `PR-0226`, and `PR-0227`: shared planner shell parity is tightened across guest and authenticated mode, grouping now holds the explicit `480px` desktop floor with `56px` / `112px` group-card sizing, grouping autosave preserves the selected classroom instead of clearing `Sittplatser`, fresh grouping drafts now seed 4 groups consistently in both guest and authenticated mode, and the default 4-card desktop grouping board now proves exact `480px` two-row math at `1440x900` while populated cards retain a desktop `234px` minimum-height floor and can grow without forced internal scrolling.
- `PR-0228` is now closed as the bounded `ST-29-11` planner-shell follow-up: the local shell stays
  on the better CSS-owned baseline where page/workspace scroll replaces the earlier rejected
  bounded-pane model, the large top panel can scroll away, the toolbar becomes the sticky working
  band, and grouping/seating share the same `480px` class-list rail pattern. Close-out keeps the
  retained live browser proof on the authenticated real-data path while guest/auth parity is
  enforced through the shared shell implementation plus focused guest/auth shell specs.
- `PR-0359` backlog cleanup canceled the original `ST-29-11` planning trio
  `PR-0195`, `PR-0196`, and `PR-0197` on 2026-06-18 as absorbed by the later
  shipped dense-control/primitives work. The current `ST-29-11` implementation
  record is the later done sequence `PR-0224`, `PR-0225`, `PR-0226`,
  `PR-0227`, `PR-0228`, `PR-0281`, `PR-0286`, `PR-0287`, `PR-0301`,
  `PR-0302`, `PR-0305`, `PR-0306`, `PR-0308`, and `PR-0309`, not the older
  generic cleanup draft.
