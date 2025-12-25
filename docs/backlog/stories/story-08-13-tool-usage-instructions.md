---
type: story
id: ST-08-13
title: "Tool usage instructions"
status: done
owners: "agents"
created: 2025-12-24
updated: 2025-12-25
epic: "EPIC-08"
acceptance_criteria:
  - "Given a tool page, when the tool has usage_instructions, then a collapsible section 'Så här gör du' is displayed"
  - "Given usage_instructions with markdown, when the section is expanded, then markdown is rendered correctly (headings, lists, emphasis)"
  - "Given a tool without usage_instructions, when the page loads, then no instructions section is shown"
  - "Given script bank with usage_instructions, when seed runs, then usage_instructions is synced to the database"
  - "Given UiOutputMarkdown in tool results, when markdown content is returned, then it is rendered (not shown as preformatted text)"
ui_impact: "New collapsible section in ToolRunView; fixed markdown rendering in tool outputs"
data_impact: "New column usage_instructions (TEXT) on tool_versions table"
risks:
  - "Markdown XSS - mitigate by sanitizing HTML output from marked"
dependencies:
  - "ADR-0036 (accepted)"
---

## Context

Users need clear, step-by-step instructions for how to use tools effectively. Currently, only a brief `summary` exists which is insufficient for explaining file preparation, expected outputs, and post-processing steps.

This story implements the architecture from ADR-0036 to add `usage_instructions` (markdown) to `ToolVersion` and display it in the tool run view.

## Notes

### Markdown rendering

- Use `marked` library (lightweight, well-maintained)
- Sanitize output to prevent XSS
- Style with Tailwind prose classes for readable typography

### UI design

- Collapsible section, collapsed by default (reduces visual noise)
- Positioned above the file upload area
- Swedish label: "Så här gör du"
- Chevron icon indicates expand/collapse state

### Script bank integration

Example for `ist-vh-mejl-bcc`:

```markdown
## Så här gör du

### Steg 1: Exportera klasslistan från IST
1. Logga in i IST Administration
2. Gå till den klass eller grupp du vill skicka till
3. Exportera listan som Excel (.xlsx) eller CSV

### Steg 2: Ladda upp filen
Ladda upp din exporterade fil (.xlsx eller .csv).

### Steg 3: Kopiera resultatet till Outlook
1. Ladda ner filen `emails_<datum>.txt`
2. Öppna filen och kopiera innehållet
3. I Outlook: Skapa nytt mejl → BCC → klistra in
```

### Files to modify

**Backend:**
- `src/skriptoteket/script_bank/models.py` - add field
- `src/skriptoteket/script_bank/bank.py` - add content
- `src/skriptoteket/domain/scripting/models.py` - add field
- `src/skriptoteket/infrastructure/db/models/tool_version.py` - add column
- `migrations/versions/` - new migration
- `src/skriptoteket/web/api/v1/tools.py` - include in response
- `src/skriptoteket/cli/main.py` - sync in seed

**Frontend:**
- `frontend/apps/skriptoteket/package.json` - add marked
- `frontend/apps/skriptoteket/src/components/ui-outputs/UiOutputMarkdown.vue` - fix rendering
- `frontend/apps/skriptoteket/src/components/tool-run/UsageInstructions.vue` - new component
- `frontend/apps/skriptoteket/src/views/ToolRunView.vue` - integrate component

## Implementation (2025-12-25)

### Display (user-facing)
- SPA: Added animated "Så här gör du" drawer in ToolRunView; extracted reusable markdown renderer (`frontend/apps/skriptoteket/src/components/ui/UiMarkdown.vue`).
- API: Added per-user seen state + mark-seen endpoint to persist across devices (`src/skriptoteket/web/api/v1/tools.py`).
- Verified: `pdm run python -m scripts.playwright_st_08_13_tool_usage_instructions_e2e --base-url http://127.0.0.1:5173` (artifacts: `.artifacts/st-08-13-tool-usage-instructions/`).

### Editor (contributor/admin)
- SPA: InstructionsDrawer with markdown edit + live preview toggle (`frontend/apps/skriptoteket/src/components/editor/InstructionsDrawer.vue`).
- Composable: `useScriptEditor.ts` tracks `usageInstructions` state, includes in save payloads.
- API: `usage_instructions` field added to `EditorBootResponse`, `CreateDraftVersionRequest`, `SaveDraftVersionRequest` (`src/skriptoteket/web/api/v1/editor.py`).
