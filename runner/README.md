# Runner Helpers

Moduler tillgängliga för verktygs-skript i körmiljön.

## pdf_helper

Renderar HTML till PDF med WeasyPrint.

```python
from pdf_helper import save_as_pdf

pdf_path = save_as_pdf(html_content, output_dir, "rapport.pdf")
```

**Parametrar:**

- `html` - HTML-sträng att rendera
- `output_dir` - Katalog för artefakter (från `run_tool`-signaturen)
- `filename` - Relativ sökväg, måste sluta med `.pdf`

**Returnerar:** Absolut sökväg till skapad PDF.

## tool_errors

Undantag för användarvänliga felmeddelanden.

```python
from tool_errors import ToolUserError

raise ToolUserError("Filtypen stöds inte.")
```

Meddelandet visas som `error_summary` utan stacktrace.

---

Se `docs/reference/ref-ai-script-generation-kb.md` för fullständig dokumentation.
