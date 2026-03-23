---
type: pr
id: PR-0110
title: "Klassrumskartan: overview compact class and classroom management"
status: in_progress
owners: "agents"
created: 2026-03-23
updated: 2026-03-23
stories:
  - "ST-24-07"
tags: ["frontend", "ux", "integration"]
acceptance_criteria:
  - "The overview surface expands from a sparse placeholder into a compact desktop-first dashboard for class and classroom management."
  - "The overview exposes the active class, class preview, class edit flow, class creation, class delete, and class switching without long expanded management lists."
  - "The overview exposes the active classroom, compact classroom preview, classroom switching, classroom edit, classroom creation, and classroom delete as explicit actions."
  - "Delete remains an explicit adjacent action rather than being embedded inside the selectors, and class/classroom delete share the same planner-native confirmation treatment."
  - "The class and classroom cards stay visually balanced through fixed preview areas, with useful count indicators next to the selected class/classroom names rather than decorative metadata cards."
  - "Grouping remains classroom-agnostic by default even though overview now shows a current classroom."
  - "Class switching is defined only from a neutral overview state: it waits for any in-flight workspace transition to finish and leaves previously active drafts resumable rather than silently discarding them."
---

## Problem

The current overview is too thin to replace the landing-page management surface. Class and
classroom management are still not compactly centralized where the teacher actually works.

## Goal

Make `Översikt` the compact desktop-first dashboard for the common teacher setup tasks before any
landing-page cutover happens.

## Non-goals

- Removing the separate landing page.
- Final `Avsluta` cutover behavior.
- Smart grouping or seating placement rules.
- Long mobile-first management layouts.

## Implementation plan

- Overview surface:
  - evolve the current class card into a compact multi-panel dashboard
  - add balanced class/classroom panels with fixed preview surfaces, compact selectors, and explicit actions
- Workspace orchestration:
  - reuse the current class/classroom modal flows and catalog data where possible
  - keep grouping entry classroom-agnostic by default
  - define class switching as an overview-only action that cannot strand active draft state
- Verification:
  - focused component and integration tests for overview management

## Test plan

- Frontend unit/integration:
  - overview renders both compact management panels
  - class/classroom selector and edit/create/delete actions wire correctly
  - class preview stays compact in three columns with ellipsis when all names do not fit
  - grouping entry remains classroom-agnostic by default
  - class switching remains blocked or deferred until the workspace is back in a neutral overview state
  - leaving one class keeps its active drafts resumable rather than discarding them
- Live/browser:
  - select class and classroom from overview
  - preview/edit/delete classroom
  - switch class after returning from active work and confirm the earlier class still exposes resumable work
  - confirm the compact desktop-first flow remains easy to scan

## Rollback plan

- Revert the overview-management expansion while keeping the already shipped class-first workspace
  and seating/grouping task surfaces intact.
