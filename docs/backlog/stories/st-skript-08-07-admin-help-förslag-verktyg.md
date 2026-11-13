---
type: story
id: ST-SKRIPT-08-07
title: Admin help (Förslag + Verktyg)
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-08
acceptance_criteria:
- Given admin pages, when opening help, then it explains statuses and the actions
  available (review, publish, depublish) in Swedish
- Given the decision form, when opening field help, then it explains what to write
  in the rationale and when fields apply (accept vs deny)
retired_ids:
- ST-08-07
---

## Context
### Tasks
- [ ] Skapa help topics för varje sida
- [ ] Lägg till fält-hjälp för beslut:
  - [ ] “Motivering” (kort, konkret, exempel)
  - [ ] “Titel/Beskrivning” (används vid accept)
- [ ] Förklara publicera/avpublicera ur ett användarperspektiv (”syns i katalogen / går att köra”)
### Files
- `src/skriptoteket/web/templates/suggestions_review_queue.html`
- `src/skriptoteket/web/templates/suggestions_review_detail.html`
- `src/skriptoteket/web/templates/admin_tools.html`
- `src/skriptoteket/web/templates/partials/` (help topics)

## Epic Contract Slice
### Scope
Kontext-hjälp för admins/superuser:

- `suggestions_review_queue.html`
- `suggestions_review_detail.html`
- `admin_tools.html`

## ADR Coverage
The source record did not define a separate section for this package heading.

## Contract Inputs
The source record did not define a separate section for this package heading.

## Live Verification Plan
The source record did not define a separate section for this package heading.

## Non-Goals
The source record did not define a separate section for this package heading.

## Notes
The source record did not define a separate section for this package heading.

## Decision And Assumption Ledger
The source record did not define a separate section for this package heading.

## Plan Document Review
The source record did not define a separate section for this package heading.

## Story Closeout Review
The source record did not define a separate section for this package heading.
