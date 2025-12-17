---
type: story
id: ST-08-07
title: "Admin help (Förslag + Verktyg)"
status: ready
owners: "agents"
created: 2025-12-17
epic: "EPIC-08"
acceptance_criteria:
  - "Given admin pages, when opening help, then it explains statuses and the actions available (review, publish, depublish) in Swedish"
  - "Given the decision form, when opening field help, then it explains what to write in the rationale and when fields apply (accept vs deny)"
---

## Scope

Kontext-hjälp för admins/superuser:

- `suggestions_review_queue.html`
- `suggestions_review_detail.html`
- `admin_tools.html`

## Tasks

- [ ] Skapa help topics för varje sida
- [ ] Lägg till fält-hjälp för beslut:
  - [ ] “Motivering” (kort, konkret, exempel)
  - [ ] “Titel/Beskrivning” (används vid accept)
- [ ] Förklara publicera/avpublicera ur ett användarperspektiv (”syns i katalogen / går att köra”)

## Files

- `src/skriptoteket/web/templates/suggestions_review_queue.html`
- `src/skriptoteket/web/templates/suggestions_review_detail.html`
- `src/skriptoteket/web/templates/admin_tools.html`
- `src/skriptoteket/web/templates/partials/` (help topics)
