---
type: story
id: ST-13-02
title: "Replace inline action feedback with toasts"
status: done
owners: "agents"
created: 2025-12-25
epic: "EPIC-13"
acceptance_criteria:
  - "Given an admin publishes or depublishes a tool, when the action completes, then the app shows toast feedback without layout jump"
  - "Given a user saves per-tool settings, when the save succeeds or fails, then the app shows toast feedback"
  - "Given an admin performs script editor save/workflow actions, when the action completes, then the app shows toast feedback"
  - "Given a contributor submits a suggestion or an admin decides a suggestion, when the action completes, then the app shows toast feedback"
  - "Blocking load errors remain inline as system messages (not toasts)"
ui_impact: "Removes layout-shifting success/error banners in key flows and replaces them with the toast overlay."
data_impact: "None."
dependencies: ["ST-13-01"]
---

## Context

Once the toast primitives exist (ST-13-01), the next step is to migrate the most visible inline message blocks that
currently cause jumpy transitions for users.

### Known migration targets (current SPA)

- Admin tools list publish/depublish: `frontend/apps/skriptoteket/src/views/admin/AdminToolsView.vue`
- Script editor save + workflow actions: `frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue`
- Tool run settings save: `frontend/apps/skriptoteket/src/components/tool-run/ToolRunSettingsPanel.vue`
- Suggestion submit: `frontend/apps/skriptoteket/src/views/SuggestionNewView.vue`
- Admin suggestion decision: `frontend/apps/skriptoteket/src/views/admin/AdminSuggestionDetailView.vue`
