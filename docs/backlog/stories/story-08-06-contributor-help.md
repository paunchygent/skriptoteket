---
type: story
id: ST-08-06
title: "Contributor help (Mina verktyg + Föreslå skript)"
status: ready
owners: "agents"
created: 2025-12-17
epic: "EPIC-08"
acceptance_criteria:
  - "Given contributor pages, when opening help, then it explains what each panel lets the user do (edit, submit suggestion, choose professions/categories)"
  - "Given non-trivial text fields (title/description), when focusing them, then placeholder examples are shown and field help is available"
---

## Scope

Kontext-hjälp för contributors:

- `my_tools.html`
- `suggestions_new.html`

## Tasks

- [ ] Skapa help topics för båda sidorna (kort, actions-fokuserat)
- [ ] Lägg till fält-hjälp + placeholder-exempel för:
  - [ ] titel (t.ex. “Omvandla klasslista till …”)
  - [ ] beskrivning (t.ex. 1–2 meningar om nytta och input)
  - [ ] yrken/kategorier (vad markeringarna används till)
- [ ] Förklara granskningsflödet på ett icke-tekniskt sätt (”ligger i granskningskön”)

## Files

- `src/skriptoteket/web/templates/my_tools.html`
- `src/skriptoteket/web/templates/suggestions_new.html`
- `src/skriptoteket/web/templates/partials/` (help topics)
