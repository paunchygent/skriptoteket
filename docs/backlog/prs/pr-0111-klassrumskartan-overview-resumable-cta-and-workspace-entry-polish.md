---
type: pr
id: PR-0111
title: "Klassrumskartan: overview resumable CTA and workspace-entry polish"
status: in_progress
owners: "agents"
created: 2026-03-23
updated: 2026-03-24
stories:
  - "ST-24-07"
tags: ["frontend", "ux", "integration"]
acceptance_criteria:
  - "The overview top area exposes compact resumable continuation surfaces for grouping and seating so the class workspace can replace the superseded landing-page CTA."
  - "The resumable continuation surfaces are not just copied from landing; they are improved with a smaller footprint, cleaner layout, a dismiss `×`, and explicit continue/settings affordances."
  - "The overview keeps a compact desktop-first layout while making workspace entry feel immediate through the existing top toggle rather than through a launcher-heavy duplicate home model."
  - "Targeted browser proof proves the compact resumable overview entry flow on the current SPA and verifies that the landing-page CTA can be removed immediately after the replacement works."
---

## Problem

Even after overview gains class/classroom management, the resumable entry flow is still anchored in
the old landing surface. A long-lived duplicate CTA phase would keep two different home models
alive, add avoidable state-sharing complexity, and preserve a surface the product no longer wants.

## Goal

Build the improved resumable overview/home surface that can immediately replace the landing-page CTA
once it works, so the old landing surface can start being deleted rather than preserved.

## Non-goals

- Preserving a long transition period where both landing and overview own resumable entry.
- Final exit-to-origin behavior.
- Introducing compatibility shims, mirrored CTA state, or shared cross-surface dismiss logic that
  only exist to keep the old landing page alive longer.

## Implementation plan

- Overview home surface:
  - add compact resumable continuation cards/surfaces for grouping and seating
  - make the continuation surfaces smaller and less bulky than the legacy CTA treatment
  - include explicit continue affordances, settings entry points, and a dismiss `×` in the new
    overview-owned surface
- Workspace entry:
  - preserve the existing top toggle as the only mode switch
  - keep the teacher inside one compact main page instead of bouncing through a separate landing
    launcher
  - tighten the top-level `Avsluta` affordance so it reads as a compact leave-the-app action rather
    than as a bulky secondary panel action
- Cutover readiness:
  - do not build durable state-sharing between landing and overview
  - once the overview-owned resumable surface works, the old landing CTA path should be ready for
    immediate removal by the tandem `ST-24-08` cutover
- Verification:
  - add targeted browser proof for the improved resumable overview entry flow and the now-cutover-
    ready main page behavior

## Test plan

- Frontend unit/integration:
  - overview renders the improved resumable continuation surface when resumable work exists
  - dismiss `×` works on the compact resumable surface
  - toggle-based entry from overview remains intact
- Live/browser:
  - verify the improved resumable surface on overview/main page
  - continue a grouping draft and a seating draft from the new surface
  - verify the compact settings affordance and dismiss affordance behave correctly
  - verify the app is ready to stop relying on the old landing CTA immediately after this slice

## Rollback plan

- Revert the improved resumable overview/home surface while keeping the compact overview management
  work from `PR-0110`.
