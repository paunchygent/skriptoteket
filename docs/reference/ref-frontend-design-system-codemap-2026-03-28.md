---
type: reference
id: REF-frontend-design-system-codemap-2026-03-28
title: "Frontend design-system codemap (SPA, planner, editor)"
status: active
owners: "agents"
created: 2026-03-28
updated: 2026-03-28
topic: "frontend design system"
links:
  - "ADR-0017"
  - "ADR-0027"
  - "ADR-0029"
  - "ADR-0030"
  - "ADR-0032"
  - "ADR-0037"
  - "ST-29-01"
  - "REF-shared-tool-control-language-v1"
  - "REF-klassrumskartan-workspace-ui-doctrine-2026-03-28"
  - "REF-tool-editor-framework-codemap"
---

## Purpose

This codemap is the canonical reading guide to Skriptoteket’s frontend design system as it exists
today in the Vue/Vite SPA.

Use it when you need to answer one of these questions:

- Where do the design-system rules actually live?
- Where do tokens become CSS and Tailwind utilities?
- Where do shared primitives exist today?
- Which files are the real proving grounds for dense tool UX?
- What should a frontend designer read before changing planner or editor controls?

## Current structural truth

- The frontend is a pnpm workspace rooted at `frontend/`.
- The only live app package today is `frontend/apps/skriptoteket/`.
- `frontend/packages/` exists, but there is no shipped shared UI package there yet.
- That means the current design system is real, but it is distributed across:
  - docs and rules
  - token CSS in backend-served static assets
  - shared UI components inside the SPA app
  - planner/editor proving-ground surfaces

## Reading order

1. Governance and doctrine
2. Workspace and build entrypoints
3. Token pipeline
4. Shared primitives and icons
5. Dense tool examples in the editor
6. Dense workspace examples in Klassrumskartan
7. Tests and verification harnesses

## Live proving routes

- Planner: `http://127.0.0.1:5173/apps/classroom.group-seating-studio`
- Editor hub: `http://127.0.0.1:5173/editor?pick=1`
- Tool editor: `http://127.0.0.1:5173/admin/tools/:toolId`

## Layer map

```text
Docs + rules
  -> token source
     -> theme bridge
        -> shared SPA primitives
           -> dense tool compositions
              -> planner and editor surfaces
                 -> tests + live verification
```

## Governing docs and rules

These are the first files a designer or frontend implementer should read.

- `docs/prd/prd-spa-frontend-v0.1.md`
- `docs/prd/prd-tool-authoring-v0.1.md`
- `docs/prd/prd-group-seating-studio-v0.3.md`
- `docs/adr/adr-0017-huleedu-design-system-adoption.md`
- `docs/adr/adr-0027-full-vue-vite-spa.md`
- `docs/adr/adr-0029-frontend-styling-pure-css-design-tokens.md`
- `docs/adr/adr-0030-openapi-as-source-and-openapi-typescript.md`
- `docs/adr/adr-0032-tailwind-4-theme-tokens.md`
- `docs/adr/adr-0037-toast-and-system-messages-spa.md`
- `docs/reference/ref-shared-tool-control-language-v1.md`
- `docs/reference/ref-klassrumskartan-workspace-ui-doctrine-2026-03-28.md`
- `docs/reference/ref-tool-editor-framework-codemap.md`
- `.agents/rules/045-huleedu-design-system.md`

## Workspace, build, and app entrypoints

These files define what the frontend is and how it boots.

- `frontend/package.json`
- `frontend/pnpm-workspace.yaml`
- `frontend/apps/skriptoteket/package.json`
- `frontend/apps/skriptoteket/vite.config.ts`
- `frontend/apps/skriptoteket/vitest.config.ts`
- `frontend/apps/skriptoteket/src/main.ts`
- `frontend/apps/skriptoteket/src/App.vue`
- `frontend/apps/skriptoteket/src/router/index.ts`
- `frontend/apps/skriptoteket/src/router/routes.ts`
- `frontend/apps/skriptoteket/src/api/openapi.d.ts`
- `frontend/apps/skriptoteket/src/test/setup.ts`

## Token pipeline

This is the real styling contract path.

- Canonical token source:
  - `src/skriptoteket/web/static/css/huleedu-design-tokens.css`
- SPA token import wrapper:
  - `frontend/apps/skriptoteket/src/styles/tokens.css`
- Tailwind theme bridge:
  - `frontend/apps/skriptoteket/src/styles/tailwind-theme.css`
- SPA CSS entrypoint and primitive classes:
  - `frontend/apps/skriptoteket/src/assets/main.css`

## Shared primitive and asset surfaces

These files are the current shared design-system implementation layer inside the SPA.

### Icons

- `frontend/apps/skriptoteket/src/components/icons/index.ts`
- `frontend/apps/skriptoteket/src/components/icons/IconUndo.vue`
- `frontend/apps/skriptoteket/src/components/icons/IconRedo.vue`
- `frontend/apps/skriptoteket/src/components/icons/IconHistory.vue`
- `frontend/apps/skriptoteket/src/components/icons/IconSettings.vue`
- `frontend/apps/skriptoteket/src/components/icons/IconDownload.vue`
- `frontend/apps/skriptoteket/src/components/icons/IconShuffle.vue`
- `frontend/apps/skriptoteket/src/components/icons/IconMoreVertical.vue`
- `frontend/apps/skriptoteket/src/components/icons/IconArrow.vue`
- `frontend/apps/skriptoteket/src/components/icons/IconX.vue`
- `frontend/apps/skriptoteket/src/components/icons/IconTrash.vue`
- `frontend/apps/skriptoteket/src/components/icons/IconCheck.vue`
- `frontend/apps/skriptoteket/src/components/icons/IconWarning.vue`
- `frontend/apps/skriptoteket/src/components/icons/IconInfo.vue`
- `frontend/apps/skriptoteket/src/components/icons/IconBan.vue`
- `frontend/apps/skriptoteket/src/components/icons/IconLink2.vue`
- `frontend/apps/skriptoteket/src/components/icons/IconSearch.vue`
- `frontend/apps/skriptoteket/src/components/icons/IconBookmark.vue`
- `frontend/apps/skriptoteket/src/components/icons/IconPresentation.vue`
- `frontend/apps/skriptoteket/src/components/icons/IconSchool.vue`

### Generic UI primitives

- `frontend/apps/skriptoteket/src/components/ui/SystemMessage.vue`
- `frontend/apps/skriptoteket/src/components/ui/ToastHost.vue`
- `frontend/apps/skriptoteket/src/components/ui/ToggleSwitch.vue`
- `frontend/apps/skriptoteket/src/components/ui/UiCollapse.vue`
- `frontend/apps/skriptoteket/src/components/ui/UiMarkdown.vue`
- `frontend/apps/skriptoteket/src/components/ui/UiSearchBar.vue`
- `frontend/apps/skriptoteket/src/components/ui/UiSegmentedToggle.vue`

### Typed action/output renderers

- `frontend/apps/skriptoteket/src/components/ui-actions/index.ts`
- `frontend/apps/skriptoteket/src/components/ui-actions/UiActionForm.vue`
- `frontend/apps/skriptoteket/src/components/ui-actions/UiActionFieldRenderer.vue`
- `frontend/apps/skriptoteket/src/components/ui-outputs/index.ts`
- `frontend/apps/skriptoteket/src/components/ui-outputs/UiOutputRenderer.vue`

## Dense tool reference surface: the code editor

These files show how the current product handles command surfaces, drawers, editing panes, compare
views, and assistant surfaces.

### Route and page entry

- `frontend/apps/skriptoteket/src/views/editor/EditorHubView.vue`
- `frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue`

### Shared editor shell and command surfaces

- `frontend/apps/skriptoteket/src/components/editor/ScriptEditorPageShell.vue`
- `frontend/apps/skriptoteket/src/components/editor/ScriptEditorHeaderPanel.vue`
- `frontend/apps/skriptoteket/src/components/editor/EditorWorkspacePanel.vue`
- `frontend/apps/skriptoteket/src/components/editor/EditorWorkspaceToolbar.vue`
- `frontend/apps/skriptoteket/src/components/editor/EditorWorkspaceModeSelector.vue`
- `frontend/apps/skriptoteket/src/components/editor/EditorToolMenu.vue`
- `frontend/apps/skriptoteket/src/components/editor/WorkflowActionsDropdown.vue`
- `frontend/apps/skriptoteket/src/components/editor/WorkflowContextButtons.vue`

### Core content surfaces

- `frontend/apps/skriptoteket/src/components/editor/EditorSourceCodePanel.vue`
- `frontend/apps/skriptoteket/src/components/editor/EditorInputSchemaPanel.vue`
- `frontend/apps/skriptoteket/src/components/editor/EditorSettingsSchemaPanel.vue`
- `frontend/apps/skriptoteket/src/components/editor/EditorSandboxPanel.vue`
- `frontend/apps/skriptoteket/src/components/editor/EditorComparePanel.vue`
- `frontend/apps/skriptoteket/src/components/editor/CodeMirrorEditor.vue`

### Drawer and secondary surfaces

- `frontend/apps/skriptoteket/src/components/editor/VersionHistoryDrawer.vue`
- `frontend/apps/skriptoteket/src/components/editor/MetadataDrawer.vue`
- `frontend/apps/skriptoteket/src/components/editor/InstructionsDrawer.vue`
- `frontend/apps/skriptoteket/src/components/editor/MaintainersDrawer.vue`
- `frontend/apps/skriptoteket/src/components/editor/ChatDrawer.vue`
- `frontend/apps/skriptoteket/src/components/editor/ScriptEditorAiPanel.vue`

### Diff and review surfaces

- `frontend/apps/skriptoteket/src/components/editor/diff/VirtualFileDiffViewer.vue`
- `frontend/apps/skriptoteket/src/components/editor/diff/AiVirtualFileDiffViewer.vue`
- `frontend/apps/skriptoteket/src/components/editor/diff/CodeMirrorMergeDiff.vue`

### Editor state and orchestration

- `frontend/apps/skriptoteket/src/composables/editor/useScriptEditor.ts`
- `frontend/apps/skriptoteket/src/composables/editor/useScriptEditorPageState.ts`
- `frontend/apps/skriptoteket/src/composables/editor/useScriptEditorDrawers.ts`
- `frontend/apps/skriptoteket/src/composables/editor/useDraftLock.ts`
- `frontend/apps/skriptoteket/src/composables/editor/useEditorCompareData.ts`
- `frontend/apps/skriptoteket/src/composables/editor/useEditorCompareState.ts`
- `frontend/apps/skriptoteket/src/composables/editor/useEditorSandboxActions.ts`
- `frontend/apps/skriptoteket/src/composables/editor/useEditorWorkflowActions.ts`
- `frontend/apps/skriptoteket/src/composables/editor/useEditorChat.ts`

## Dense workspace reference surface: Klassrumskartan

These files are the current proving ground for desktop-first multi-workspace design.

### Route and orchestration

- `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerView.vue`
- `frontend/apps/skriptoteket/src/views/apps/useClassroomPlannerRouteShell.ts`
- `frontend/apps/skriptoteket/src/views/apps/useClassroomState.ts`
- `frontend/apps/skriptoteket/src/views/apps/useSmartRuleUiState.ts`
- `frontend/apps/skriptoteket/src/views/apps/useRosterSmartRuleLane.ts`
- `frontend/apps/skriptoteket/src/views/apps/useRoomViewportZoom.ts`
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerNavigation.ts`
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerOverviewStore.ts`
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerExportFlow.ts`

### Shared planner shell and control surfaces

- `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceActionBar.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerTopPanel.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerToolbarIconButton.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerToolbarOverflowMenu.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerExportActionGroup.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerHistoryDrawer.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerMetadataDrawer.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerConfirmationDialog.vue`

### Overview mode

- `frontend/apps/skriptoteket/src/views/apps/components/PlannerOverviewResumeCards.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerRosterOverviewPanel.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerTemplateOverviewPanel.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerClassWorkspace.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/CreateRosterModal.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/CreateRoomTemplateModal.vue`

### Grouping mode

- `frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspacePane.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/GroupBoard.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/GroupCard.vue`

### Seating mode

- `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspacePane.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerStudentPool.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerSmartRulesSummaryStrip.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/RoomCanvas.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/RoomSceneSurface.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/RoomSeatToken.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/SeatNode.vue`

### Rules mode

- `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesWorkspacePane.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesToolRail.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesMapPanel.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesMapCanvas.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesSeatNode.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesInspector.vue`

### Room/classroom editor surfaces

- `frontend/apps/skriptoteket/src/views/apps/useRoomTemplateEditorState.ts`
- `frontend/apps/skriptoteket/src/views/apps/components/RoomTemplateBuilderSurface.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/RoomTemplateEditorSidebar.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/RoomTemplatePreviewScene.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/RoomFixtureArtwork.vue`

## Tests that expose design-system behavior

- `frontend/apps/skriptoteket/src/router/index.spec.ts`
- `frontend/apps/skriptoteket/src/components/editor/EditorWorkspaceToolbar.spec.ts`
- `frontend/apps/skriptoteket/src/components/editor/ChatDrawer.spec.ts`
- `frontend/apps/skriptoteket/src/components/editor/diff/CodeMirrorMergeDiff.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerView.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/useClassroomState.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspacePane.smart-rules.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesWorkspacePane.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerExportActionGroup.spec.ts`

## Current gap to keep in mind

The design system is canonical at the rules/docs level, but not yet fully canonical at the package
level.

Today:

- tokens are shared through backend static CSS
- generic primitives live inside the SPA app
- planner dense-tool controls still include app-local wrappers
- editor and planner both act as proving grounds

So the immediate ST-29-01 implementation path is:

1. freeze docs and codemap
2. implement shared dense-tool primitives inside the SPA
3. prove them in `Sittplatser`
4. only later decide whether extraction into `frontend/packages/` is justified

## Related implementation slices

- `docs/backlog/prs/pr-0156-st-29-01-control-language-freeze-primitive-contract-and-fe-codemap.md`
- `docs/backlog/prs/pr-0157-st-29-01-shared-dense-tool-primitives-and-canonical-symbol-assets.md`
- `docs/backlog/prs/pr-0158-st-29-01-seating-workspace-adoption-of-shared-dense-tool-primitives.md`
