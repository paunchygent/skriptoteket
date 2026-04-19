---
type: reference
id: REF-skriptoteket-help-copy-signoff
title: "Skriptoteket help copy signoff"
status: active
owners: "agents"
created: 2026-04-20
topic: "help-copy"
links:
  - docs/backlog/epics/epic-08-contextual-help-and-onboarding.md
  - docs/backlog/stories/story-08-35-help-completion-route-coverage-and-copy-signoff.md
  - docs/backlog/prs/pr-0271-st-08-35-help-completion-route-coverage-and-copy-signoff.md
---

## Purpose

This reference is the approval surface for the exact Swedish help copy that will
later be implemented in the SPA help topics.

No word-by-word help topic implementation should ship until the relevant copy
block in this reference has been reviewed and marked approved by the product
owner.

## Copy Rules

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

## Approval States

Use these states per copy block:

- `draft`: wording is proposed but not yet reviewed.
- `approved`: wording may be implemented word for word.
- `revise`: wording needs another pass before implementation.
- `superseded`: wording is retained as history but no longer active.

## Route Topic Matrix

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

## Copy Blocks

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

### Kassaskåpet

State: approved
Routes:

- `vault`

Drawer copy:

- Kassaskåpet är ditt eget utrymme för filer du vill spara -- till exempel körresultat eller dokument du använder ofta.
- Du kan öppna, ladda ner eller ta bort filer. Tar du bort en fil är den borta för gott.
- Utrymmet är begränsat. När du närmar dig gränsen syns en varning högst upp.

Micro-help:

- Ladda ner: Sparar kopian på din dator. Originalet ligger kvar i Kassaskåpet.
- Ta bort: Raderar filen permanent.
- Utrymme: Visar hur mycket du har kvar av din kvot.

Approval notes:

- "Kassaskåpet" är det förvalda namnet; justera om produktnamnet ändras.

### Min profil

State: approved
Routes:

- `profile`

Drawer copy:

- Här ser du vilket konto du är inloggad med och vilka roller du har i Skriptoteket.
- Namn och e-post kommer från HuleEdu och ändras där -- inte här.
- Inställningar som språk och aviseringar styr du på den här sidan.

Micro-help:

- Roller: Visar vad du får göra i Skriptoteket. Vill du ha en annan roll pratar du med din skoladministratör.
- Länkad identitet: Kontot som används vid inloggning. Byter du skola kan du behöva be om att få det uppdaterat.

Approval notes:

- Säg "roll", inte "projection" eller "scope".

### Föreslå ett nytt verktyg

State: approved
Routes:

- `suggestion-new`

Drawer copy:

- Saknar du ett verktyg? Beskriv det här så tar vi en titt.
- Var konkret om vad du vill kunna göra och i vilket sammanhang -- det gör det mycket lättare att bedöma och bygga.
- När du skickar in förslaget får du en bekräftelse direkt på sidan.

Micro-help:

- Titel: En kort, beskrivande rubrik. Exempel: "Generera veckobrev från kalendern".
- Beskrivning: Vad ska verktyget göra, för vem, och när i arbetet används det? Exempel på indata och förväntat resultat hjälper mycket.
- Yrke: Välj det yrke förslaget främst gäller. Du kan lägga till fler om det passar flera.
- Kategori: Välj den kategori som bäst beskriver vad verktyget gör.

Approval notes:

- Lova inte att förslag byggs. Skriv att de bedöms.

### Administrera förslag

State: approved
Routes:

- `admin-suggestions`
- `admin-suggestion-detail`

Drawer copy:

- Här hanterar du inkomna förslag. Öppna ett förslag för att läsa det i sin helhet och sätta ett beslut.
- Statusarna betyder: **nytt** -- oöppnat, **under översyn** -- någon tittar på det, **godkänt** -- ska byggas, **avvisat** -- byggs inte just nu.
- Skriv alltid en kort motivering vid beslutet. Det är den texten användaren ser.

Micro-help:

- Beslut: Välj status och skriv en kort motivering riktad till den som lämnat förslaget.
- Motivering: Två-tre meningar räcker. Var saklig och konkret.

Approval notes:

- Tonen mot förslagsställaren ska alltid vara respektfull, även vid avslag.

### Administrera verktyg

State: approved
Routes:

- `admin-tools`

Drawer copy:

- Listan visar alla verktyg i Skriptoteket. Härifrån publicerar, avpublicerar och redigerar du dem.
- **Publicera** gör verktyget synligt för alla användare som har rätt roll. **Avpublicera** döljer det igen -- befintliga körningar påverkas inte.
- Ta bort ett verktyg bara om det verkligen inte ska finnas kvar. Körhistorik följer med.

Micro-help:

- Publicera-knappen: Gör verktyget tillgängligt för användare direkt.
- Avpublicera-knappen: Döljer verktyget men sparar versionen.

Approval notes:

- Skilj tydligt mellan "avpublicera" (döljs) och "ta bort" (raderas).

### Redigera verktyg

State: approved
Routes:

- `admin-tool-editor`
- `admin-tool-version-editor`

Drawer copy:

- Här bygger du verktyget: beskrivning, fält, filtyper och själva skriptet som körs.
- Testa alltid i **Testkörning** innan du publicerar. Då ser du exakt vad användaren kommer att se.
- Varje sparad version får ett eget nummer. Du kan alltid gå tillbaka till en tidigare version om något blir fel.

Micro-help:

- Testkörning: Kör verktyget med dina egna indata utan att publicera.
- Version: Visar vilken version du redigerar. Spara skapar en ny version, inte en överskrivning.
- Publicera: Gör vald version synlig för användarna.

Approval notes:

- Ordvalet "version" är avsett för lärare-utvecklare; det är okej i denna vy.

### Administrera användare

State: approved
Routes:

- `admin-users`
- `admin-user-detail`

Drawer copy:

- Här ser du användare i Skriptoteket och vilka roller de har lokalt hos oss.
- Rollen bestämmer vad användaren får göra -- inte vem hen är. Identitet och inloggning sköts av HuleEdu.
- Ändringar slår igenom nästa gång användaren laddar om sidan.

Micro-help:

- Roll: Vad användaren får göra i Skriptoteket. Ändringen sparas direkt.
- Spärra: Hindrar användaren från att logga in. Hävs genom att sätta rollen tillbaka.

Approval notes:

- Endast synligt för superanvändare. Gör tydligt att roller är lokala.

### Åtkomst saknas

State: approved
Routes:

- `forbidden`

Drawer copy:

- Den här sidan kräver en roll eller behörighet som ditt konto inte har just nu.
- Det är inget fel på dig -- det kan handla om att du behöver tilldelas en roll eller logga in med rätt konto.
- Vet du inte vem du ska fråga? Börja med din skoladministratör.

Micro-help:

- Till startsidan: Tar dig tillbaka till något du garanterat har åtkomst till.

Approval notes:

- Undvik formuleringar som skuldbelägger användaren.

### Sidan hittades inte

State: approved
Routes:

- `not-found`
- `public-app-route-recovery`

Drawer copy:

- Adressen leder inte någonstans just nu. Kanske har länken blivit gammal, eller så har något flyttats.
- Prova att gå till startsidan och leta dig fram därifrån, eller använd sökfältet.
- Kom du hit via en länk från någon annan? Hör av dig till den som delade länken -- den behöver förmodligen uppdateras.

Micro-help:

- Till startsidan: Tar dig till Skriptotekets översikt.
- Sök: Hjälper dig att hitta verktyg eller appar om du minns namnet.

Approval notes:

- Samma copy fungerar för både 404 och återställning av publika app-länkar.

## First Signoff Batch

The first copy review batch should cover the current missing and high-traffic
surfaces before component work:

- auth lifecycle and provisioning
- catalog and tool run/result
- profile, vault, and my runs
- contributor suggestion form
- admin suggestion/tools/editor surfaces
- route recovery and forbidden access

Klassrumskartan mode help is already sourced from
`docs/guides/guide-klassrumskartan-kom-igang.md`; changes to that wording should
continue through the guide and generator rather than through hand-written topic
components.
