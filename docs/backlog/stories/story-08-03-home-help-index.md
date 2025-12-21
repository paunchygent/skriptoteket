---
type: story
id: ST-08-03
title: "Post-login home help index (site map)"
status: done
owners: "agents"
created: 2025-12-17
epic: "EPIC-08"
acceptance_criteria:
  - "Given a logged-in user, when opening help index, then it explains the main navigation items and what actions they enable"
  - "Given different roles, when viewing help index, then the index only shows pages/actions available for that role"
---

## Scope

Ett “hjälpindex” för startsidan efter login som fungerar som en kort och lättbegriplig sitemap: vad finns i menyerna och vad kan man göra där.

## Hjälp-innehåll (svenska, kort)

- Katalog: hitta verktyg via yrke → kategori → verktyg, kör verktyg med fil.
- Mina verktyg (contributors+): se och öppna verktyg du underhåller.
- Föreslå skript (contributors+): skicka in idéer, välj yrken/kategorier.
- Förslag (admins+): granska och fatta beslut.
- Verktyg (admins+): publicera/avpublicera och öppna editorn.

## Tasks

- [x] Lägg till `help_context_id="home"` och koppla “Till hjälpindex” till logged-in index
- [x] Skapa help index för logged-in (role-aware) och länka till topics per sida
- [x] Säkerställ att copy är kort, actions-fokuserad och utan tekniska detaljer

## Files

- `src/skriptoteket/web/templates/home.html`
- `src/skriptoteket/web/templates/partials/` (help index + topic för home)
