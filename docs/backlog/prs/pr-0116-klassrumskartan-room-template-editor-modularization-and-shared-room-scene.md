---
type: pr
id: PR-0116
title: "Klassrumskartan: room-template editor modularization and shared room scene rendering"
status: done
owners: "agents"
created: 2026-03-24
updated: 2026-03-24
stories: []
tags: ["frontend", "refactor", "srp", "room-builder", "export-readiness"]
acceptance_criteria:
  - "`frontend/apps/skriptoteket/src/views/apps/components/CreateRoomTemplateModal.vue` is reduced below 500 LOC via cohesive decomposition into editor-state, builder-surface, and preview/rendering modules."
  - "Room-template editor state and placement rules are extracted into a dedicated composable or domain module rather than being embedded directly in the modal component."
  - "The room-template builder and room preview use shared room-scene rendering primitives so later export/checkpoint rendering does not require a separate duplicate scene implementation."
  - "The current room-builder behavior is preserved: resize controls, ghost preview, wall anchoring, zoom, clear, and CRUD flows still work the same."
  - "Performance-sensitive placement checks are organized around clearer editor-domain helpers instead of repeated ad hoc component-level scans where that simplification materially improves readability and responsiveness."
  - "Focused frontend tests pass for the extracted room-editor logic/components, and a live browser check confirms classroom creation/editing still works on the local SPA."
---

## Problem

`CreateRoomTemplateModal.vue` is currently the largest Klassrumskartan frontend file and mixes too
many concerns in one place:

- editor state
- room geometry state
- tool selection
- seat and fixture placement rules
- hover / ghost placement logic
- viewport zoom logic
- builder rendering
- preview rendering
- submit/delete CRUD handling

That makes the room editor harder to evolve and especially risky ahead of later export/checkpoint
work, where we want to reuse room-scene rendering rather than fork another rendering path.

## Goal

Turn the room-template editor into a reusable, well-bounded frontend module with shared room-scene
rendering primitives that can support later seating export/checkpoint work without duplicating the
classroom scene model.

## Implementation summary

- `frontend/apps/skriptoteket/src/views/apps/components/CreateRoomTemplateModal.vue` is now a
  231-line modal shell that owns only composition plus create/update/delete transport.
- Editor state and placement rules now live in:
  - `frontend/apps/skriptoteket/src/views/apps/useRoomTemplateEditorState.ts`
  - `frontend/apps/skriptoteket/src/views/apps/roomTemplateEditorDomain.ts`
- Builder/presentation UI is split into:
  - `frontend/apps/skriptoteket/src/views/apps/components/RoomTemplateEditorSidebar.vue`
  - `frontend/apps/skriptoteket/src/views/apps/components/RoomTemplateBuilderSurface.vue`
  - `frontend/apps/skriptoteket/src/views/apps/components/RoomTemplatePreviewScene.vue`
- Shared room-scene rendering now flows through
  `frontend/apps/skriptoteket/src/views/apps/components/RoomSceneSurface.vue`, which is reused by
  both the interactive builder and the compact preview.
- Focused frontend coverage now includes:
  - `frontend/apps/skriptoteket/src/views/apps/components/CreateRoomTemplateModal.spec.ts`
  - `frontend/apps/skriptoteket/src/views/apps/useRoomTemplateEditorState.spec.ts`
  - `frontend/apps/skriptoteket/src/views/apps/roomTemplateEditorDomain.spec.ts`
- Live verification is captured in
  `scripts/playwright_pr_0116_room_template_editor_check.py` with artifacts under
  `.artifacts/pr-0116-room-template-check/`.

## Non-goals

- Changing room-builder product behavior or adding new classroom-editing features.
- Changing seating draft semantics or planner-shell route orchestration.
- Shipping export/checkpoint UX in this PR.
- Replacing the existing room layout/presentation helper modules unless the refactor clearly folds
  into them.

## Implementation plan

- Editor-state extraction:
  - introduce a dedicated room-template editor composable or editor-domain module for:
    - grid dimensions
    - selected tool
    - seat placement state
    - fixture placement state
    - hover / ghost state
    - zoom / viewport state
    - validation and error state
  - keep the modal component focused on composition and submit/delete lifecycle only
- UI decomposition:
  - extract tool palette / room-size controls into dedicated components
  - extract builder viewport/canvas into a dedicated component
  - extract preview scene into a dedicated component
- Shared room-scene rendering:
  - introduce shared room-scene primitives where useful so the preview scene and later export
    rendering can rely on the same floor/wall/seat composition rules
  - reuse existing room layout/presentation modules rather than adding a second parallel rendering
    stack
- Editor-domain cleanup:
  - make placement/occupancy logic easier to follow and test in isolation
  - improve internal data shaping where it reduces repeated full-array scanning or repeated
    coordinate normalization logic

## Test plan

- Frontend unit/integration:
  - extracted room-editor state preserves resize, clear, zoom, and tool-selection behavior
  - ghost placement and wall anchoring still behave as before
  - submit payload shape remains unchanged for create and edit flows
  - preview rendering still reflects the same saved seats and fixtures
  - focused tests cover extracted placement helpers and editor composable state transitions
- Live/browser:
  - create a classroom, place seats and fixtures, resize the room, zoom, clear, and save
  - reopen an existing classroom and verify edit/delete still work
  - verify preview and saved classroom rendering still match the edited room layout

## Rollback plan

- Revert to the current monolithic room-template modal implementation while preserving the shipped
  room-builder behavior and current classroom CRUD flows.
