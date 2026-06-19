---
type: pr
id: PR-0361
title: "ST-37-03 service shell UX realignment planning package"
status: done
owners: "agents"
created: 2026-06-17
updated: 2026-06-18
stories:
  - "ST-37-03"
tags:
  - docs
  - frontend
  - ux
dependencies:
  - "PR-0358"
  - "PR-0359"
  - "PR-0360"
  - "REF-current-product-lanes-and-sir-convert-boundary-v1"
  - "REF-service-shell-ux-realignment-plan-v1"
acceptance_criteria:
  - "Given stale backlog state has been repaired, when this planning package closes, then the main service shell/dashboard redesign has a PR-sized implementation sequence grounded in current app lanes."
  - "Given the dashboard must become more service-aligned, when implementation tasks are created, then vanity-card and generic catalog assumptions are explicitly out of scope."
  - "Given future UI changes affect protected routes, when implementation tasks are created, then each route-visible slice names focused Vitest coverage and live browser proof through the HuleEdu browser-session ceremony."
---

# PR-0361: ST-37-03 Service Shell UX Realignment Planning Package

## Problem

The shell/dashboard redesign should happen after backlog cleanup and current
product-lane framing, otherwise it risks encoding stale app structure.

## Goal

Create the implementation-ready service-shell redesign plan and PR sequence.

## Non-goals

- No shell/dashboard implementation in this planning package.
- No route renames before app-presentation decomposition is reviewed.

## Implementation plan

1. Read the cleaned backlog state from `ST-37-01`.
2. Read the current product-lane reference from `ST-37-02`:
   [REF-current-product-lanes-and-sir-convert-boundary-v1](../../reference/ref-current-product-lanes-and-sir-convert-boundary-v1.md).
3. Reconcile existing UI epic/story direction with the desired main service
   shell.
4. Create or update PR-sized implementation slices for the dashboard redesign,
   with exact frontend test and browser-proof gates.

## Implementation Summary

Completed on 2026-06-18. The durable planning output is
[REF-service-shell-ux-realignment-plan-v1](../../reference/ref-service-shell-ux-realignment-plan-v1.md).
It records current code reality, closed decisions, options, assumptions,
recommendations, stop conditions, and the route-visible proof gates for the
future service-shell implementation sequence.

This slice created the follow-up implementation PR tasks:

- [PR-0363](pr-0363-st-37-03-conversion-lane-mode-deep-link-contract.md):
  current `documents.conversion_hub` query-mode deep links for Exam Converter
  and Audio Transcription.
- [PR-0364](pr-0364-st-37-03-authenticated-home-work-apps-surface.md):
  signed-in home product-lane surface.
- [PR-0365](pr-0365-st-37-03-authenticated-shell-navigation-realignment.md):
  authenticated shell navigation realignment.

No frontend, route, registry, API, Sir Convert, HuleEdu, QTI, or DOCX code was
changed. `ST-37-03` remains open for implementation. `PR-0362` / `ST-37-04`
is now unblocked because the service-shell planning package is closed. The
implementation PRs above remain blocked until `PR-0362` closes and their own
review gates are approved.

## Test plan

- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Verification

- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Rollback plan

Revert the planning package if review decides the shell redesign belongs under a
different epic or needs a different product-lane order.
