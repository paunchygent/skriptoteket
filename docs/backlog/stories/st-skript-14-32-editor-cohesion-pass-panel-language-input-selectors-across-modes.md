---
type: story
id: ST-SKRIPT-14-32
title: 'Editor: cohesion pass (panel language + input selectors across modes)'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-14
acceptance_criteria:
- Given the author switches between Källkod/Diff/Metadata/Testkör, then typography,
  spacing, borders, and button sizes stay consistent (IDE-like, no drawer-style headers
  inside the editor surface).
- Given the editor shows input selectors (preset/entrypoint/diff target), then they
  share one compact size system (height, font, padding) and one tooltip/help pattern
  without label collisions.
- Given the author interacts with Testkör mode, then in-editor actions (file picker,
  run, clear) use the same editor utility hierarchy (no large CTA-style buttons inside
  the editor).
- Given the author uses Metadata mode, then the panel uses the same compact section
  headers and actions as the main editor (no redundant intro copy).
- Given the author uses Diff mode, then diff controls use the same utility button
  + select styling as the rest of the editor.
retired_ids:
- ST-14-32
---

## Context

### Source: Context

The editor shell is now stable (fixed-height, mode toggles, chat column), but non-source modes still look and feel like
embedded drawers/pages. This story aligns **all editor modes** to a single compact "editor panel language" so the editor
reads as one coherent IDE surface.

## Epic Contract Slice

The source does not provide a separate epic contract slice section; no additional epic contract slice is recorded.

## ADR Coverage

The source does not provide a separate adr coverage section; no additional adr coverage is recorded.

## Contract Inputs

The source does not provide a separate contract inputs section; no additional contract inputs is recorded.

## Live Verification Plan

The source does not provide a separate live verification plan section; no additional live verification plan is recorded.

## Non-Goals

The source does not provide a separate non-goals section; no additional non-goals is recorded.

## Notes

### Source: Notes

- This is a **design cohesion** pass; avoid changing behavior/contracts unless required for consistency or accessibility.
- Prioritize small, reusable primitives over one-off styling.

## Decision And Assumption Ledger

The source does not provide a separate decision and assumption ledger section; no additional decision and assumption ledger is recorded.

## Plan Document Review

The source does not provide a separate plan document review section; no additional plan document review is recorded.

## Story Closeout Review

The source does not provide a separate story closeout review section; no additional story closeout review is recorded.
