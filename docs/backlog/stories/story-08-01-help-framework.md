---
type: story
id: ST-08-01
title: "Help framework (toggle, index, close behavior)"
status: ready
owners: "agents"
created: 2025-12-17
epic: "EPIC-08"
acceptance_criteria:
  - "Given any page, when clicking 'Hjälp', then a help panel opens and is reachable with keyboard"
  - "Given help is open, when clicking outside the help area or pressing Escape, then it closes"
  - "Given help is open, when interacting with other UI (links/forms), then help collapses"
  - "Given a page help view, when clicking 'Till hjälpindex', then the help index for the current login state is shown"
  - "Given role-based navigation, when viewing help index, then only relevant topics are listed"
---

## Context

Skriptoteket behöver en inbyggd, låg-tröskel “Hjälp” som är konsekvent på alla sidor och som visar rätt innehåll beroende på var användaren befinner sig (och vilken roll användaren har).

Denna story definierar **ramverket**. Innehållet (copy) levereras i separata stories per sida.

## UX-principer (source of truth)

- Kortfattat, handlingsorienterat och pedagogiskt på svenska (ingen tekniksnack).
- Hjälp ska vara **tydlig men diskret**: synlig entry-point, men inte “i vägen”.
- Progressive disclosure: index → sida → (valfritt) små förklaringar vid fält.
- Hjälp stänger automatiskt när användaren fortsätter jobba (klick/fokus utanför, Escape, navigation).

## Tekniskt upplägg (utan nya beroenden)

- En global “Hjälp”-toggle i `base.html` (visas både före/efter login).
- En help-panel/drawer som renderas i base-layout och fylls med **kontext**:
  - *Index* (olika index beroende på login-state)
  - *Sida* (hjälp för aktuell sida)
- Kontext-id sätts explicit från routes/templates (undvik “magisk” matchning på URL).
- Field-level micro-help återanvänds som en liten komponent/pattern:
  - diskret ikon nära label
  - kort tooltip/popover
  - exempel via placeholder/ghost text (försvinner när man skriver)

## Tasks

- [ ] UI-shell: lägg till “Hjälp” i `src/skriptoteket/web/templates/base.html` (nära header-actions)
- [ ] Help container: lägg till en panel/drawer i base-layout (kan vara dold som default)
- [ ] Context loading:
  - [ ] definiera en liten konvention för `help_context_id` per sida (t.ex. `"login"`, `"home"`, `"browse_professions"`, `"admin_tools"`, `"editor"`)
  - [ ] definiera en “index”-vy som skiljer på logged-out och logged-in (t.ex. `index_logged_out` / `index_logged_in`)
- [ ] Beteende (vanilla JS i `src/skriptoteket/web/static/js/app.js`):
  - [ ] toggle open/close + uppdatera `aria-expanded`
  - [ ] stäng på `Escape`
  - [ ] stäng på click/focus utanför helpytan
  - [ ] stäng på navigation/HTMX-interaktion (ex. `htmx:beforeRequest`)
- [ ] Styling (HuleEdu tokens + befintliga komponenter):
  - [ ] hjälp-panel känns som “kort/drawer” och är lätt att skanna (rubriker + punktlistor)
  - [ ] tydlig men diskret hjälp-ikon för fält

## Files (expected)

- `src/skriptoteket/web/templates/base.html`
- `src/skriptoteket/web/static/js/app.js`
- `src/skriptoteket/web/static/css/app/components.css` (eller separat fil under `app/` om uppdelning behövs)
- `src/skriptoteket/web/templates/partials/` (nya partials för help index + topics)

## Notes

- All hjälpcopy ska vara på svenska och fokusera på vad användaren kan göra (inte implementation).
- Undvik duplicering: ramverket + beteende definieras här, sid-specifik copy i respektive story.
