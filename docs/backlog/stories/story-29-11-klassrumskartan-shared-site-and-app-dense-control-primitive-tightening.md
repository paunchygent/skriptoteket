---
type: story
id: ST-29-11
title: "Klassrumskartan — Shared site/app dense-control primitive tightening"
status: ready
owners: "agents"
created: 2026-04-01
updated: 2026-05-09
epic: "EPIC-29"
dependencies:
  - "ST-29-01"
  - "ST-29-05"
acceptance_criteria:
  - "Given dense controls now exist across overview, grouping, seating, rules, editor, and other tool-grade SPA surfaces, when this follow-on ships, then repeated control families use one shared primitive contract instead of surface-owned variants or wrapper-specific visual rules."
  - "Given shared dense controls still rely on local CSS overrides or toolbar-owned spacing, radius, disabled, focus, active, and disclosure behavior, when this story ships, then those rules live in the shared primitive layer and surface wrappers become thin adapters."
  - "Given planner/editor/tool surfaces still expose overlapping icon-button, menu-button, split-button, toggle, or segmented-switch abstractions, when this story is complete, then the remaining wrappers are intentional usage adapters rather than accidental competing sources of truth."
  - "Given browser proof is run on the current dense-control surfaces at the canonical `laptop` and `desktop` review widths, when this story is reviewed, then control rhythm and interaction polish stay consistent without reopening the shipped workspace layouts."
ui_impact: "Yes (shared dense-control primitives across planner/editor/app surfaces)"
data_impact: "No"
---

## Context

The desktop-first workspace overhaul is now largely represented by shipped layout behavior. What
remains is not another pass on overview/grouping/seating composition. The remaining gap is the
shared primitive layer that those surfaces depend on.

This story isolates the follow-on primitive-tightening work as a cross-surface design-system lane
instead of treating it as unfinished planner-layout implementation.

## Notes

- This is a post-core tightening story, not a feature-expansion or workflow-redesign story.
- The target is shared site/app primitive governance across Klassrumskartan and adjacent dense tool
  surfaces, not one more local planner toolbar pass.
- `ST-29-01` is now the shipped foundation story. This story picks up the still-open consolidation
  and adapter-thinning work that no longer belongs under the old `PR-0158` seating-first framing.
- Bounded planner shell/layout corrections are still allowed here when they restore the existing
  `ST-29-03` / `ST-29-05` desktop contract, but that restoration work must keep planner geometry
  CSS-owned and must not reopen the accepted workspace direction through new runtime sizing or
  breakpoint logic.

## Planned PR slices

- [PR-0195: ST-29-11 dense-control primitive contract normalization and generic menu/split behavior](../prs/pr-0195-st-29-11-dense-control-primitive-contract-normalization-and-generic-menu-split-behavior.md)
- [PR-0196: ST-29-11 planner wrapper thinning and action-surface adapter cleanup](../prs/pr-0196-st-29-11-planner-wrapper-thinning-and-action-surface-adapter-cleanup.md)
- [PR-0197: ST-29-11 editor/site adoption proof and segmented-toggle contract completion](../prs/pr-0197-st-29-11-editor-site-adoption-proof-and-segmented-toggle-contract-completion.md)
- [PR-0224: ST-29-11 desktop-first planner width stability and shrink-to-fit remediation](../prs/pr-0224-st-29-11-desktop-first-planner-width-stability-and-shrink-to-fit-remediation.md)
- [PR-0225: ST-29-11 desktop-first planner toolbar priority and overflow hardening](../prs/pr-0225-st-29-11-desktop-first-planner-toolbar-priority-and-overflow-hardening.md)
- [PR-0226: ST-29-11 shared planner shell parity and grouping viewport-height stabilization](../prs/pr-0226-st-29-11-shared-planner-shell-parity-and-grouping-viewport-height-stabilization.md)
- [PR-0227: ST-29-11 exact two-row grouping board height contract at desktop baseline](../prs/pr-0227-st-29-11-exact-two-row-grouping-board-height-contract-at-desktop-baseline.md)
- [PR-0228: ST-29-11 follow-up: desktop student-pool rail stickiness restoration](../prs/pr-0228-st-29-11-follow-up-desktop-student-pool-rail-stickiness-restoration.md)
- [PR-0229: ST-29-11 follow-up: desktop-first planner toolbar breakpoint overflow escalation and undo/redo shortcut parity](../prs/pr-0229-st-29-11-desktop-first-planner-toolbar-breakpoint-overflow-escalation-and-undo-redo-shortcut-parity.md)
- [PR-0281: ST-29-11 toolbar processing spinner and status-pill removal](../prs/pr-0281-st-29-11-toolbar-processing-spinner-and-status-pill-removal.md)
- [PR-0282: ST-26-06 shared-link PDF download spinner contract](../prs/pr-0282-st-26-06-shared-link-pdf-download-spinner-contract.md)
- [PR-0286: ST-29-11 share/export affordance consolidation](../prs/pr-0286-st-29-11-share-export-affordance-consolidation.md)
- [PR-0287: ST-29-11 Smart settings popover persistence](../prs/pr-0287-st-29-11-smart-settings-popover-persistence.md)
- [PR-0301: ST-29-11 overview share/export scope rail and draft confirmation](../prs/pr-0301-st-29-11-overview-share-export-scope-rail-and-draft-confirmation.md)
- [PR-0302: ST-29-11 planner toolbar Smart overflow default remediation](../prs/pr-0302-st-29-11-planner-toolbar-overflow-priority-regression.md)
- [PR-0303: ST-26-06 public guest overview share/export state wiring](../prs/pr-0303-st-26-06-public-guest-overview-share-export-state-wiring.md)
- [PR-0305: ST-29-11 Smart advanced settings drawer copy and history default](../prs/pr-0305-st-29-11-smart-advanced-settings-drawer-copy-and-history-default.md)
- [PR-0306: ST-29-11 share priority and Smart settings opt-out parity](../prs/pr-0306-st-29-11-share-priority-and-smart-settings-opt-out-parity.md)
- [PR-0307: ST-26-06 share-as-export Smart history provenance](../prs/pr-0307-st-26-06-share-as-export-smart-history-provenance.md)
- [PR-0308: ST-29-11 Smart settings preference continuity and seating-influence default](../prs/pr-0308-st-29-11-smart-settings-preference-continuity-and-seating-influence-default.md)
- [PR-0309: ST-29-11 phone grouping toolbar distribution overflow regression](../prs/pr-0309-st-29-11-phone-grouping-toolbar-distribution-overflow-regression.md)

## Implementation Summary (as of 2026-04-06)

- `PR-0224`, `PR-0225`, `PR-0226`, and `PR-0227` are now implemented as the current
  planner-focused `ST-29-11` hardening set: the desktop shell stays width-stable, toolbar actions
  now respect the shared overflow/priority contract, guest and authenticated grouping/seating
  shells now share the same sticky wrapper/layout contract, the grouping workspace keeps the
  explicit `480px` desktop lane floor with `56px` / `112px` group-card sizing, fresh grouping
  drafts now seed 4 groups in both guest and authenticated mode, grouping autosave preserves the
  overview-selected classroom, and the default 4-card desktop grouping board now proves exact
  `480px` two-row math at `1440x900` while populated cards retain a desktop `234px` minimum-height
  floor and can grow without forced internal scrolling.
- `PR-0228` is now closed as the bounded student-pool/class-list rail follow-up after the latest
  planner shell tightening. The canonical sticky rail contract is still explicitly owned by
  `ST-29-03` and reinforced by `ST-29-05`, while this slice closes the regression-restoration lane
  on the healthier CSS-owned baseline: the main page/workspace scroll is back, the large top panel
  can scroll away, the toolbar becomes the sticky working band, grouping/seating share the same
  `480px` rail pattern, the retained live browser proof stays on the authenticated real-data path,
  and guest/auth parity is carried by the shared shell implementation plus focused guest/auth shell
  specs.
- `PR-0281` is closed as a bounded dense-control processing-feedback follow-up: grouping/seating
  export/share/revoke processing now uses in-place shared spinner affordances, toolbar status pills
  no longer pop into the secondary action row, and browser proof freezes the `Dela` / `Exportera`
  x-position while export is busy.
- `PR-0282` is closed as the public-share disabled/busy-state counterpart after
  `REV-PR-0282` re-review approved the lifecycle remediation. The action enters
  canonical busy state, suppresses duplicate activation, then clears through a
  short browser-handoff guard with restored `href` and cleared busy attributes;
  retained proof covers grouping/seating at desktop and mobile widths.
- `PR-0286` is closed as the next bounded toolbar/distribution-surface follow-up:
  it folds file export choices into the single `Dela` affordance as `Dela och
  exportera`, keeps share and export orchestration as separate state machines,
  and proves the composition in both `Grupper` and `Sittplatser` at phone and
  desktop viewports without changing backend or artifact contracts.
- `PR-0287` is closed as the Smart settings persistence follow-up: grouping and
  seating settings stay open for internal toggles/selects in authenticated and
  guest shells, while explicit close, backdrop, Escape, and intentional Rules
  navigation still close the panel.
- `PR-0301` is done as a bounded overview `Dela och exportera` polish slice:
  it keeps the `PR-0286` share/export consolidation intact, replaces the clunky
  stacked content selector with the product-owner preferred rail toggle, and
  adds selected-draft confirmation for class list and classroom context with
  live proof at phone, laptop, and desktop widths.
- `PR-0302` is amended as a bounded Smart toolbar remediation: grouping/seating
  keep the split Smart toggle/settings control in overflow by default across
  authenticated and public guest workspaces, new drafts default Smart on unless
  the user opts out, and turning Smart off shows the locked Swedish warning
  toast explaining which placement supports are skipped.
- `PR-0303` is done as a cross-linked `ST-26-06` remediation slice for public
  guest overview wiring only: it preserves the existing overview rail and
  dense-control presentation while making public overview share/export actions
  use the selected browser-owned draft and show the browser-owned current link
  rows.
- `PR-0305` is done as the Smart advanced-settings copy/default lock:
  grouping/seating now open `Avancerade inställningar` from the normal overflow
  settings group, the drawer starts with the `Smart placering` master toggle,
  authenticated `Historik` defaults on unless explicitly opted out, public guest
  history remains omitted, and the locked Swedish copy is covered by focused
  component tests plus the retained toolbar parity browser proof.
- `PR-0306` is done as the share-priority and remaining Smart opt-out parity
  follow-up: grouping/seating toolbar tests keep inline `Dela` more important
  than the class/classroom selector, grouping-specific `Tillämpa sittschema`
  initially defaulted on until explicitly turned off, and the grouping
  classroom helper copy now explains the exact room-context versus
  seating-influence behavior. `PR-0308` supersedes that seating-influence
  default while keeping the toolbar/copy work intact.
- `PR-0307` is done as the backend persistence counterpart for the Smart
  history default: authenticated share links now count as export-backed history
  checkpoints, while public guest shares stay outside account-backed history.
- `PR-0308` is done as a remediation to the over-broad `PR-0306` default:
  authenticated Smart settings are profile-owned and cross-browser persisted,
  first-time grouping drafts keep `Tillämpa sittschema` off, and public guest
  drafts remember explicit Smart choices only in browser storage.
- `PR-0309` is done as the phone grouping-toolbar distribution overflow
  remediation: `Dela` now moves into overflow at the iPhone 15 Pro portrait
  proof width so the group-count split control remains reachable, while seating
  keeps its existing phone ladder.

## References

- Epic parent: [EPIC-29](../epics/epic-29-klassrumskartan-desktop-first-workspace-overhaul.md)
- Primitive foundation: [ST-29-01](story-29-01-klassrumskartan-canonical-operation-symbols-and-planner-control-primitives.md)
- Workspace baseline already using the current primitives in practice: [ST-29-05](story-29-05-klassrumskartan-grouping-and-seating-desktop-workspace-overhaul.md)
- Frontend codemap: [REF-frontend-design-system-codemap-2026-03-28](../../reference/ref-frontend-design-system-codemap-2026-03-28.md)
- Shared control matrix: [REF-shared-tool-control-language-v1](../../reference/ref-shared-tool-control-language-v1.md)
