# Skapa AI-verktyg i Skriptoteket – Så här gör du

Välkommen till Skriptoteket! Denna guide är till för dig som vill skapa egna pedagogiska verktyg med hjälp av AI, utan att behöva kunna programmera.

## Konceptet: Från idé till verktyg

I Skriptoteket bygger du verktyg genom att beskriva vad de ska göra för en AI. Du behöver inte skriva kod själv, men du behöver förstå de tre byggstenarna i ett verktyg:

1. **Input:** Vad ska användaren mata in? (t.ex. en elevtext, ett ämne, en årskurs).

2. **Arbetsuppgift:** Vad ska verktyget göra med informationen? (t.ex. "hitta stavfel", "ge förslag på lektionsplanering").

3. **Output:** Hur ska svaret visas? (t.ex. en lista, en tabell, en formatterad text).

## Steg-för-steg: Skapa ditt första verktyg

### 1. Skapa ett nytt verktyg

1. Logga in i Skriptoteket.
2. Gå till **Admin** i menyn och välj **Verktyg**.
3. Klicka på knappen **"Skapa nytt verktyg"**.
4. Ge verktyget en **Titel** (t.ex. "Lektionsplanerare") och en kort **Beskrivning**.
5. Klicka på **Skapa**. Du hamnar nu i **Verktygseditorn**.

### 2. Hitta runt i Editorn

Editorn är din verkstad. Den består av flera delar:

* **Källkod (Mitten):** Här ligger själva "motorn" (Python-koden).
* **Inställningar & Input (Höger):** Här bestämmer du vilka knappar och fält användaren ska se.
* **Förhandsgranskning (Botten/Höger):** Här testkör du ditt verktyg ("Sandbox").
* **Redigeringsförslag (Vänster/Botten):** Din inbyggda AI-assistent för att göra ändringar.

### 3. Ta hjälp av en extern AI (ChatGPT/Claude)

För att få en flygande start använder vi en extern AI-tjänst (som ChatGPT eller Claude) för att skriva den första versionen av koden.

1. Öppna ChatGPT eller Claude i en ny flik.
2. Kopiera **System-prompten** (se nedan) och klistra in den först i chatten. Detta lär AI:n hur Skriptoteket fungerar.
3. Använd **Mall för verktygsbeskrivning** (se nedan) för att beskriva ditt verktyg. Klistra in beskrivningen i chatten.
4. AI:n kommer nu att generera tre delar:
    * `source_code` (Python)
    * `input_schema` (JSON)
    * `settings_schema` (JSON)

### 4. Klistra in och kör

1. Gå tillbaka till Skriptoteket-editorn.
2. Kopiera koden från AI:n och klistra in i respektive fält:
    * Python-koden -> **Källkod**
    * Input-schemat -> **Input Schema** (under fliken Schema)
    * Inställnings-schemat -> **Inställningar Schema**
3. Klicka på **"Spara"** (diskett-ikonen).
4. Klicka på **"Kör"** i förhandsgranskningen för att testa verktyget direkt.

### 5. Finjustera med inbyggd AI

Om du vill ändra något litet (t.ex. "Gör knappen blå" eller "Lägg till ett fält för årskurs"), använd den inbyggda assistenten i Skriptoteket:

1. Hitta panelen **"Redigeringsförslag"**.
2. Skriv vad du vill ändra: *"Lägg till en dropdown-meny för att välja årskurs 1-9."*
3. Klicka på **"Föreslå ändring"**.
4. Om förslaget ser bra ut, klicka på **"Verkställ"**.

### 6. Publicera och Administrera

När du är nöjd med ditt verktyg i "Sandboxen" är det dags att göra det tillgängligt för andra.

### 4. Utvecklarverktyg (DX)

### Toolkit (`skriptoteket_toolkit.py`)

För att göra det enkelt att skriva verktyg finns ett inbyggt bibliotek. Använd alltid detta istället för att läsa miljövariabler direkt.

```python
from skriptoteket_toolkit import get_action_parts, read_inputs, read_settings

# Hämta inputs (antingen från start eller från en "action")
action_id, action_input, state = get_action_parts()
inputs = action_input if action_id else read_inputs()

# Läs inställningar (settings)
settings = read_settings()
```

### Avancerad retur (Contract V3)

Du kan returnera mer än bara text. Om du returnerar ett `dict` kan du styra status, nästa steg och tillstånd.

```python
def run_tool(input_dir, output_dir):
    return {
        "outputs": [
            {"kind": "markdown", "markdown": "# Analys klar"},
            {"kind": "notice", "level": "info", "message": "Resultat sparat."}
        ],
        "state_update": {"kind": "set", "state": {"steg": 2}},
        "next_actions": [
            {"action_id": "step_2", "label": "Gå vidare", "primary": True}
        ]
    }
```

---

## Resurser för AI-assistenten

Här är de texter du behöver för att instruera en extern AI (som ChatGPT).

### System-prompt (Kopiera och klistra in detta FÖRST)

```text
Du är en expertutvecklare för plattformen "Skriptoteket". Din uppgift är att skriva kompletta, fungerande verktyg i
Python baserat på användarens beskrivning.

Du ska alltid generera exakt tre kodblock, i denna ordning:
1) `source_code` (Python 3.13)
2) `input_schema` (JSON)
3) `settings_schema` (JSON)

## Runner-kontrakt (Contract V3)

- Entrypoint: `def run_tool(input_dir: str, output_dir: str) -> dict | str`
- Ingen nätverksåtkomst (Docker kör med `--network none`).
- Filsystemet är read-only utom `/work` och `/tmp`.
- Använd `skriptoteket_toolkit` för att läsa inputs och settings.
- `state_update` semantics: `{"kind": "no_change|clear|set", "state": {...}}`.
- Returnera en `str` (HTML) eller en `dict` med `outputs`, `next_actions`, `state_update`.

## Output-kontrakt (UI Elements)

`run_tool` ska returnera:

```python
{
  "outputs": [...],      # UI-element
  "next_actions": [...], # Knappar för nästa steg
  "state_update": {"kind": "no_change"} # Hantering av sessionstillstånd
}
```

**UI-element** (läggs i `outputs`):

* notice: `{"kind":"notice","level":"info|warning|error","message":"..."}`
* markdown: `{"kind":"markdown","markdown":"..."}`
* table: `{"kind":"table","title":"...", "columns":[{"key":"k","label":"K"}], "rows":[{"k":"v"}]}`
* json: `{"kind":"json","title":"...", "value": {...}}`
* html_sandboxed: `{"kind":"html_sandboxed","html":"<p>...</p>"}`
* vega_lite: `{"kind":"vega_lite","spec": {...}}`

## Exempel på svar (tre block)

```python
# 1. source_code
import json
import os

def run_tool(input_dir: str, output_dir: str) -> dict:
    inputs_raw = os.environ.get("SKRIPTOTEKET_INPUTS", "")
    inputs = json.loads(inputs_raw) if inputs_raw.strip() else {}
    name = inputs.get("namn", "Okänd")

    return {
        "outputs": [{"kind": "notice", "level": "info", "message": f"Hej {name}!"}],
        "next_actions": [],
        "state": None,
    }
```

```json
// 2. input_schema
[
  {"kind": "string", "name": "namn", "label": "Ditt namn"}
]
```

```json
// 3. settings_schema
[]
```

### Mall för verktygsbeskrivning (Fyll i och ge till AI:n)

Använd denna mall för att beskriva din idé så att AI:n förstår exakt vad du vill ha.

```text
**Verktygets namn:** (t.ex. Beröm-generatorn)

**Input (Vad ska användaren mata in?):**
* (t.ex. En textruta för elevens namn)
* (t.ex. En dropdown-meny för "Typ av uppgift" med valen: Uppsats, Prov, Muntligt)

**Arbetsuppgift (Vad ska verktyget göra?):**
* (t.ex. Skriv en kort, uppmuntrande kommentar till eleven baserat på uppgiftstyp. Kommentaren ska vara personlig och nämna namnet.)

**Output (Hur ska svaret se ut?):**
* (t.ex. Visa kommentaren som Markdown-text.)
```

---

## Del 3: Receptsamling – Exempel från verkligheten

Här är ett exempel på hur ett riktigt behov i skolan kan översättas till en AI-prompt.

### Exempel: "Kontaktlistor från IST till Outlook"

**Problem:** Du har tagit ut en klasslista från IST som en Excel-fil. Den är rörig och innehåller massor av kolumner. Du vill bara ha alla vårdnadshavares e-postadresser i en lista, separerade med semikolon, så att du kan klistra in dem i "Hemlig kopia" (BCC) i Outlook.

**Så här fyller du i mallen för att skapa verktyget:**

```text
**Verktygets namn:** IST Kontakt-fixare

**Input:**
* En filuppladdning (`file`) som accepterar `.xlsx` och `.csv`. Etikett: "Ladda upp klasslista från IST".

**Arbetsuppgift:**
1. Läs filen (Excel eller CSV).
2. Leta igenom alla kolumnrubriker. Hitta de som verkar innehålla e-postadresser (sök efter ord som "e-post", "email", "mail", "vårdnadshavare").
3. Extrahera alla e-postadresser från dessa kolumner.
4. Ta bort dubbletter (samma adress ska bara finnas med en gång).
5. Sortera adresserna i bokstavsordning.
6. Skapa en enda lång textsträng där alla adresser skiljs åt med semikolon (;). Detta krävs för Outlook.

**Output:**
* Visa resultatet (den semikolon-separerade listan) som `{"kind":"markdown", ...}` så att jag enkelt kan kopiera den.
* Visa även en tabell (`{"kind":"table", ...}`) med två kolumner: "Namn på kolumn i Excel" och "Antal adresser funna", så jag ser att den hittat rätt.
```

**Tips:** Om AI:n inte hittar rätt kolumner direkt, be den i "Redigeringsförslag" att: *"Lägg till sökordet 'kontakt' när du letar efter kolumner."*

---

### Exempel: "Gruppgeneratorn"

**Problem:** Du har en klasslista och vill snabbt skapa elevgrupper. Du vill också återanvända en klass utan att ladda upp filen varje gång, och ge varje gruppindelning ett namn.

**Så här fyller du i mallen för att skapa verktyget:**

```text
**Verktygets namn:** Gruppgeneratorn

**Input:**
* Filuppladdning (`file`) som accepterar `.csv` och `.xlsx` (valfri om klass finns i settings).
* Ett heltalsfält (`integer`) för gruppstorlek.
* Ett textfält (`string`) för klassnamn.
* Ett textfält (`string`) för namn på gruppindelningen.
* Ett textfält (`text`) för tidigare grupper (valfritt).

**Arbetsuppgift:**
1. Vid första körning: visa status (uppladdad fil eller sparade klasser) och returnera `next_actions`.
2. Vid action-körning: läs elevnamn från CSV/XLSX eller sparad klass.
3. Rensa dubbletter och tomma rader.
4. Skapa grupper med vald storlek.
5. Om tidigare grupper finns, försök minimera upprepade par.
6. Skapa en artefakt (textfil) med grupperna.

**Output:**
* Visa grupperna i en tabell.
* Visa en kort sammanfattning (antal elever, gruppstorlek, antal grupper).
* Returnera `next_actions` så användaren kan generera igen utan ny uppladdning.
* Visa en JSON-blocket med “Sparade klasser (JSON)” om fil laddats upp (så att användaren kan spara klassen).
```

**Settings som behövs (Sparade klasser):**

I settings sparar du klasserna som JSON:

```json
{
  "7A": ["Anna Andersson", "Bo Berg", "Cecilia Carlsson"],
  "7B": ["Daniel Dahl", "Eva Ek", "Filip Fors"]
}
```

**Tips:** Om du vill undvika upprepade par, klistra in tidigare grupper som JSON:

```json
[
  ["Anna Andersson", "Bo Berg", "Cecilia Carlsson"],
  ["Daniel Dahl", "Eva Ek", "Filip Fors"]
]
```

---

### Exempel: "Lix-räknaren"

Här är ett exempel på hur du kan fylla i mallen för ett verktyg som räknar LIX (läsbarhetsindex).

**Verktygets namn:** Lix-räknaren

**Input:**

* Ett stort textfält (`text`) med etiketten "Klistra in text här".

**Arbetsuppgift:**

1. Räkna antal ord.
2. Räkna antal meningar.
3. Räkna antal långa ord (över 6 bokstäver).
4. Beräkna LIX = (antal ord / antal meningar) + (antal långa ord * 100 / antal ord).
5. Klassificera texten (t.ex. < 30 = Mycket lättläst, > 60 = Mycket svår).

**Output:**

* Visa LIX-värdet och klassificeringen som ett `notice`-output (`{"kind":"notice", ...}`).
* Visa detaljerad statistik (antal ord, meningar, etc.) som en `table` (`{"kind":"table", ...}`).
