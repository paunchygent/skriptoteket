---
type: story
id: ST-08-09
title: "Script editor help (test runner + run result)"
status: ready
owners: "agents"
created: 2025-12-17
epic: "EPIC-08"
acceptance_criteria:
  - "Given the script editor test area, when opening help, then it explains how to choose a file, run a test, and read the result"
  - "Given run errors, when opening help, then it explains next steps (fix code, try again) without technical jargon"
---

## Scope

Hjälp för testytan i editorn:

- Filuppladdning + “Testkör”
- Resultatytan (status, resultat/iframe, filer)

## Tasks

- [ ] Skapa help topic för testytan i `admin/script_editor.html`
- [ ] Lägg till fält-hjälp vid filval (vad som händer och vad som används som input)
- [ ] Förklara resultaten kort och action-fokuserat (t.ex. “om du ser fel: justera koden och testkör igen”)

## Files

- `src/skriptoteket/web/templates/admin/script_editor.html`
- `src/skriptoteket/web/templates/admin/partials/run_result.html`
- `src/skriptoteket/web/templates/partials/` (help topics)
