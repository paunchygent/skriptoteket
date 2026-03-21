---
type: pr
id: PR-0080
title: "Klassrumskartan: draft resolve and explicit resume CTA"
status: done
owners: "agents"
created: 2026-03-21
updated: 2026-03-21
stories:
  - "ST-24-01"
tags: ["backend", "frontend", "api", "persistence"]
acceptance_criteria:
  - "The landing page shows an explicit resume affordance when resumable draft work exists, instead of auto-opening the planner."
  - "Starting planning uses a server-owned resolve flow that returns an existing compatible active draft or creates a new one."
  - "Draft resume ordering is based on server-owned lifecycle metadata such as last-opened time."
  - "Backend tests cover resolve/resume semantics and frontend tests cover CTA visibility and click-through behavior."
---

## Problem

The current app still relies on client-local draft restoration mechanics. That undermines the
landing-page-first contract and allows draft lifecycle behavior to drift out of the server's
control.

## Goal

Replace auto-resume with an explicit teacher-facing resume CTA and make draft resolution a proper
server concept, while acknowledging that the later class-first stories will refine the draft key
from a transitional global planner shape into class-scoped draft kinds.

## Non-goals

- Full draft-history browsing.
- Broader mode-specific grouping/seating APIs from later stories.
- Delete blocking for active-draft dependencies; that belongs to PR-0081.

## Checklist

- [x] Introduce server-owned draft lifecycle fields for active/resumable work.
- [x] Add `POST /drafts/resolve` to return an existing compatible active draft or create a new one.
- [x] Add `GET /drafts/resumable` for a landing-page resume CTA.
- [x] Make the landing page show an explicit `Fortsätt senaste utkastet` affordance instead of auto-resuming.
- [x] Make start-planning call `resolve`, not raw draft creation.
- [x] Keep resume limited to one clear teacher-facing CTA for the latest resumable draft, with class/classroom labels.
- [x] Persist and update `last_opened_at` server-side for resume ordering.
- [x] Add backend tests for resolve/resume semantics and frontend tests for CTA rendering and click-through behavior.

## Implementation plan

- Add the minimum draft lifecycle shape needed for ST-24-01:
  - `active` draft state
  - resumable/latest ordering via `last_opened_at`
  - room for later expansion into `abandoned` / `superseded`
- Add bespoke planner endpoints:
  - `POST /api/v1/apps/classroom.group-seating-studio/drafts/resolve`
  - `GET /api/v1/apps/classroom.group-seating-studio/drafts/resumable`
- Update the landing page to fetch resumable draft metadata and render one explicit resume CTA.
- Remove mount-time auto-open behavior from the current `sessionStorage` restore flow; session
  storage may remain as a compatibility hint internally if needed, but it must not control the
  visible workflow.

## Test plan

- Backend:
  - resolve returns an existing compatible active draft
  - resolve creates a new draft when no compatible active draft exists
  - resumable endpoint returns the latest resumable draft for the teacher
- Frontend:
  - resume CTA appears only when resumable draft exists
  - clicking the CTA opens the planner explicitly
  - no mount-time planner hijack on reload
- Manual:
  - create/open a draft, return to the landing page, reload the app, and verify the CTA appears
    instead of dropping directly into the planner

## Rollback plan

- Revert the new endpoints and restore the previous direct-create flow if resolve introduces
  unstable draft selection behavior; keep the landing-page-first UI contract in place.

## Follow-up direction

- This PR established the server-owned resume/resolve foundation.
- `ST-24-02` and ADR-0072 refine the long-term invariant to one active draft per class per draft
  kind, rather than treating the current transitional behavior as the final lifecycle contract.
