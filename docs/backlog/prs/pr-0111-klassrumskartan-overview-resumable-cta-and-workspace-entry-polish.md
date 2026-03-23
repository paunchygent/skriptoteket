---
type: pr
id: PR-0111
title: "Klassrumskartan: overview resumable CTA and workspace-entry polish"
status: ready
owners: "agents"
created: 2026-03-23
updated: 2026-03-23
stories:
  - "ST-24-07"
tags: ["frontend", "ux", "integration"]
acceptance_criteria:
  - "The overview top area exposes a resumable CTA that duplicates the current landing-page continuation affordance during transition."
  - "The overview keeps a compact desktop-first layout while making class switching and workspace entry feel immediate."
  - "Teachers can continue from the overview directly into `Grupper` or `Sittplatser` through the existing top toggle without reintroducing a launcher-heavy surface."
  - "Targeted browser proof proves the duplicated resumable CTA and compact overview-first workspace-entry flow while the separate landing page still exists."
---

## Problem

Even after overview gains class/classroom management, the landing page still owns too much of the
"continue where I left off" entry flow. That prevents the overview replacement from being proven in
real use before the final cutover.

## Goal

Duplicate the resumable CTA into the overview and tighten compact workspace-entry behavior so the
overview can serve as the fully capable replacement surface ahead of the final landing removal.

## Non-goals

- Removing the landing page.
- Final exit-to-origin behavior.
- Introducing compatibility shims that survive the later big-bang cutover.

## Implementation plan

- Overview top area:
  - add the resumable CTA in a compact banner treatment
  - keep the existing landing CTA temporarily duplicated
- Workspace entry:
  - tighten class switching and task-entry affordances without adding clutter
  - preserve the existing top toggle as the only mode switch
- Verification:
  - add targeted browser proof for the duplicated CTA and overview-first entry flow

## Test plan

- Frontend unit/integration:
  - overview resumable CTA renders when resumable work exists
  - toggle-based entry from overview remains intact
- Live/browser:
  - verify landing and overview both show the continuation affordance during transition
  - continue a resumable draft from overview
  - switch into `Grupper` and `Sittplatser` via the existing toggle

## Rollback plan

- Revert the duplicated overview CTA and entry polish while keeping the compact overview management
  work from `PR-0110`.
