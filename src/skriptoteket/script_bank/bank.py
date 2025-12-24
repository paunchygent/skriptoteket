from __future__ import annotations

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
    ),
    ScriptBankEntry(
        slug="html-to-pdf",
        title="HTML → PDF-konverterare",
        summary=(
            "Omvandlar en uppladdad HTML-fil till en PDF. Stöder externa assets (CSS/bilder) "
            "om de laddas upp tillsammans och refereras med relativa filnamn."
        ),
        usage_instructions="""\
## Enkel konvertering

1. Klicka på **Välj filer** och välj din HTML-fil (.html eller .htm).
2. Klicka **Kör**.
3. Ladda ner den genererade PDF-filen.

## Med bilder och CSS

Om din HTML-fil använder externa CSS-filer eller bilder:

1. Välj **alla filer** (HTML, CSS, bilder) i samma filväljardialog.
2. Se till att HTML-filen refererar till resurserna med **relativa filnamn**, t.ex.:
   - `<link rel="stylesheet" href="style.css">`
   - `<img src="bild.png">`
3. Klicka **Kör** - verktyget hittar automatiskt resurserna.

## Tips

- Flera HTML-filer? Alla konverteras till separata PDF:er.
- Bildformat: PNG, JPG, GIF och SVG stöds.
- CSS: De flesta webbstandarder fungerar, men avancerade layouter kan skilja sig något.""",
        profession_slugs=["gemensamt"],
        category_slugs=["ovrigt"],
        source_filename="html_to_pdf.py",
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
    ),
]
