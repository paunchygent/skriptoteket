"""Generate planner help sections from the getting-started guide.

Reads ``docs/guides/guide-klassrumskartan-kom-igang.md``, splits by
``## Steg`` headings, strips video annotations (``[VISA: ...]``,
``[PAUS]``, ``> TALMANUS: ...``), and writes a TypeScript module with
pre-rendered HTML per planner workspace mode.

Usage::

    pdm run generate-planner-help
"""

from __future__ import annotations

import re
from pathlib import Path

GUIDE_PATH = Path("docs/guides/guide-klassrumskartan-kom-igang.md")
OUTPUT_PATH = Path(
    "frontend/apps/skriptoteket/src/components/help/plannerHelpSections.generated.ts"
)

# Section heading → mode mapping.  Sections are matched by their ``## ``
# prefix and assigned to the first matching mode key.
SECTION_MAP: list[tuple[str, list[str]]] = [
    ("planner_overview", ["Steg 1", "Steg 2"]),
    ("planner_seating", ["Steg 3"]),
    ("planner_grouping", ["Steg 4"]),
    ("planner_rules", ["Steg 5", "Sammanfattning"]),
]

# Titles shown in the help panel header per mode.
SECTION_TITLES: dict[str, str] = {
    "planner_overview": "Översikt: klass och klassrum",
    "planner_seating": "Sittplatser",
    "planner_grouping": "Grupper",
    "planner_rules": "Regler och sammanfattning",
}

# ── markdown stripping ──────────────────────────────────────────────

_RE_VISA = re.compile(r"^\[VISA:.*?\]\s*$", re.MULTILINE)
_RE_PAUS = re.compile(r"^\[PAUS\]\s*$", re.MULTILINE)
# Match full TALMANUS blockquote blocks (first line has TALMANUS,
# continuation lines start with ``> ``).
_RE_TALMANUS = re.compile(r"^>.*TALMANUS.*$(?:\n^>.*$)*", re.MULTILINE)
_RE_HR = re.compile(r"^---+\s*$", re.MULTILINE)
# Only match YAML frontmatter at the very start of the document.
_RE_FRONTMATTER = re.compile(r"\A---\n.*?^---\n", re.MULTILINE | re.DOTALL)
_RE_BLANK_RUNS = re.compile(r"\n{3,}")


def _strip_annotations(md: str) -> str:
    """Remove video annotations and horizontal rules."""
    md = _RE_VISA.sub("", md)
    md = _RE_PAUS.sub("", md)
    md = _RE_TALMANUS.sub("", md)
    md = _RE_HR.sub("", md)
    md = _RE_BLANK_RUNS.sub("\n\n", md)
    return md.strip()


# ── markdown → HTML (minimal, no external deps) ────────────────────


def _md_to_html(md: str) -> str:
    """Convert a small subset of markdown to HTML.

    Handles headings, bold, italic, unordered/ordered lists, paragraphs,
    and tables.  Good enough for the guide's structure without pulling in
    a full markdown library.
    """
    lines = md.split("\n")
    html_parts: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Headings
        if line.startswith("### "):
            text = _inline(line[4:].strip())
            html_parts.append(f"<h4>{text}</h4>")
            i += 1
            continue
        if line.startswith("## "):
            text = _inline(line[3:].strip())
            html_parts.append(f"<h3>{text}</h3>")
            i += 1
            continue

        # Table
        if "|" in line and i + 1 < len(lines) and re.match(r"^\|[-| :]+\|$", lines[i + 1].strip()):
            table_lines: list[str] = []
            while i < len(lines) and "|" in lines[i]:
                table_lines.append(lines[i])
                i += 1
            html_parts.append(_table_to_html(table_lines))
            continue

        # Unordered list
        if re.match(r"^- ", line):
            items: list[str] = []
            while i < len(lines) and (re.match(r"^- ", lines[i]) or re.match(r"^  ", lines[i])):
                if re.match(r"^- ", lines[i]):
                    items.append(lines[i][2:].strip())
                else:
                    items[-1] += " " + lines[i].strip()
                i += 1
            li = "".join(f"<li>{_inline(item)}</li>" for item in items)
            html_parts.append(f"<ul>{li}</ul>")
            continue

        # Ordered list
        if re.match(r"^\d+\.\s", line):
            items = []
            while i < len(lines) and (
                re.match(r"^\d+\.\s", lines[i]) or re.match(r"^   ", lines[i])
            ):
                if re.match(r"^\d+\.\s", lines[i]):
                    items.append(re.sub(r"^\d+\.\s", "", lines[i]).strip())
                else:
                    items[-1] += " " + lines[i].strip()
                i += 1
            li = "".join(f"<li>{_inline(item)}</li>" for item in items)
            html_parts.append(f"<ol>{li}</ol>")
            continue

        # Blank line
        if not line.strip():
            i += 1
            continue

        # Paragraph (collect contiguous non-blank lines)
        para_lines: list[str] = []
        while i < len(lines) and lines[i].strip() and not lines[i].startswith("#"):
            para_lines.append(lines[i])
            i += 1
        if para_lines:
            text = _inline(" ".join(pl.strip() for pl in para_lines))
            html_parts.append(f"<p>{text}</p>")

    return "\n".join(html_parts)


def _inline(text: str) -> str:
    """Convert inline markdown (bold, italic, code) to HTML."""
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    return text


def _table_to_html(table_lines: list[str]) -> str:
    """Convert markdown table lines to an HTML table."""

    def cells(line: str) -> list[str]:
        return [c.strip() for c in line.strip().strip("|").split("|")]

    headers = cells(table_lines[0])
    # Skip separator line (index 1)
    rows = [cells(line) for line in table_lines[2:]]

    th = "".join(f"<th>{_inline(h)}</th>" for h in headers)
    tbody = "".join(
        "<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in row) + "</tr>" for row in rows
    )
    return f"<table><thead><tr>{th}</tr></thead><tbody>{tbody}</tbody></table>"


# ── section splitting ───────────────────────────────────────────────


def _split_sections(md: str) -> dict[str, str]:
    """Split markdown into named sections by ``##`` headings."""
    md = _RE_FRONTMATTER.sub("", md)
    parts: dict[str, str] = {}
    current_heading = "__intro__"
    current_lines: list[str] = []

    for line in md.split("\n"):
        if line.startswith("## "):
            parts[current_heading] = "\n".join(current_lines)
            current_heading = line[3:].strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    parts[current_heading] = "\n".join(current_lines)
    return parts


def _resolve_sections(raw_sections: dict[str, str]) -> dict[str, str]:
    """Map raw heading names to mode keys and render HTML."""
    result: dict[str, str] = {}

    for mode_key, heading_prefixes in SECTION_MAP:
        combined_md_parts: list[str] = []

        if mode_key == "planner_overview":
            # Include the intro (before any ## heading)
            intro = raw_sections.get("__intro__", "")
            if intro.strip():
                # Remove the top-level heading
                intro = re.sub(r"^#\s+.*$", "", intro, count=1, flags=re.MULTILINE)
                combined_md_parts.append(intro.strip())

        for heading, content in raw_sections.items():
            if heading == "__intro__":
                continue
            for prefix in heading_prefixes:
                if heading.startswith(prefix):
                    combined_md_parts.append(content.strip())
                    break

        combined_md = "\n\n".join(combined_md_parts)
        stripped = _strip_annotations(combined_md)
        html = _md_to_html(stripped)
        result[mode_key] = html

    return result


# ── output ──────────────────────────────────────────────────────────


def _write_ts(sections: dict[str, str], titles: dict[str, str]) -> None:
    """Write the generated TypeScript module."""
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "// Auto-generated from docs/guides/guide-klassrumskartan-kom-igang.md",
        "// Do not edit manually. Re-generate with: pdm run generate-planner-help",
        "",
        "export const plannerHelpTitles: Record<string, string> = {",
    ]
    for key, title in titles.items():
        lines.append(f'  {key}: "{title}",')
    lines.append("};")
    lines.append("")
    lines.append("export const plannerHelpSections: Record<string, string> = {")

    for key, html in sections.items():
        escaped = html.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
        lines.append(f"  {key}: `{escaped}`,")

    lines.append("};")
    lines.append("")

    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    if not GUIDE_PATH.exists():
        msg = f"Guide not found: {GUIDE_PATH}"
        raise FileNotFoundError(msg)

    md = GUIDE_PATH.read_text(encoding="utf-8")
    raw_sections = _split_sections(md)
    sections = _resolve_sections(raw_sections)
    _write_ts(sections, SECTION_TITLES)
    print(f"Generated {OUTPUT_PATH} ({len(sections)} sections)")


if __name__ == "__main__":
    main()
