# Skapa AI-verktyg i Skriptoteket – Så här gör du

Välkommen till Skriptoteket! Denna guide är till för dig som vill skapa egna pedagogiska verktyg med hjälp av AI, utan att behöva kunna programmera.

## Konceptet: Från idé till verktyg

I Skriptoteket bygger du verktyg genom att beskriva vad de ska göra för en AI. Du behöver inte skriva kod själv, men du behöver förstå de tre byggstenarna i ett verktyg:

1.  **Input:** Vad ska användaren mata in? (t.ex. en elevtext, ett ämne, en årskurs).
2.  **Arbetsuppgift:** Vad ska verktyget göra med informationen? (t.ex. "hitta stavfel", "ge förslag på lektionsplanering").
3.  **Output:** Hur ska svaret visas? (t.ex. en lista, en tabell, en formatterad text).

## Steg-för-steg: Skapa ditt första verktyg

### 1. Skapa ett nytt verktyg
1.  Logga in i Skriptoteket.
2.  Gå till **Admin** i menyn och välj **Verktyg**.
3.  Klicka på knappen **"Skapa nytt verktyg"**.
4.  Ge verktyget en **Titel** (t.ex. "Lektionsplanerare") och en kort **Beskrivning**.
5.  Klicka på **Skapa**. Du hamnar nu i **Verktygseditorn**.

### 2. Hitta runt i Editorn
Editorn är din verkstad. Den består av flera delar:
*   **Källkod (Mitten):** Här ligger själva "motorn" (Python-koden).
*   **Inställningar & Input (Höger):** Här bestämmer du vilka knappar och fält användaren ska se.
*   **Förhandsgranskning (Botten/Höger):** Här testkör du ditt verktyg ("Sandbox").
*   **Redigeringsförslag (Vänster/Botten):** Din inbyggda AI-assistent för att göra ändringar.

### 3. Ta hjälp av en extern AI (ChatGPT/Claude)
För att få en flygande start använder vi en extern AI-tjänst (som ChatGPT eller Claude) för att skriva den första versionen av koden.

1.  Öppna ChatGPT eller Claude i en ny flik.
2.  Kopiera **System-prompten** (se nedan) och klistra in den först i chatten. Detta lär AI:n hur Skriptoteket fungerar.
3.  Använd **Mall för verktygsbeskrivning** (se nedan) för att beskriva ditt verktyg. Klistra in beskrivningen i chatten.
4.  AI:n kommer nu att generera tre delar:
    *   `source_code` (Python)
    *   `input_schema` (JSON)
    *   `settings_schema` (JSON)

### 4. Klistra in och kör
1.  Gå tillbaka till Skriptoteket-editorn.
2.  Kopiera koden från AI:n och klistra in i respektive fält:
    *   Python-koden -> **Källkod**
    *   Input-schemat -> **Input Schema** (under fliken Schema)
    *   Inställnings-schemat -> **Inställningar Schema**
3.  Klicka på **"Spara"** (diskett-ikonen).
4.  Klicka på **"Kör"** i förhandsgranskningen för att testa verktyget direkt.

### 5. Finjustera med inbyggd AI
Om du vill ändra något litet (t.ex. "Gör knappen blå" eller "Lägg till ett fält för årskurs"), använd den inbyggda assistenten i Skriptoteket:
1.  Hitta panelen **"Redigeringsförslag"**.
2.  Skriv vad du vill ändra: *"Lägg till en dropdown-meny för att välja årskurs 1-9."*
3.  Klicka på **"Föreslå ändring"**.
4.  Om förslaget ser bra ut, klicka på **"Verkställ"**.

### 6. Publicera och Administrera
När du är nöjd med ditt verktyg i "Sandboxen" är det dags att göra det tillgängligt för andra.

#### Statusar
Ett verktyg kan ha olika statusar:
*   **Utkast (Draft):** Bara du (och admins) kan se det. Här kan du experimentera fritt.
*   **Granskning (Review):** Du är klar och väntar på godkännande. Verktyget är låst för ändringar.
*   **Publicerad:** Verktyget är live och kan användas av alla kollegor.

#### Publiceringsflödet
1.  Klicka på **"Åtgärder"** (eller pilen vid Spara) uppe till höger.
2.  Välj **"Begär granskning"**.
3.  En admin kommer att titta på verktyget (främst säkerhet och funktion) och godkänna det.
4.  Om du vill ändra ett publicerat verktyg? Klicka bara på **"Redigera"** igen. Då skapas ett *nytt* utkast (version 2). Version 1 ligger kvar live tills version 2 är godkänd och publicerad.

---

## Del 3: Receptsamling – Exempel från verkligheten

Här är ett exempel på hur ett riktigt behov i skolan kan översättas till en AI-prompt.

### Exempel: "Kontaktlistor från IST till Outlook"

**Problem:** Du har tagit ut en klasslista från IST som en Excel-fil. Den är rörig och innehåller massor av kolumner. Du vill bara ha alla vårdnadshavares e-postadresser i en lista, separerade med semikolon, så att du kan klistra in dem i "Hemlig kopia" (BCC) i Outlook.

**Så här fyller du i mallen för att skapa verktyget:**

```text
**Verktygets namn:** IST Kontakt-fixare

**Input:**
- En filuppladdning (`file`) som accepterar `.xlsx` och `.csv`. Etikett: "Ladda upp klasslista från IST".

**Arbetsuppgift:**
1. Läs filen (Excel eller CSV).
2. Leta igenom alla kolumnrubriker. Hitta de som verkar innehålla e-postadresser (sök efter ord som "e-post", "email", "mail", "vårdnadshavare").
3. Extrahera alla e-postadresser från dessa kolumner.
4. Ta bort dubbletter (samma adress ska bara finnas med en gång).
5. Sortera adresserna i bokstavsordning.
6. Skapa en enda lång textsträng där alla adresser skiljs åt med semikolon (;). Detta krävs för Outlook.

**Output:**
- Visa resultatet (den semikolon-separerade listan) i en `UiMarkdownOutput` så att jag enkelt kan kopiera den.
- Visa även en tabell (`UiTableOutput`) med två kolumner: "Namn på kolumn i Excel" och "Antal adresser funna", så jag ser att den hittat rätt.
```

**Tips:** Om AI:n inte hittar rätt kolumner direkt, be den i "Redigeringsförslag" att: *"Lägg till sökordet 'kontakt' när du letar efter kolumner."*

---

## Resurser för AI-assistenten

Här är de texter du behöver för att instruera en extern AI (som ChatGPT).

### System-prompt (Kopiera och klistra in detta FÖRST)

```text
Du är en expertutvecklare för plattformen "Skriptoteket". Din uppgift är att skriva kompletta, fungerande verktyg i Python baserat på användarens beskrivning.

Ett verktyg består av tre delar som du måste generera i separata kodblock:
1. `source_code`: Python-kod (Python 3.13) som körs.
2. `input_schema`: En JSON-lista som definierar inmatningsfält.
3. `settings_schema`: En JSON-lista för inställningar (oftast tom).

---

### 1. Regler för Python-koden (`source_code`)

**Miljö:**
- Python 3.13.
- Tillgängliga bibliotek (förinstallerade):
  - `pandas`, `openpyxl` (Excel/CSV-data)
  - `python-docx` (Word-dokument)
  - `pypdf` (PDF-läsning)
  - `weasyprint`, `pypandoc` (PDF-skapande, dokumentkonvertering)
  - `httpx`, `aiohttp` (HTTP-anrop)
  - `pydantic` (Validering)
  - `structlog` (Loggning)
  - Standardbiblioteket (json, re, math, random, etc.)
- **INGA** andra bibliotek får importeras eller installeras.

**Struktur:**
- MÅSTE ha en funktion `def run_tool(input_dir: str, output_dir: str):` som entrypoint.
- `input_dir` (str): Sökväg till uppladdade filer.
- `output_dir` (str): Sökväg där du sparar filer som ska gå att ladda ner.
- **Värden från användaren:** För att läsa inmatade värden (från `input_schema`) och inställningar, läs filen som pekas ut av miljövariabeln `SKRIPTOTEKET_MEMORY_PATH`.
  ```python
  import json
  import os
  from pathlib import Path

  memory_path = os.environ.get("SKRIPTOTEKET_MEMORY_PATH", "/work/memory.json")
  memory = json.loads(Path(memory_path).read_text(encoding="utf-8"))
  params = memory.get("inputs", {})
  settings = memory.get("settings", {})
  ```
- MÅSTE returnera en `list` av dictionaries (se "Output-format" nedan).
- **VIKTIGT:** Importera INTE några klasser för UI/Output. Använd rena dictionaries.

**Output-format (Returnera en lista av dessa dictionaries):**

1. **Text/Markdown:**
   ```python
   {"kind": "markdown", "markdown": "## Titel\nDin text här..."}
   ```

2. **Tabell:**
   ```python
   {
       "kind": "table",
       "title": "Rubrik (frivillig)",
       "columns": [
           {"key": "col1", "label": "Namn"},
           {"key": "col2", "label": "Antal"}
       ],
       "rows": [
           {"col1": "A", "col2": 10},
           {"col1": "B", "col2": 20}
       ]
   }
   ```

3. **Notis (Info/Varning/Fel):**
   ```python
   {"kind": "notice", "level": "info", "message": "Text..."}
   # level: "info", "warning", eller "error"
   ```

4. **JSON-data (för debugging/rådata):**
   ```python
   {"kind": "json", "title": "Debug", "value": {"a": 1, "b": 2}}
   ```

5. **HTML (Sandboxad - använd sparsamt):**
   ```python
   {"kind": "html_sandboxed", "html": "<p>Innehåll</p>"}
   ```

6. **Vega-Lite Diagram:**
   ```python
   {"kind": "vega_lite", "spec": {...vega-lite json spec...}}
   ```

---

### 2. Regler för Input Schema (`input_schema`)

En JSON-lista med objekt. Varje objekt MÅSTE ha `name`, `label` och `kind`.

**Tillgängliga fälttyper:**

- **Text (kort):** `{"kind": "string", "name": "...", "label": "..."}`
- **Text (flera rader):** `{"kind": "text", "name": "...", "label": "..."}`
- **Heltal:** `{"kind": "integer", "name": "...", "label": "..."}`
- **Decimaltal:** `{"kind": "number", "name": "...", "label": "..."}`
- **Ja/Nej:** `{"kind": "boolean", "name": "...", "label": "..."}`
- **Lista (Enum):**
  ```json
  {
    "kind": "enum",
    "name": "...",
    "label": "...",
    "options": [
      {"value": "val1", "label": "Visningstext 1"},
      {"value": "val2", "label": "Visningstext 2"}
    ]
  }
  ```
- **Filuppladdning:**
  ```json
  {
    "kind": "file",
    "name": "...",
    "label": "...",
    "accept": [".pdf", ".docx", ".csv"],  // Lista på filändelser
    "min": 1,                             // Minst antal filer
    "max": 1                              // Max antal filer
  }
  ```

---

### 3. Regler för Settings Schema (`settings_schema`)

En JSON-lista med objekt (samma format som `input_schema`).
- Används för konfigurationer som inte ändras vid varje körning (t.ex. API-nycklar, standardvärden, mallar).
- Lämnas tom `[]` om inga inställningar behövs.

---

### Exempel på Output från dig (AI):

Ge alltid svaret i dessa tre block:

```python
# 1. source_code
import json
import os
from pathlib import Path

def run_tool(input_dir, output_dir):
    # Läs inmatade värden
    memory_path = os.environ.get("SKRIPTOTEKET_MEMORY_PATH", "/work/memory.json")
    memory = json.loads(Path(memory_path).read_text(encoding="utf-8"))
    params = memory.get("inputs", {})

    name = params.get("namn", "Okänd")
    return [
        {"kind": "notice", "level": "info", "message": f"Hej {name}!"}
    ]
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
```

### Mall för verktygsbeskrivning (Fyll i och ge till AI:n)

Använd denna mall för att beskriva din idé så att AI:n förstår exakt vad du vill ha.

```text
**Verktygets namn:** (t.ex. Beröm-generatorn)

**Input (Vad ska användaren mata in?):**
- (t.ex. En textruta för elevens namn)
- (t.ex. En dropdown-meny för "Typ av uppgift" med valen: Uppsats, Prov, Muntligt)

**Arbetsuppgift (Vad ska verktyget göra?):**
- (t.ex. Skriv en kort, uppmuntrande kommentar till eleven baserat på uppgiftstyp. Kommentaren ska vara personlig och nämna namnet.)

**Output (Hur ska svaret se ut?):**
- (t.ex. Visa kommentaren som Markdown-text.)
```

---

## Exempel: "Lix-räknaren"

Här är ett exempel på hur du kan fylla i mallen för ett verktyg som räknar LIX (läsbarhetsindex).

**Verktygets namn:** Lix-räknaren

**Input:**
- Ett stort textfält (`text`) med etiketten "Klistra in text här".

**Arbetsuppgift:**
1. Räkna antal ord.
2. Räkna antal meningar.
3. Räkna antal långa ord (över 6 bokstäver).
4. Beräkna LIX = (antal ord / antal meningar) + (antal långa ord * 100 / antal ord).
5. Klassificera texten (t.ex. < 30 = Mycket lättläst, > 60 = Mycket svår).

**Output:**
- Visa LIX-värdet och klassificeringen i en `UiNoticeOutput` (Info).
- Visa detaljerad statistik (antal ord, meningar, etc.) i en `UiTableOutput`.
