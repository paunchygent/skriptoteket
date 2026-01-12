from __future__ import annotations

from skriptoteket.domain.scripting.tool_inputs import (
    ToolInputBooleanField,
    ToolInputEnumField,
    ToolInputEnumOption,
    ToolInputFileField,
    ToolInputStringField,
)
from skriptoteket.domain.scripting.ui.contract_v2 import UiStringField

from .models import ScriptBankEntry

SCRIPT_BANK: list[ScriptBankEntry] = [
    ScriptBankEntry(
        slug="ist-vh-mejl-bcc",
        title="IST: Extrahera vårdnadshavares mejladresser (BCC)",
        summary=(
            "Extraherar vårdnadshavares e‑postadresser ur en klasslista (CSV/XLSX) och "
            "returnerar en semikolonseparerad lista som passar Outlook BCC."
        ),
        usage_instructions="""\
## Förbered din fil

1. Exportera klasslistor från IST (eller motsvarande) som CSV eller Excel (XLSX).
2. Se till att filen har en **rubrikrad** - verktyget letar efter kolumner med
   namn som "e-post", "mejl", "vårdnadshavare" m.fl.
3. Du kan ladda upp flera filer samtidigt - verktyget slår ihop alla unika adresser.

## Kör verktyget

1. Klicka på **Välj filer** och välj dina klasslistor.
2. Klicka **Kör**.
3. Resultatet visar hur många unika adresser som hittades.

## Använd resultatet

1. Ladda ner textfilen som skapas (t.ex. `emails_20250101_123456.txt`).
2. Öppna filen och kopiera hela innehållet.
3. I Outlook: skapa ett nytt mejl och klistra in adressen i **BCC-fältet**.

Adresserna är semikolonseparerade och fungerar direkt i Outlook.""",
        profession_slugs=["larare"],
        category_slugs=["administration"],
        source_filename="ist_vh_mejl_bcc.py",
        input_schema=[
            ToolInputFileField(name="files", label="Filer", min=1, max=10),
        ],
    ),
    ScriptBankEntry(
        slug="filkonverterare-markdown-md-till-word-docx",
        title="Filkonverterare: Markdown (.md) till Word (.docx)",
        summary=(
            "Konverterar 1–10 uppladdade Markdown-filer (.md) till Word-dokument (.docx) "
            "med valbar formateringsprofil."
        ),
        usage_instructions="""\
## Så här använder du verktyget

1. Ladda upp en eller flera Markdown-filer (`.md` eller `.markdown`).
2. Välj **Formateringsmall**:
   - **Standard** (modern standardstil),
   - **Print (svartvit)** (utan färgaccenter),
   - **Print (färg)** (diskreta färgaccenter).
3. Valfritt: slå på **Jämförelse** om du vill få en extra variant.
   - Välj **Jämförelseprofil** (t.ex. Print svartvit).
   - Välj **Jämförelseomfattning**: endast första filen eller alla filer.
4. Klicka **Kör**.

## Resultat

- Du får en `.docx` per fil och per profil.
- Filnamn får ett suffix som visar profilen, t.ex. `__standard` eller `__print_bw`.
- Resultattabellen visar status och filstorlek.

## Tips

- Vid stora batcher: välj **Endast första filen** för jämförelse om du vill spara tid.
- Om du behöver två varianter för utskrift, använd **Jämförelse** med en annan profil.
""",
        profession_slugs=["gemensamt"],
        category_slugs=["administration", "ovrigt"],
        source_filename="markdown_to_docx.py",
        input_schema=[
            ToolInputFileField(
                name="markdown_files",
                label="Markdown-filer (.md)",
                accept=[".md", ".markdown"],
                min=1,
                max=10,
            ),
            ToolInputEnumField(
                name="profile",
                label="Formateringsmall",
                options=[
                    ToolInputEnumOption(
                        value="standard",
                        label="Standard – modern standardstil med tydliga rubriker",
                    ),
                    ToolInputEnumOption(
                        value="print_bw",
                        label="Print (svartvit) – utskriftsvänlig typografi utan färgaccenter",
                    ),
                    ToolInputEnumOption(
                        value="print_color",
                        label="Print (färg) – utskriftsvänlig typografi med diskreta färgaccenter",
                    ),
                ],
            ),
            ToolInputBooleanField(
                name="make_comparison",
                label="Jämförelse (generera även en alternativ profil)",
            ),
            ToolInputEnumField(
                name="comparison_profile",
                label="Jämförelseprofil",
                options=[
                    ToolInputEnumOption(value="standard", label="Standard"),
                    ToolInputEnumOption(value="print_bw", label="Print (svartvit)"),
                    ToolInputEnumOption(value="print_color", label="Print (färg)"),
                ],
            ),
            ToolInputEnumField(
                name="comparison_scope",
                label="Jämförelseomfattning",
                options=[
                    ToolInputEnumOption(value="first", label="Endast första filen"),
                    ToolInputEnumOption(value="all", label="Alla filer"),
                ],
            ),
        ],
    ),
    ScriptBankEntry(
        slug="demo-next-actions",
        title="Demo: Interaktiv körning (next_actions)",
        summary=(
            "Demoverktyg för att testa SPA-flödet: upload → outputs/artifacts → "
            "next_actions → ny körning."
        ),
        usage_instructions="""\
## Syfte

Det här är ett **demoverktyg** för att testa hur interaktiva verktyg fungerar i Skriptoteket.

## Så här gör du

1. Ladda upp valfri fil (spelar ingen roll vad).
2. Klicka **Kör**.
3. Verktyget visar knappar: "Nästa steg", "Nollställ", "Avsluta".
4. Prova att klicka på dem och se hur state sparas mellan körningar.

## Vad testas?

- **next_actions**: Verktyget kan returnera knappar som leder till nya körningar.
- **state**: Information sparas mellan körningar (stegräknare).
- **artifacts**: Varje körning skapar en textfil som kan laddas ner.""",
        profession_slugs=["gemensamt"],
        category_slugs=["ovrigt"],
        source_filename="demo_next_actions.py",
        input_schema=[
            ToolInputFileField(name="files", label="Filer", min=1, max=10),
        ],
    ),
    ScriptBankEntry(
        slug="html-to-pdf-preview",
        title="HTML → PDF med förhandsgranskning",
        summary=(
            "Förhandsgranska din HTML innan konvertering till PDF. "
            "Demonstrerar alla Skriptoteket-funktioner: preview, diagram, inställningar."
        ),
        usage_instructions="""\
## Tvåstegsprocess

Det här verktyget låter dig **förhandsgranska** din HTML innan du konverterar den till PDF.

### Steg 1: Förhandsgranska

1. Klicka på **Välj filer** och välj din HTML-fil (och eventuella CSS/bilder).
2. Klicka **Kör**.
3. Du ser en **live-förhandsgranskning** av hur din HTML ser ut.
4. Granska resultatet - ser det rätt ut?

### Steg 2: Konvertera

1. Om du är nöjd, klicka **Konvertera till PDF**.
2. Välj sidstorlek (A4 eller Letter) och orientering (stående/liggande).
3. Ladda ner den genererade PDF-filen.

### Börja om

Om förhandsgranskningen inte ser rätt ut:
1. Klicka **Börja om**.
2. Ladda upp korrigerade filer.

## Demonstrerar

Det här verktyget visar alla Skriptoteket-funktioner:
- **html_sandboxed**: Live HTML-förhandsgranskning
- **vega_lite**: Diagram över filstorlekar
- **next_actions**: Navigering mellan steg
- **settings**: Spara standardinställningar (sidstorlek, orientering)
- **state**: Spåra arbetsflödessteg""",
        profession_slugs=["gemensamt"],
        category_slugs=["ovrigt"],
        source_filename="html_to_pdf_preview.py",
        input_schema=[
            ToolInputFileField(name="files", label="Filer", min=1, max=10),
        ],
    ),
    ScriptBankEntry(
        slug="demo-regression-table",
        title="Demo: Table column order test (E2E)",
        summary="Playwright E2E test tool for table column order regression (ST-11-07).",
        profession_slugs=["gemensamt"],
        category_slugs=["ovrigt"],
        source_filename="demo_regression_table.py",
    ),
    ScriptBankEntry(
        slug="demo-settings-test",
        title="Demo: Personalized settings test (E2E)",
        summary="Playwright E2E test tool for personalized tool settings (ST-12-03).",
        profession_slugs=["gemensamt"],
        category_slugs=["ovrigt"],
        source_filename="demo_settings_test.py",
        settings_schema=[
            UiStringField(name="theme_color", label="Färgtema"),
        ],
    ),
    ScriptBankEntry(
        slug="demo-inputs",
        title="Demo: Indata utan filer (input_schema)",
        summary="Demoverktyg för ST-12-04: text/dropdown inputs utan filuppladdning.",
        profession_slugs=["gemensamt"],
        category_slugs=["ovrigt"],
        source_filename="demo_inputs.py",
        input_schema=[
            ToolInputStringField(name="title", label="Titel"),
            ToolInputEnumField(
                name="format",
                label="Format",
                options=[
                    ToolInputEnumOption(value="pdf", label="PDF"),
                    ToolInputEnumOption(value="txt", label="Text"),
                ],
            ),
        ],
    ),
    ScriptBankEntry(
        slug="demo-inputs-file",
        title="Demo: Indata + filer (input_schema)",
        summary="Demoverktyg för ST-12-04: inputs + file-fält med accept/min/max.",
        profession_slugs=["gemensamt"],
        category_slugs=["ovrigt"],
        source_filename="demo_inputs.py",
        input_schema=[
            ToolInputStringField(name="title", label="Titel"),
            ToolInputFileField(
                name="documents",
                label="Dokument",
                accept=[".txt", ".md"],
                min=1,
                max=2,
            ),
        ],
    ),
    ScriptBankEntry(
        slug="yrkesgeneratorn",
        title="Yrkesgeneratorn",
        summary=(
            "Skriv in ditt för- och efternamn så berättar verktyget vad du ska bli när du "
            "blir stor."
        ),
        profession_slugs=["gemensamt"],
        category_slugs=["ovrigt"],
        source_filename="yrkesgenerator.py",
        input_schema=[
            ToolInputStringField(
                name="full_name",
                label="Skriv in ditt för- och efternamn",
            ),
        ],
    ),
]
