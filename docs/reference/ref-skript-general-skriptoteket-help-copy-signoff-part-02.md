---
type: reference
id: REF-SKRIPT-GENERAL-skriptoteket-help-copy-signoff-PART-02
title: Skriptoteket help copy signoff — part 02
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
root: REF-SKRIPT-GENERAL-skriptoteket-help-copy-signoff
part: 2
---

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

### First Signoff Batch

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

## Decisions And Interpretation

No implementation authority is created by this reference.
