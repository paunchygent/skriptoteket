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
        profession_slugs=["gemensamt"],
        category_slugs=["ovrigt"],
        source_filename="demo_next_actions.py",
    ),
]
