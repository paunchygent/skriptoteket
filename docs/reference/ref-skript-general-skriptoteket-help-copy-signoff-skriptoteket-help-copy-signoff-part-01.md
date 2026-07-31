---
type: reference
id: REF-SKRIPT-GENERAL-skriptoteket-help-copy-signoff-PART-01
title: Skriptoteket help copy signoff — part 01
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
root: REF-SKRIPT-GENERAL-skriptoteket-help-copy-signoff
part: 1
---

## Overview

Source: `docs/reference/ref-skriptoteket-help-copy-signoff.md`. Skriptoteket help copy signoff.

This reference is the approval surface for the exact Swedish help copy that will later be implemented in the SPA help topics. No word-by-word help topic implementation should ship until the relevant copy block in this reference has been reviewed and marked approved by the product owner. - Write in Swedish. - Keep the voice practical, calm, and teacher-facing. - Explain what the user can do, not how the system is built. - Prefer short bullets and concrete next actions. - Avoid jargon such as API, projection, route, stdout, stderr, schema, token, or sandbox unless the target user is explicitly a tool author in the editor. - Do not promise capabilities that are not available on the route. - Kee

## Facts And Semantics

This reference retains durable facts, terminology, evidence, and interpretation.

### Source evidence

### Purpose

This reference is the approval surface for the exact Swedish help copy that will
later be implemented in the SPA help topics.

No word-by-word help topic implementation should ship until the relevant copy
block in this reference has been reviewed and marked approved by the product
owner.

### Copy Rules

- Write in Swedish.
- Keep the voice practical, calm, and teacher-facing.
- Explain what the user can do, not how the system is built.
- Prefer short bullets and concrete next actions.
- Avoid jargon such as API, projection, route, stdout, stderr, schema, token,
  or sandbox unless the target user is explicitly a tool author in the editor.
- Do not promise capabilities that are not available on the route.
- Keep each route topic short enough to scan inside the existing help drawer.
- Keep field-level micro-help to one or two sentences plus an example when
  helpful.

### Approval States

Use these states per copy block:

- `draft`: wording is proposed but not yet reviewed.
- `approved`: wording may be implemented word for word.
- `revise`: wording needs another pass before implementation.
- `superseded`: wording is retained as history but no longer active.

### Route Topic Matrix

| Route name | Topic id | Current state | Copy signoff state | Notes |
|---|---|---:|---:|---|
| `home` | `home` | Implemented | approved | Expand only if role-aware home copy changes. |
| `auth-login`, `auth-callback` | `login` or new auth topic | Partial | approved | Align with HuleEdu-owned login ceremony. |
| `register`, `forgot-password`, `reset-password`, `verify-email` | new lifecycle topic | Missing | approved | Explain lifecycle handoff without app-local auth wording. |
| `auth-provisioning-required` | new provisioning topic | Missing | approved | Explain activation path and who to contact. |
| `browse`, `browse-professions` | `browse_professions` | Partial | approved | Route map must cover both route names. |
| `browse-categories` | `browse_categories` | Partial | approved | Keep category navigation short. |
| `browse-tools` | `browse_tools` | Partial | approved | Explain apps vs tools without implementation detail. |
| `tool-run` | `tools_run` | Partial | approved | Add input/file help and run-state expectations. |
| `my-runs` | new runs list topic | Missing | approved | Explain history, statuses, and downloads. |
| `my-runs-detail` | `tools_result` | Partial | approved | Explain result status, files, and recovery actions. |
| `vault` | new vault topic | Missing | approved | Explain saved files, restore/delete, quota. |
| `profile` | new profile topic | Missing | approved | Explain profile preferences and account links. |
| `app-detail` | `apps_detail` plus app contexts | Partial | approved | Generic app help should remain a fallback. |
| `public-app-detail` | `apps_detail` or public app topic | Missing | approved | Distinguish public guest capability from account-only features. |
| Klassrumskartan overview | `planner_overview` | Implemented | approved | Generated from the approved getting-started guide. |
| Klassrumskartan grouping | `planner_grouping` | Implemented | approved | Generated from the approved getting-started guide. |
| Klassrumskartan seating | `planner_seating` | Implemented | approved | Generated from the approved getting-started guide. |
| Klassrumskartan rules | `planner_rules` | Implemented | approved | Generated from the approved getting-started guide. |
| `my-tools` | `my_tools` | Partial | approved | Explain maintainer responsibilities. |
| `editor-hub` | new editor hub topic | Missing | approved | Explain where contributors start. |
| `suggestion-new` | `suggestions_new` | Partial | approved | Include title, description, profession/category micro-help. |
| `admin-suggestions`, `admin-suggestion-detail` | `admin_suggestions` | Partial | approved | Include decision statuses and rationale guidance. |
| `admin-tools` | `admin_tools` | Partial | approved | Include publish/unpublish consequences. |
| `admin-tool-editor`, `admin-tool-version-editor` | `admin_editor` | Partial | approved | Split overview/test/run-result guidance if needed. |
| `admin-users`, `admin-user-detail` | new user admin topic | Missing | approved | Superuser-only, local role/projection wording must be clear. |
| `forbidden` | new access topic | Missing | approved | Explain role/access mismatch without blame. |
| `public-app-route-recovery`, `not-found` | new recovery topic | Missing | approved | Match route recovery copy and next actions. |

### Copy Blocks

Draft the approved wording under this section before implementing topic
components. Keep each block in this shape:

```markdown
### Topic title

State: approved
Routes:

- `route-name`

Drawer copy:

- ...

Micro-help:

- Field label: ...

Approval notes:

- ...
```

### Start

State: approved
Routes:

- `home` for authenticated users. The signed-out public landing page should open the logged-out help index, not this topic.

Drawer copy:

- Start samlar de vanligaste vägarna vidare: katalogen, dina körningar och de bidrags- eller adminvyer du har behörighet till.
- Välj **Katalog** när du vill hitta ett verktyg eller en app. Välj **Mina körningar** när du vill gå tillbaka till ett tidigare resultat.
- Om en genväg eller sektion saknas beror det oftast på din roll eller på att du inte är inloggad.

Micro-help:

- Katalog: Verktyg och appar sorterade efter yrke och kategori.
- Mina körningar: Dina egna körningar och deras status.
- Bidra: Syns bara om du får föreslå eller bygga verktyg.
- Admin: Syns bara om du har en administratörsroll.

Approval notes:

- Ersätter tidigare formulering "kör dem när du behöver" och det otydliga "Om verktyget behöver fler saker, visas de under resultatet".
- Ersätter den för försvarande formuleringen "Det är ingenting som är trasigt" och undviker ASCII-inskottet kring behörighet.
- Nämn inte rolltekniska begrepp som "projection" eller "scope".

### App-detaljer

State: approved
Routes:

- `app-detail`
- `public-app-detail`

Drawer copy:

- Inloggad appvy: Appar är större arbetsytor, som Klassrumskartan, där du jobbar i flera steg inuti själva appen.
- Inloggad appvy: Klicka på appen för att öppna arbetsytan.
- Inloggad appvy: När du är inloggad sparas arbetet i appen, så att du kan fortsätta där du slutade nästa gång.
- Publik Klassrumskartan: Detta är en fullständig förhandsvisning av vad Klassrumskartan gör. Du kan prova arbetsytan direkt i webbläsaren.
- Publik Klassrumskartan: Logga in för att spara ditt arbete och kunna fortsätta där du slutade nästa gång.
- Publik Klassrumskartan: Om appen säger att du ska logga in beror det på att den här webbläsaren redan har använt Klassrumskartan med konto.

Micro-help:

- Appen: Öppnar appens egen arbetsyta.
- Beskrivning: Kort om vad appen är till för och vilka steg som ingår.
- Inloggning krävs: Sparat arbete och fortsatt arbete mellan besök hör till den inloggade appvyn.

Approval notes:

- Ersätter "Resultat och nästa steg visas under" som var otydligt ("under vad?").
- `app-detail` och `public-app-detail` behöver auth-/route-medveten copy eftersom den publika Klassrumskartan är en fullständig förhandsvisning och kan visa en inloggningsuppmaning i webbläsare som redan använt appen med konto.

### Mina verktyg

State: approved
Routes:

- `my-tools`

Drawer copy:

- Här ligger de verktyg du ansvarar för som bidragsgivare. Klicka på ett verktyg för att se versioner, beskrivning och metadata.
- Klicka **Redigera** för att öppna skripteditorn och jobba vidare på en ny version.
- Behöver du lämna över ansvaret för ett verktyg? Hör av dig till en administratör.

Micro-help:

- Redigera-knappen: Öppnar verktyget i skripteditorn för att skapa eller justera en version.
- Status: Visar om verktyget är publicerat, under granskning eller endast utkast.

Approval notes:

- Förtydligar vad "underhåller" innebär i praktiken (ansvarig som bidragsgivare).

### Inloggning

State: approved
Routes:

- `auth-login`
- `auth-callback`

Drawer copy:

- Logga in med ditt skolkonto. HuleEdu sköter själva inloggningen och skickar dig tillbaka till Skriptoteket när du är klar.
- Kommer du inte vidare? Gå tillbaka till Skriptotekets startsida och välj **Logga in** igen.
- Kvarstår problemet, be skolans HuleEdu-kontakt eller support om hjälp.

Micro-help:

- Logga in-knappen: Tar dig till HuleEdus inloggning. Du kommer tillbaka hit automatiskt.

Approval notes:

- Nämn inte "token", "session" eller "redirect" i användartext.
- Undvik teknisk webbläsarfelsökning i normal hjälptext.

### Skapa konto, glömt lösenord och bekräfta e-post

State: approved
Routes:

- `register`
- `forgot-password`
- `reset-password`
- `verify-email`

Drawer copy:

- Kontohanteringen sker hos HuleEdu. Det är där du skapar konto, byter lösenord och bekräftar din e-postadress.
- När du är klar skickas du tillbaka till Skriptoteket och kan logga in som vanligt.
- Får du inget mejl inom några minuter? Titta i skräpposten och kontrollera att du skrev rätt adress.

Micro-help:

- E-postadress: Använd den adress du vill logga in med. Den behöver tillhöra en godkänd skoldomän.
- Nytt lösenord: Välj något du inte använder någon annanstans. Minst tolv tecken rekommenderas.

Approval notes:

- Håll texten neutral i fråga om vilken identitetsleverantör som används; hänvisa till HuleEdu.

### Kontot behöver aktiveras

State: approved
Routes:

- `auth-provisioning-required`

Drawer copy:

- Inloggningen gick bra, men ditt konto är inte fullt aktiverat i Skriptoteket ännu.
- Oftast löser det sig av sig själv inom några minuter. Ladda om sidan och försök igen.
- Om problemen kvarstår: kontakta din skoladministratör eller be support om hjälp. Ange din e-postadress när du hör av dig -- det gör det snabbare att ta reda på var det fastnat.

Micro-help:

- Försök igen-knappen: Kontrollerar om kontot har aktiverats sedan sist.

Approval notes:

- Undvik att antyda att det är användarens fel.

### Bläddra bland yrken

State: approved
Routes:

- `browse`
- `browse-professions`

Drawer copy:

- Här hittar du verktyg och appar sorterade efter yrke. Välj det som ligger närmast ditt uppdrag -- du kan alltid gå tillbaka.
- Varje yrke leder vidare till de kategorier som är relevanta för just det arbetet.
- Letar du efter något särskilt? Använd sökfältet i toppen.

Micro-help:

- Yrkeskort: Klicka för att se kategorier och verktyg för det yrket.

Approval notes:

- Kalla det "yrken" och "kategorier", inte "taxonomi" eller "noder".

### Bläddra bland kategorier

State: approved
Routes:

- `browse-categories`

Drawer copy:

- Kategorierna grupperar verktyg efter vad de gör -- till exempel planering, bedömning eller elevkommunikation.
- Välj en kategori för att se alla verktyg som hör dit.
- Samma verktyg kan dyka upp under flera kategorier om det passar på fler ställen.

Micro-help:

- Kategorikort: Klicka för att se verktygen i kategorin.

Approval notes:

- Ingen text om hur kategorierna skapas eller underhålls.

### Bläddra bland verktyg

State: approved
Routes:

- `browse-tools`

Drawer copy:

- Här syns både **verktyg** och **appar**. Verktyg är små, fokuserade funktioner du kör med några inställningar. Appar är större arbetsytor -- som Klassrumskartan -- med egen vy och flera steg.
- Klicka på ett kort för att se mer och komma igång.
- Använd filtren för att begränsa till ditt yrke, en kategori eller en viss typ.

Micro-help:

- Filter: Kombinera yrke och kategori för att smalna av listan.
- Appmarkering: Kort märkta som "app" öppnas i en egen arbetsyta.

Approval notes:

- Skilj på verktyg och appar utan att gå in på teknisk arkitektur.

### Kör ett verktyg

State: approved
Routes:

- `tool-run`

Drawer copy:

- Fyll i fälten, ladda upp filer om det behövs och klicka **Kör**.
- Medan verktyget arbetar kan du lämna sidan -- körningen fortsätter i bakgrunden. Du hittar den igen under **Mina körningar**.
- När körningen är klar får du ett resultat du kan ladda ner eller spara i Kassaskåpet.

Micro-help:

- Textfält: Skriv eller klistra in det verktyget ber om. Exempel finns ofta i hjälptexten vid varje fält.
- Filuppladdning: Dra in filen eller klicka för att välja. Tillåtna format står vid fältet.
- Kör-knappen: Startar körningen. Den blir otillgänglig om något obligatoriskt fält saknas.

Approval notes:

- Säg "körning", inte "job" eller "process".

### Mina körningar

State: approved
Routes:

- `my-runs`

Drawer copy:

- Här ligger alla dina körningar, den senaste först. Du ser status, vilket verktyg det var och när den startade.
- Klicka på en rad för att se resultat, nedladdningar och felmeddelanden.
- Statusarna betyder: **pågår** -- verktyget arbetar, **klar** -- resultat finns att hämta, **misslyckad** -- något gick fel och du kan oftast försöka igen.

Micro-help:

- Rad i listan: Klicka för att öppna körningen i detalj.
- Status "misslyckad": Öppna körningen för att se vad som gick fel och om det går att köra om.

Approval notes:

- Undvik ord som "queue" och "worker".

### Körningsresultat

State: approved
Routes:

- `my-runs-detail`

Drawer copy:

- Här ser du vad verktyget gjorde och det som blev resultatet. Filer kan laddas ner direkt eller sparas i Kassaskåpet.
- Gick något fel visar vi ett begripligt meddelande om vad som hände och vad du kan prova.
- Behöver du köra om med samma inställningar klickar du **Kör igen**. Då öppnas verktyget med dina tidigare val ifyllda.

Micro-help:

- Ladda ner: Sparar filen lokalt på din dator.
- Spara i Kassaskåpet: Lägger filen i ditt personliga utrymme i Skriptoteket.
- Kör igen: Öppnar verktyget med samma fält som förra gången.

Approval notes:

- Tekniska loggar ska inte erbjudas i hjälptext -- bara i själva gränssnittet.
