---
type: story
id: ST-37-03
title: "Service shell and dashboard UX realignment"
status: ready
owners: "agents"
created: 2026-06-17
updated: 2026-06-19
epic: "EPIC-37"
dependencies:
  - "ST-37-01"
  - "ST-37-02"
  - "REF-current-product-lanes-and-sir-convert-boundary-v1"
  - "REF-service-shell-ux-realignment-plan-v1"
  - "EPIC-29"
acceptance_criteria:
  - "Given stale backlog signals have been repaired, when the main service shell/dashboard is redesigned, then it centers teacher productivity applications instead of vanity cards, generic catalog framing, or outdated script-first messaging."
  - "Given the app lanes are named and bounded, when the shell renders, then it presents clear entrypoints for the current application families with dense, work-oriented navigation and no duplicate explanatory chrome."
  - "Given UI or route behavior changes, when implementation begins, then the slice includes focused frontend tests plus live browser proof through the sanctioned auth ceremony for protected paths."
ui_impact: "Yes (main dashboard/service shell and app entry hierarchy)."
---

# ST-37-03: Service Shell And Dashboard UX Realignment

## Context

The current dashboard direction predates the stable transcript app and the
sharper app-lane split. The next UI pass should resume the recent service-shell
redesign direction after backlog truth is repaired and after product-lane naming
is explicit.

## Planned PR Slices

- [x] [PR-0361: ST-37-03 service shell UX realignment planning package](../prs/pr-0361-st-37-03-service-shell-ux-realignment-planning-package.md)
- [x] [PR-0363: ST-37-03 conversion lane mode deep-link contract](../prs/pr-0363-st-37-03-conversion-lane-mode-deep-link-contract.md)
- [ ] [PR-0364: ST-37-03 authenticated home work-apps surface](../prs/pr-0364-st-37-03-authenticated-home-work-apps-surface.md)
- [ ] [PR-0365: ST-37-03 authenticated shell navigation realignment](../prs/pr-0365-st-37-03-authenticated-shell-navigation-realignment.md)

## Notes

- `PR-0361` is complete. The implementation sequence and scope-closure ledger
  now live in
  [REF-service-shell-ux-realignment-plan-v1](../../reference/ref-service-shell-ux-realignment-plan-v1.md).
  `ST-37-03` remains open because the route-visible shell implementation slices
  have not yet run.
- `PR-0363` is complete and approved by
  [REV-PR-0363](../reviews/review-pr-0363-conversion-lane-mode-deep-link-contract.md).
  It added the authenticated compatibility-host
  `/apps/documents.conversion_hub?mode=exam|transcript` bridge and retained
  Docker-backed HuleEdu browser-session proof. `PR-0364` and `PR-0365` remain
  the open ST-37-03 implementation slices.
- `PR-0364` is ready for independent review via
  [REV-PR-0364](../reviews/review-pr-0364-authenticated-home-work-apps-surface.md)
  after approval of the
  [C2 authenticated home mockup](../../mockups/pr-0364-authenticated-home-work-apps-surface/README.md).
  It should make authenticated `/` app-first, treat `Kodredigerare` as a
  primary app, remove `Mina körningar`/latest-used/recent-used home chrome,
  keep `Mina körningar` out of persistent shell navigation, and avoid nested
  card layouts. The deleted card-grid and service-foyer mockup attempts from
  2026-06-19 must not guide implementation.
- Implementation must use the integrated frontend stack guidance: CSS-owned
  geometry, dense workspace doctrine where applicable, focused Vitest coverage,
  and live browser proof for route-visible changes.
