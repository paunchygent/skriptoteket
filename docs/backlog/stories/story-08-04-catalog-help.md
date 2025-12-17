---
type: story
id: ST-08-04
title: "Catalog help (browse + run)"
status: ready
owners: "agents"
created: 2025-12-17
epic: "EPIC-08"
acceptance_criteria:
  - "Given browse pages, when opening help, then it explains how to navigate yrke → kategori → verktyg"
  - "Given a tool run page, when opening help, then it explains how to upload a file and run the tool"
  - "Given the file upload control, when opening field help, then it explains what kind of file is expected in plain Swedish"
---

## Scope

Kontext-hjälp för katalogflödet:

- `browse_professions.html`
- `browse_categories.html`
- `browse_tools.html`
- `tools/run.html`

## Tasks

- [ ] Skapa help topics för varje sida (kort, stegvis, actions-fokuserat)
- [ ] Lägg till fält-hjälp vid filuppladdning på `tools/run.html`
- [ ] Säkerställ “Till hjälpindex” fungerar från alla dessa sidor

## Files

- `src/skriptoteket/web/templates/browse_professions.html`
- `src/skriptoteket/web/templates/browse_categories.html`
- `src/skriptoteket/web/templates/browse_tools.html`
- `src/skriptoteket/web/templates/tools/run.html`
- `src/skriptoteket/web/templates/partials/` (help topics)
