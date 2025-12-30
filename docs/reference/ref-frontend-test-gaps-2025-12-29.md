---
type: reference
id: REF-frontend-test-gaps-2025-12-29
title: "Reference: Frontend test coverage gaps (SPA)"
status: active
owners: "agents"
created: 2025-12-29
topic: "frontend-testing"
---

## Overview

This reference lists current Vitest coverage gaps for the SPA (`frontend/apps/skriptoteket`).
Check items off as coverage is added. Critical gaps should be prioritized in order.

## Critical gaps (start here)

- [x] Router guards + auth redirects (`frontend/apps/skriptoteket/src/router/index.ts`, `frontend/apps/skriptoteket/src/router/routes.ts`, `frontend/apps/skriptoteket/src/composables/useLoginModal.ts`)
- [x] Tool run flow (validation, FormData, polling, multi-step actions) (`frontend/apps/skriptoteket/src/composables/tools/useToolRun.ts`)
- [x] Editor save + workflow actions (`frontend/apps/skriptoteket/src/composables/editor/useScriptEditor.ts`, `frontend/apps/skriptoteket/src/composables/editor/useEditorWorkflowActions.ts`)
- [x] Draft lock acquisition + heartbeat (`frontend/apps/skriptoteket/src/composables/editor/useDraftLock.ts`)
- [x] Tool settings flows (load/save, state_rev conflicts) (`frontend/apps/skriptoteket/src/composables/tools/useToolSettings.ts`, `frontend/apps/skriptoteket/src/composables/editor/useToolVersionSettings.ts`, `frontend/apps/skriptoteket/src/composables/editor/useSandboxSettings.ts`)

## High-priority gaps

- [ ] Catalog filtering + route sync + debounce (`frontend/apps/skriptoteket/src/composables/useCatalogFilters.ts`)
- [ ] Favorites toggle (`frontend/apps/skriptoteket/src/composables/useFavorites.ts`)
- [ ] Profile update + password/email flows (`frontend/apps/skriptoteket/src/composables/useProfile.ts`)
- [ ] Tool maintainers admin flow (`frontend/apps/skriptoteket/src/composables/editor/useToolMaintainers.ts`)
- [ ] Tool taxonomy editor (`frontend/apps/skriptoteket/src/composables/editor/useToolTaxonomy.ts`)
- [ ] Editor schema parsing helper (`frontend/apps/skriptoteket/src/composables/editor/useEditorSchemaParsing.ts`)
- [ ] Script editor intelligence loader (`frontend/apps/skriptoteket/src/composables/editor/useSkriptoteketIntelligenceExtensions.ts`)

## Medium-priority gaps

- [ ] Script editor completions (`frontend/apps/skriptoteket/src/composables/editor/skriptoteketCompletions.ts`)
- [ ] Script editor hover docs (`frontend/apps/skriptoteket/src/composables/editor/skriptoteketHover.ts`)
- [ ] Python parsing helpers (`frontend/apps/skriptoteket/src/composables/editor/skriptoteketPythonTree.ts`, `frontend/apps/skriptoteket/src/composables/editor/skriptoteketPythonAnalysis.ts`, `frontend/apps/skriptoteket/src/composables/editor/skriptoteketPythonVariables.ts`)
- [ ] Settings form conversions (`frontend/apps/skriptoteket/src/composables/tools/toolSettingsForm.ts`)
- [ ] Page transitions logic (`frontend/apps/skriptoteket/src/composables/usePageTransition.ts`)

## Component + view coverage baseline

- [ ] CodeMirror wiring (`frontend/apps/skriptoteket/src/components/editor/CodeMirrorEditor.vue`)
- [ ] Tool run UI (`frontend/apps/skriptoteket/src/views/ToolRunView.vue`, `frontend/apps/skriptoteket/src/components/tool-run/**`)
- [ ] Script editor UI (`frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue`, `frontend/apps/skriptoteket/src/components/editor/**`)
- [ ] Auth/profile UI (`frontend/apps/skriptoteket/src/views/ProfileView.vue`, `frontend/apps/skriptoteket/src/components/auth/**`)
- [ ] Catalog/browse UI (`frontend/apps/skriptoteket/src/views/Browse*.vue`, `frontend/apps/skriptoteket/src/components/catalog/**`)

## Already covered (for reference)

- [x] API client (`frontend/apps/skriptoteket/src/api/client.ts`)
- [x] Auth store (`frontend/apps/skriptoteket/src/stores/auth.ts`)
- [x] Toast store (`frontend/apps/skriptoteket/src/stores/toast.ts`)
- [x] Tool inputs (`frontend/apps/skriptoteket/src/composables/tools/useToolInputs.ts`)
- [x] Tool settings helpers (`frontend/apps/skriptoteket/src/composables/tools/toolSettingsHelpers.ts`)
- [x] Admin users (`frontend/apps/skriptoteket/src/composables/admin/useAdminUsers.ts`)
- [x] CodeMirror linting (`frontend/apps/skriptoteket/src/composables/editor/skriptoteketLinter.ts`)
