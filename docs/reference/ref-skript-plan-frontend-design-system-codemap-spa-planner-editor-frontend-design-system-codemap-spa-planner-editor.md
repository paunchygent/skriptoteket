---
type: reference
id: REF-SKRIPT-PLAN-frontend-design-system-codemap-spa-planner-editor
title: Frontend design-system codemap (SPA, planner, editor)
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
reference_kind: plan
retired_ids:
- REF-frontend-design-system-codemap-2026-03-28
summary: Frontend design-system codemap (SPA, planner, editor)
---

## Outcome And Purpose

### Source: Purpose

This codemap is the canonical reading guide to Skriptoteket’s frontend design system as it exists
today in the Vue/Vite SPA.

Use it when you need to answer one of these questions:

- Where do the design-system rules actually live?
- Where do tokens become CSS and Tailwind utilities?
- Where do shared primitives exist today?
- Which files are the real proving grounds for dense tool UX?
- Where does the shared transition-continuity rule live?
- What should a frontend designer read before changing planner or editor controls?

## Planning Boundary

The source does not provide a separate planning boundary section; no additional planning boundary is recorded.

## Evidence Basis

### Source: Current structural truth

- The frontend is a pnpm workspace rooted at `frontend/`.
- The only live app package today is `frontend/apps/skriptoteket/`.
- `frontend/packages/` exists, but there is no shipped shared UI package there yet.
- That means the current design system is real, but it is distributed across:
  - docs and rules
  - token CSS in backend-served static assets
  - shared UI components inside the SPA app
  - planner/editor proving-ground surfaces

## Confirmed Contract

The source does not provide a separate confirmed contract section; no additional confirmed contract is recorded.

## Backlog Derivation

### Source: Governing docs and rules

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
- `docs/adr/adr-0077-same-shell-transition-continuity.md`
- `docs/reference/ref-frontend-transition-continuity-v1.md`
- `docs/reference/ref-shared-tool-control-language-v1.md`
- `docs/reference/ref-klassrumskartan-workspace-ui-doctrine-2026-03-28.md`
- `docs/reference/ref-tool-editor-framework-codemap.md`
- `.codex/rules/045-huleedu-design-system.md`

### Source: Related implementation slices

- `docs/backlog/prs/pr-0156-st-29-01-control-language-freeze-primitive-contract-and-fe-codemap.md`
- `docs/backlog/prs/pr-0157-st-29-01-shared-dense-tool-primitives-and-canonical-symbol-assets.md`
- `docs/backlog/prs/pr-0158-st-29-01-seating-workspace-adoption-of-shared-dense-tool-primitives.md`

## Planning Stop Conditions

The source does not provide a separate planning stop conditions section; no additional planning stop conditions is recorded.

### Source: Reading order

1. Governance and doctrine
2. Workspace and build entrypoints
3. Token pipeline
4. Shared primitives and icons
5. Dense tool examples in the editor
6. Dense workspace examples in Klassrumskartan
7. Tests and verification harnesses

### Source: Live proving routes

- Planner: `http://127.0.0.1:5173/apps/classroom.group-seating-studio`
- Editor hub: `http://127.0.0.1:5173/editor?pick=1`
- Tool editor: `http://127.0.0.1:5173/admin/tools/:toolId`

### Source: Layer map

```text
Docs + rules
  -> token source
     -> theme bridge
        -> shared SPA primitives
           -> dense tool compositions
              -> planner and editor surfaces
                 -> tests + live verification
```

### Source: Workspace, build, and app entrypoints

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

### Source: Token pipeline

This is the real styling contract path.

- Canonical token source:
  - `src/skriptoteket/web/static/css/huleedu-design-tokens.css`
- SPA token import wrapper:
  - `frontend/apps/skriptoteket/src/styles/tokens.css`
- Tailwind theme bridge:
  - `frontend/apps/skriptoteket/src/styles/tailwind-theme.css`
- SPA CSS entrypoint and primitive classes:
  - `frontend/apps/skriptoteket/src/assets/main.css`

### Source: Current palette contract

- Deep Navy `#082B4C`: `--huleedu-navy`, `text-navy`, `border-navy`, structural and long-form text.
- Warm Terracotta `#C94F32`: `--huleedu-terracotta`, brand accent only.
- Verdigris Teal `#3F7F78`: `--huleedu-action`, `bg-action`, `text-action`, functional action,
  selected state, focus, and calm confirmation.
- Button text white is exposed as `--button-primary-text` / `text-button-primary-text` so filled
  action controls do not rely on Tailwind default color names.
- Canvas/Paper `#FAFAF6`: `--huleedu-paper` / `--huleedu-canvas`, light warm surface.
- Modal shell: `--huleedu-modal` / `--surface-modal`, exposed as `bg-modal` for opaque
  canvas-toned modal, dialog, popover, drawer, and sheet shells over overlays.
- Panel shell: `--huleedu-panel` / `--huleedu-panel-muted`, exposed as `bg-panel` and
  `bg-panel-muted` for translucent canvas-toned panels and internal rows.
- Critical burgundy `#4D1521`: `--huleedu-critical`, `bg-critical`, `text-critical`, destructive
  and truly critical decisions.
- Warning amber remains `--huleedu-warning`; warning is not terracotta or teal.

`--huleedu-burgundy` and `burgundy` utilities remain compatibility aliases for older call sites. New
code should prefer `action`, `terracotta`, `critical`, `warning`, or `error` according to the semantic role.

Surface rule: use the light canvas as the uniform base. Avoid large white panels stacked over canvas unless
the object needs deliberate contrast; use `bg-panel` for in-page panel shells and `bg-panel-muted` or semantic
tints for rows/highlights so pages do not feel blotchy. Use `bg-modal` for opaque modal/dialog/popover/drawer
shells that float over dimmed or layered content.

Action hierarchy rule: Verdigris fill is for true primary CTA or selected/active state. Secondary actions
that still belong to the action family, such as share-link creation, use Verdigris border/text treatment and
semantic icons (`IconLink2` for link/share), not primary fill or generic plus symbols.

### Source: Shared primitive and asset surfaces

These files are the current shared design-system implementation layer inside the SPA.

### Source: Icons

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

### Source: Generic UI primitives

- `frontend/apps/skriptoteket/src/components/ui/SystemMessage.vue`
- `frontend/apps/skriptoteket/src/components/ui/ToastHost.vue`
- `frontend/apps/skriptoteket/src/components/ui/ToggleSwitch.vue`
- `frontend/apps/skriptoteket/src/components/ui/UiCollapse.vue`
- `frontend/apps/skriptoteket/src/components/ui/UiMarkdown.vue`
- `frontend/apps/skriptoteket/src/components/ui/UiSearchBar.vue`
- `frontend/apps/skriptoteket/src/components/ui/UiSegmentedToggle.vue`

### Source: Typed action/output renderers

- `frontend/apps/skriptoteket/src/components/ui-actions/index.ts`
- `frontend/apps/skriptoteket/src/components/ui-actions/UiActionForm.vue`
- `frontend/apps/skriptoteket/src/components/ui-actions/UiActionFieldRenderer.vue`
- `frontend/apps/skriptoteket/src/components/ui-outputs/index.ts`
- `frontend/apps/skriptoteket/src/components/ui-outputs/UiOutputRenderer.vue`

### Source: Dense tool reference surface: the code editor

These files show how the current product handles command surfaces, drawers, editing panes, compare
views, and assistant surfaces.

### Source: Route and page entry

- `frontend/apps/skriptoteket/src/views/editor/EditorHubView.vue`
- `frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue`

### Source: Shared editor shell and command surfaces

- `frontend/apps/skriptoteket/src/components/editor/ScriptEditorPageShell.vue`
- `frontend/apps/skriptoteket/src/components/editor/ScriptEditorHeaderPanel.vue`
- `frontend/apps/skriptoteket/src/components/editor/EditorWorkspacePanel.vue`
- `frontend/apps/skriptoteket/src/components/editor/EditorWorkspaceToolbar.vue`
- `frontend/apps/skriptoteket/src/components/editor/EditorWorkspaceModeSelector.vue`
- `frontend/apps/skriptoteket/src/components/editor/EditorToolMenu.vue`
- `frontend/apps/skriptoteket/src/components/editor/WorkflowActionsDropdown.vue`
- `frontend/apps/skriptoteket/src/components/editor/WorkflowContextButtons.vue`

### Source: Core content surfaces

- `frontend/apps/skriptoteket/src/components/editor/EditorSourceCodePanel.vue`
- `frontend/apps/skriptoteket/src/components/editor/EditorInputSchemaPanel.vue`
- `frontend/apps/skriptoteket/src/components/editor/EditorSettingsSchemaPanel.vue`
- `frontend/apps/skriptoteket/src/components/editor/EditorSandboxPanel.vue`
- `frontend/apps/skriptoteket/src/components/editor/EditorComparePanel.vue`
- `frontend/apps/skriptoteket/src/components/editor/CodeMirrorEditor.vue`

### Source: Drawer and secondary surfaces

- `frontend/apps/skriptoteket/src/components/editor/VersionHistoryDrawer.vue`
- `frontend/apps/skriptoteket/src/components/editor/MetadataDrawer.vue`
- `frontend/apps/skriptoteket/src/components/editor/InstructionsDrawer.vue`
- `frontend/apps/skriptoteket/src/components/editor/MaintainersDrawer.vue`
- `frontend/apps/skriptoteket/src/components/editor/ChatDrawer.vue`
- `frontend/apps/skriptoteket/src/components/editor/ScriptEditorAiPanel.vue`

### Source: Diff and review surfaces

- `frontend/apps/skriptoteket/src/components/editor/diff/VirtualFileDiffViewer.vue`
- `frontend/apps/skriptoteket/src/components/editor/diff/AiVirtualFileDiffViewer.vue`
- `frontend/apps/skriptoteket/src/components/editor/diff/CodeMirrorMergeDiff.vue`

### Source: Editor state and orchestration

- `frontend/apps/skriptoteket/src/composables/editor/useScriptEditor.ts`
- `frontend/apps/skriptoteket/src/composables/editor/useScriptEditorPageState.ts`
- `frontend/apps/skriptoteket/src/composables/editor/useScriptEditorDrawers.ts`
- `frontend/apps/skriptoteket/src/composables/editor/useDraftLock.ts`
- `frontend/apps/skriptoteket/src/composables/editor/useEditorCompareData.ts`
- `frontend/apps/skriptoteket/src/composables/editor/useEditorCompareState.ts`
- `frontend/apps/skriptoteket/src/composables/editor/useEditorSandboxActions.ts`
- `frontend/apps/skriptoteket/src/composables/editor/useEditorWorkflowActions.ts`
- `frontend/apps/skriptoteket/src/composables/editor/useEditorChat.ts`

### Source: Dense workspace reference surface: Klassrumskartan

These files are the current proving ground for desktop-first multi-workspace design.

### Source: Route and orchestration

- `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerView.vue`
- `frontend/apps/skriptoteket/src/views/apps/useClassroomPlannerRouteShell.ts`
- `frontend/apps/skriptoteket/src/views/apps/useClassroomState.ts`
- `frontend/apps/skriptoteket/src/views/apps/useSmartRuleUiState.ts`
- `frontend/apps/skriptoteket/src/views/apps/useRosterSmartRuleLane.ts`
- `frontend/apps/skriptoteket/src/views/apps/useRoomViewportZoom.ts`
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerNavigation.ts`
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerOverviewStore.ts`
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerExportFlow.ts`

### Source: Shared planner shell and control surfaces

- `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceActionBar.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerTopPanel.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerToolbarIconButton.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerToolbarOverflowMenu.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerExportActionGroup.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerHistoryDrawer.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerMetadataDrawer.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerConfirmationDialog.vue`

### Source: Overview mode

- `frontend/apps/skriptoteket/src/views/apps/components/PlannerOverviewResumeCards.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerRosterOverviewPanel.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerTemplateOverviewPanel.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerClassWorkspace.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/CreateRosterModal.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/CreateRoomTemplateModal.vue`

### Source: Grouping mode

- `frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspacePane.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/GroupBoard.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/GroupCard.vue`

### Source: Seating mode

- `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspacePane.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerStudentPool.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerSmartRulesSummaryStrip.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/RoomCanvas.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/RoomSceneSurface.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/RoomSeatToken.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/SeatNode.vue`

### Source: Rules mode

- `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesWorkspacePane.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesToolRail.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesMapPanel.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesMapCanvas.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesSeatNode.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesInspector.vue`

### Source: Room/classroom editor surfaces

- `frontend/apps/skriptoteket/src/views/apps/useRoomTemplateEditorState.ts`
- `frontend/apps/skriptoteket/src/views/apps/components/RoomTemplateBuilderSurface.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/RoomTemplateEditorSidebar.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/RoomTemplatePreviewScene.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/RoomFixtureArtwork.vue`

### Source: Tests that expose design-system behavior

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

### Source: Current gap to keep in mind

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
