---
type: story
id: ST-08-02
title: "Login help + micro-help"
status: done
owners: "agents"
created: 2025-12-17
epic: "EPIC-08"
acceptance_criteria:
  - "Given the login page, when opening help, then it explains how to log in and how to handle a forgotten password (contact admin)"
  - "Given the login form, when focusing email/password fields, then examples are shown via placeholder/ghost text without changing the actual field value"
  - "Given field help icons, when using keyboard, then help can be opened and closed without trapping focus"
---

## Scope

Kontextberoende hjälp för `login.html` inklusive fält-hjälp för e-post och lösenord.

## Hjälp-innehåll (svenska, kort)

- Vad inloggning gör (kommer till startsidan efter login).
- Vilken e-post som ska användas (skol-/arbetsadress).
- Glömt lösenord: **kontakta admin** (ingen återställning i systemet än).

## Tasks

- [x] Lägg till `help_context_id="login"` för sidan
- [x] Lägg till sida-hjälp (topic) för login
- [x] Lägg till diskret fält-hjälp:
  - [x] E-post: placeholder exempel (t.ex. `namn@skola.se`) + kort tooltip
  - [x] Lösenord: kort tooltip + ev. placeholder (t.ex. `••••••••`)

## Files

- `src/skriptoteket/web/templates/login.html`
- `src/skriptoteket/web/templates/partials/` (help topic för login)
