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
]
