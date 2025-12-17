---
type: story
id: ST-08-08
title: "Script editor help (overview + versioning)"
status: ready
owners: "agents"
created: 2025-12-17
epic: "EPIC-08"
acceptance_criteria:
  - "Given the script editor page, when opening help, then it explains saving, drafts/versions, and the review/publish flow in plain Swedish"
  - "Given role restrictions, when opening help, then it clarifies which actions are available for the current role"
---

## Scope

Översiktshjälp för script editorn (utan testytan, som hanteras i ST-08-09).

## Tasks

- [ ] Skapa help topic för `admin/script_editor.html` (översikt)
- [ ] Förklara panelerna: redigering, process (skicka för granskning/publicera/begär ändringar), historik (versioner)
- [ ] Lägg till micro-help för fält som är otydliga:
  - [ ] “Startfunktion” (vad ska stå där)
  - [ ] “Ändringssammanfattning” (kort exempel)

## Files

- `src/skriptoteket/web/templates/admin/script_editor.html`
- `src/skriptoteket/web/templates/partials/` (help topics)
