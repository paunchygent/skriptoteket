---
type: task
id: TASK-SKRIPT-27-09-05
title: A pinch in the classroom builder zooms around the fingers
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-29'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: orchestrator
  decided_at: '2026-10-29'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'Junior commit b376ac22b with fail-first pinch spec (CreateRoomTemplateModal.pinch.spec.ts), merged de4c60e93, pre-push 704 files passed, deployed to production de4c60e93 2026-10-29; the user confirmed on their iPhone in Chrome and Safari that a pinch in Skapa klassrum zooms around the fingers. Light route, no review (D2).'
task_kind: story
acceptance_criteria:
  - On a phone, a two-finger pinch on the classroom builder canvas in Skapa klassrum zooms in and out around the point between the fingers, as the Sittplatser seat map does; the builder uses the shared anchored viewport zoom, and a focused spec proves the anchor is kept
story: ST-SKRIPT-27-09
backlog_document_profile: contract-derived
---

## Implementation Contract

On the user's iPhone (Chrome, production `e08981037`, 2026-10-29) a two-finger pinch in the middle of the
classroom builder canvas in Skapa klassrum zooms toward the top-left corner. The Sittplatser seat map zooms
around the pinch point. The builder must behave like the seat map.

- Actor: a teacher creating or editing a classroom template on a phone.
- Cause found in code: `RoomTemplateBuilderSurface.vue:59-65` drops the pinch midpoint in `onZoomByFactor`
  (emit typed factor-only at `:47`) and never starts a gesture camera; `useRoomTemplateEditorState.ts:85-93`
  uses the unanchored `useRoomViewportZoom.zoomByFactor`, which changes scale but not scroll; the surface
  transform origin is `top left` (`:186-187`).
- Change: the builder uses the shared `useAnchoredRoomViewportZoom` (as `PlannerPhoneClassroomSeatMap.vue:101-116`
  does), forwards the pinch anchor from the surface through `CreateRoomTemplateModal.vue:240`, and calls the
  gesture-camera begin and end hooks on gesture start and end.
- Non-goals: the Regler canvas (it has no pinch handler; the browser zooms the page there), button zoom
  behaviour, desktop wheel zoom beyond keeping it working.

## Contract Inputs

- User report 2026-10-29 in the Hemma orchestrator session; REV-SKRIPT-TASK-REP-0024-CLOSEOUT blocker 3.
- `useAnchoredRoomViewportZoom.ts` and its spec; `PlannerPhoneClassroomSeatMap.vue` as the working wiring.

## Core Vertical And Performance

One pinch on the builder: gesture start begins the camera at the midpoint, each zoom step keeps the content
point under the midpoint fixed by adjusting scroll, gesture end flushes the final frame. No new listeners per
frame beyond the existing gesture handlers. One junior unit.

## Validation

- A focused Vitest spec on the builder wiring: a pinch at a given viewport point keeps that content point
  under the same viewport point after zoom (scroll changes with scale).
- Existing `useAnchoredRoomViewportZoom` and builder specs pass.
- The user repeats the pinch on their iPhone after the production deploy.

## Stop Conditions

- The builder cannot use `useAnchoredRoomViewportZoom` without changing its behaviour for the seat map.
- The anchored zoom needs a transform origin other than the one the seat map uses.

## Decided Contract Terms

| ID  | Decided contract term                                                                                             |
| --- | ----------------------------------------------------------------------------------------------------------------- |
| D1  | The builder reuses `useAnchoredRoomViewportZoom` exactly as the seat map does; no second anchored implementation. |
| D2  | Proof is a focused Vitest spec plus the user's iPhone pinch check on production; no review (light route).         |
