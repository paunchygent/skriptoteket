---
type: story
id: ST-32-01
title: "Curated-app public access profiles and current app matrix"
status: done
owners: "agents"
created: 2026-04-03
updated: 2026-04-30
epic: "EPIC-32"
dependencies: ["ADR-0023", "ADR-0079"]
acceptance_criteria:
  - "Given Skriptoteket's current curated app registry, when public access planning is recorded, then each current curated app is classified into an explicit `current_access_profile` with a short rationale."
  - "Given a curated app has `min_role=user`, when its public posture is reviewed, then the plan explicitly states that authenticated role authorization does not by itself imply guest/public entry."
  - "Given a future curated app is added without an explicit public classification, when planning or implementation begins, then the default posture remains `authenticated_only`."
  - "Given the current app set is reviewed, when the matrix is finalized, then Klassrumskartan, Flunk-Out Frenzy, Reagent Prep Chef, Conversion Hub, and `demo.counter` all have an explicit `current_access_profile`, and any future intent is recorded separately as optional `future_target_profile` guidance."
  - "Given router, bootstrap, and API decisions must fail closed, when the source of truth is defined, then the curated-app definition/registry is the canonical owner of the public-access profile consumed by those seams."
ui_impact: "No direct UI change; establishes the planning contract that later public-entry work depends on."
data_impact: "Yes (registry/definition metadata becomes the canonical public-access-profile source of truth)."
---

## Context

Skriptoteket already has several curated apps, but they do not share the same
public-readiness shape. Treating “open access to curated apps” as one blanket
switch would mix teacher workspace privacy, anonymous compute abuse, browser
runtime state, and dev/demo surfaces into one vague category.

## Notes

- The matrix must be a first-class planning artifact, not tribal knowledge.
- Recommended initial classification:
  - `classroom.group-seating-studio`
    - `current_access_profile`: `public_browser_workspace_with_upgrade`
  - `games.flunk_out_frenzy`
    - `current_access_profile`: `authenticated_only`
    - `future_target_profile`: `public_browser_runtime`
  - `chemistry.reagent_prep_chef`
    - `current_access_profile`: `authenticated_only`
    - `future_target_profile`: `public_stateless`
  - `documents.conversion_hub`
    - `current_access_profile`: `authenticated_only`
  - `demo.counter`
    - `current_access_profile`: `authenticated_only`
    - operational note: dev/demo-only, not part of the production public-access rollout
- This story is deliberately platform-level. It exists so later app work can
  reuse one vocabulary rather than reopening the access model every time.

## Status Reconciliation (2026-04-30)

This story is now marked `done`. `ADR-0079` is accepted, `REV-EPIC-32`
approved the access-profile matrix, and the implemented curated-app public
bootstrap returns `public_access_profile` from the public app contract used by
the SPA host.
