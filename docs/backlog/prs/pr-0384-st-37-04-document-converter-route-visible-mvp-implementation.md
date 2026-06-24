---
type: pr
id: PR-0384
title: "ST-37-04 Document Converter route-visible MVP implementation"
status: blocked
owners: "agents"
created: 2026-06-23
updated: 2026-06-23
stories:
  - "ST-37-04"
tags:
  - frontend
  - document-converter
  - route-visible
dependencies:
  - "PR-0381"
  - "PR-0382"
  - "PR-0383"
acceptance_criteria:
  - "Given the approved backend contracts and mockups exist, when this slice closes, then `/apps/document-converter` is a truthful authenticated route that consumes Skriptoteket-owned Document Converter APIs."
  - "Given the authenticated home card currently remains inert, when the route ships, then the Document Converter card links to the new route without adding duplicate app links to persistent navigation."
  - "Given teachers need visible conversion state, when a job or preview runs, then the UI shows progress, result readiness, failure recovery, and allowed save/download actions through Skriptoteket endpoints."
  - "Given copy is locked separately, when implementation lands, then production text matches the approved copy sheet and no unreviewed labels are introduced."
---

# PR-0384: ST-37-04 Document Converter Route-Visible MVP Implementation

## Problem

Document Converter is visible as an approved product lane but still has no
truthful route. It must not be activated until the backend contracts, preview
contract, mockups, and copy lock are approved.

## Goal

Implement the first route-visible authenticated Document Converter app using
the approved mockup, approved copy, and scoped backend contracts.

## Blocked Until

- `PR-0381` and `PR-0382` are implemented and reviewed.
- `PR-0383` has approved image mockups, HTML/CSS mockup, and copy lock.
- The user confirms that the first route-visible scope is ready for production.

## Non-goals

- No public anonymous Document Converter lane.
- No sidebar app-link duplication.
- No generic Conversion Hub teacher-facing label resurrection.
- No unapproved copy.
- No broad registry/API app-presentation split unless `PR-0369` is explicitly
  activated by a concrete contract need.

## Red-First Proof Plan

- Frontend red: authenticated home card is inert and `/apps/document-converter`
  has no runnable app route.
- Frontend red: selected approved workflow cannot be completed against the
  current UI.
- Contract red: UI cannot yet consume the required progress/result/preview
  shape.

## Green Proof Plan

- Focused Vitest coverage for route guard, home-card activation, batch/source
  selection, progress, preview/result state, download/save actions, retry or
  discard paths, and failure states.
- `pdm run fe-type-check`
- `pdm run fe-lint`
- Relevant focused backend tests if API integration changes.
- Live shared-auth Docker browser proof through the HuleEdu browser-session
  ceremony.
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Stop Conditions

- Stop if production UI deviates from approved mockup or copy.
- Stop if the route would call Sir Convert directly from the browser.
- Stop if small-screen behavior cannot be proven.
- Stop if implementation needs app registry/bootstrap contract changes not
  approved by a concrete `PR-0369` activation.

## Rollback Plan

Remove the route, home-card link activation, route tests, generated type usage,
and docs/handoff updates. Leave backend contracts available but route-inactive.
