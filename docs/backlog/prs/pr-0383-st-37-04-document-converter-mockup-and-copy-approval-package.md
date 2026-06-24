---
type: pr
id: PR-0383
title: "ST-37-04 Document Converter mockup and copy approval package"
status: blocked
owners: "agents"
created: 2026-06-23
updated: 2026-06-23
stories:
  - "ST-37-04"
tags:
  - planning
  - frontend
  - mockup
  - copy
dependencies:
  - "PR-0380"
  - "PR-0381"
  - "PR-0382"
acceptance_criteria:
  - "Given the user requires a gated UI process, when this package starts, then it begins with image-generated mockups and iterates until the user approves the visual direction."
  - "Given production UI must not be invented directly, when image direction is approved, then a real HTML/CSS mockup is created and iterated until approved before production Vue work."
  - "Given copy must be user-reviewed word by word, when the mockup is approved, then a separate copy sheet is created and no copy is treated as final until explicitly approved."
  - "Given the app should match existing conversion-app conventions, when mockups are produced, then they adapt the current Skriptoteket/Vue design language rather than creating a new product style."
---

# PR-0383: ST-37-04 Document Converter Mockup And Copy Approval Package

## Problem

Document Converter needs a route-visible app, but production UI and copy are
not allowed to be improvised. The product must move through the approved
mockup-first and copy-lock process before implementation.

## Goal

Produce the approved design and copy package for the Document Converter route
after backend contracts have stabilized enough to make the UI truthful.

## Blocked Until

- `PR-0381` proves the local/heavy producer and batch contract.
- `PR-0382` defines the HTML/CSS project and preview contract.
- The user confirms the route-visible scope for the first UI pass.

## Required Pipeline

1. Image-generated mockups.
2. User iteration until image direction is approved.
3. Real HTML/CSS mockup.
4. User iteration until the HTML/CSS mockup is approved.
5. Separate copy sheet using the user's copy-review protocol.
6. Explicit user approval before `PR-0384` implementation.

## Non-goals

- No production Vue route or component changes.
- No backend contract changes.
- No generated API type changes.
- No copy is final until the user approves it.

## Test Plan

- Mockup index/docs validation if mockup docs are created.
- `pdm run docs-validate`
- `pdm run handoff-validate` if handoff changes
- `git diff --check`

## Stop Conditions

- Stop if asked to implement UI before image mockup approval.
- Stop if asked to lock copy before the separate copy sheet is reviewed.
- Stop if the mockup tries to expose unresolved backend decisions as finished
  product behavior.

## Rollback Plan

Archive or remove the mockup package and copy sheet. Keep backend contracts and
previous planning docs unchanged.
