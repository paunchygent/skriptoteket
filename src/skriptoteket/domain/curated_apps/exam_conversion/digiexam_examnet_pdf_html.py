"""Exam.net PDF renderer document HTML assembly.

Purpose:
    Assemble full HTML documents for the Exam.net-oriented PDF renderer from
    already-rendered item sections.

Relationships:
    - Consumes item sections from `domain.digiexam_examnet_pdf_items`.
    - Feeds the in-process Exam.net PDF renderer seam through the thin
      document coordinator.
"""

from __future__ import annotations

from html import escape

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfItemRender,
)


def build_examnet_pdf_html(
    *,
    source_filename: str,
    items: tuple[DigiExamExamNetPdfItemRender, ...],
    header_lines: tuple[str, ...] = (),
) -> str:
    """Build the complete HTML document rendered by WeasyPrint."""

    header_html = ""
    if header_lines:
        title, *details = header_lines
        detail_html = "".join(f"<p>{escape(line)}</p>" for line in details)
        header_html = f'<header class="exam-header"><h1>{escape(title)}</h1>{detail_html}</header>'
    item_html = "\n".join(item.html for item in items)
    return f"""<!doctype html>
<html lang="sv">
<head>
<meta charset="utf-8">
<title>{escape(source_filename)} Exam.net PDF Import</title>
<style>
@page {{
  size: A4;
  margin: 18mm 16mm;
}}
body {{
  color: #111;
  font-family: Arial, sans-serif;
  font-size: 12pt;
  line-height: 1.35;
}}
.exam-item {{
  break-inside: avoid;
  margin: 0 0 18pt;
}}
h2 {{
  font-size: 15pt;
  margin: 0 0 6pt;
}}
p {{
  margin: 0 0 6pt;
}}
.points,
.item-type,
.answer-key {{
  font-weight: 700;
}}
.prompt {{
  margin: 8pt 0;
}}
.prompt-image {{
  display: block;
  margin: 6pt 0;
  max-width: 100%;
}}
.gap-placeholder {{
  border-bottom: 1pt solid #111;
  display: inline-block;
  min-width: 42pt;
  text-align: center;
}}
.options {{
  margin: 8pt 0 8pt 18pt;
}}
.options p {{
  margin: 0 0 5pt;
}}
.parent-instruction {{
  font-weight: 700;
  margin: 0 0 14pt;
}}
.matching-grid {{
  border-collapse: collapse;
  margin: 8pt 0;
  width: 100%;
  table-layout: fixed;
}}
.matching-grid th,
.matching-grid td {{
  border: 0.5pt solid #111;
  padding: 5pt;
  overflow-wrap: anywhere;
}}
.matching-grid td {{
  text-align: center;
}}
.matching-grid th[scope="row"] {{
  text-align: left;
}}
.number-box {{
  border: 1pt solid #111;
  display: inline-block;
  width: 24pt;
  height: 16pt;
  vertical-align: middle;
}}
.tick-box {{
  border: 1pt solid #111;
  display: inline-block;
  width: 12pt;
  height: 12pt;
  line-height: 12pt;
  vertical-align: middle;
}}
</style>
</head>
<body>
<main>
{header_html}
{item_html}
</main>
</body>
</html>
"""
