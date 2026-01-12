from __future__ import annotations

import argparse
import html
import re
from pathlib import Path
from typing import Any

import markdown
import yaml
from markdown.extensions.toc import slugify


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text

    end_marker = "\n---\n"
    end = text.find(end_marker, 4)
    if end == -1:
        raise ValueError("Frontmatter starts with '---' but no closing '---' found.")

    frontmatter_raw = text[4:end]
    body = text[end + len(end_marker) :]

    frontmatter = yaml.safe_load(frontmatter_raw) or {}
    if not isinstance(frontmatter, dict):
        raise ValueError("Frontmatter must be a YAML mapping.")

    return frontmatter, body


def _split_h2_sections(markdown_body: str) -> tuple[str, list[tuple[str, str]]]:
    lines = markdown_body.splitlines()

    in_fence = False
    fence_marker: str | None = None

    subtitle_lines: list[str] = []
    sections: list[tuple[str, list[str]]] = []
    current_h2: str | None = None
    current_lines: list[str] = []

    def _flush_current() -> None:
        nonlocal current_h2, current_lines
        if current_h2 is None:
            return
        sections.append((current_h2, current_lines))
        current_h2 = None
        current_lines = []

    for line in lines:
        stripped = line.lstrip()

        if not in_fence and (stripped.startswith("```") or stripped.startswith("~~~")):
            in_fence = True
            fence_marker = stripped[:3]
        elif in_fence and fence_marker is not None and stripped.startswith(fence_marker):
            in_fence = False
            fence_marker = None

        if not in_fence and line.startswith("## "):
            _flush_current()
            current_h2 = line.removeprefix("## ").strip()
            current_lines = []
            continue

        if current_h2 is None:
            subtitle_lines.append(line)
        else:
            current_lines.append(line)

    _flush_current()

    subtitle = " ".join([ln.strip() for ln in subtitle_lines if ln.strip()])
    return subtitle, [
        (h2, "\n".join(section_lines).rstrip() + "\n") for h2, section_lines in sections
    ]


def _wrap_callouts(html_body: str) -> str:
    def _callout(*, kind: str, title: str, inner_html: str) -> str:
        return (
            f'<div class="callout {kind}">\n'
            f'  <div class="title"><span class="dot"></span>{html.escape(title)}</div>\n'
            f"{inner_html}\n"
            f"</div>"
        )

    # Notes: <p>Notes:</p><ul>...</ul>
    html_body = re.sub(
        r"<p>Notes:</p>\s*(<ul>.*?</ul>)",
        lambda m: _callout(kind="note", title="Notes", inner_html=m.group(1)),
        html_body,
        flags=re.DOTALL,
    )

    # **Critical**: ... => <p><strong>Critical</strong>: ...</p>
    html_body = re.sub(
        r"<p><strong>Critical</strong>:\s*(.*?)</p>",
        lambda m: _callout(kind="critical", title="Critical", inner_html=f"<p>{m.group(1)}</p>"),
        html_body,
        flags=re.DOTALL,
    )

    # Note: ... => <p>Note: ...</p>
    html_body = re.sub(
        r"<p>Note:\s*(.*?)</p>",
        lambda m: _callout(kind="warn", title="Note", inner_html=f"<p>{m.group(1)}</p>"),
        html_body,
        flags=re.DOTALL,
    )

    # Live note (hemma): ... => <p>Live note (hemma): ...</p>
    html_body = re.sub(
        r"<p>Live note \(hemma\):\s*(.*?)</p>",
        lambda m: _callout(
            kind="note", title="Live note (hemma)", inner_html=f"<p>{m.group(1)}</p>"
        ),
        html_body,
        flags=re.DOTALL,
    )

    return html_body


def _render_markdown_fragment(markdown_text: str) -> str:
    rendered = markdown.markdown(
        markdown_text,
        extensions=[
            "fenced_code",
            "tables",
            "toc",
        ],
    )
    return _wrap_callouts(rendered)


def export_runbook_pdf_html(*, input_path: Path, output_path: Path) -> None:
    raw = input_path.read_text(encoding="utf-8")
    meta, body = _split_frontmatter(raw)

    subtitle, sections = _split_h2_sections(body)

    title = str(meta.get("title", "Runbook"))
    doc_id = str(meta.get("id", ""))
    owners = str(meta.get("owners", ""))
    status = str(meta.get("status", "")).strip().title()
    created = str(meta.get("created", ""))
    updated = str(meta.get("updated", ""))
    system = str(meta.get("system", ""))

    toc_items = []
    section_html_parts: list[str] = []
    for heading, section_markdown in sections:
        section_id = slugify(heading, "-")
        toc_items.append(f'<li><a href="#{section_id}">{html.escape(heading)}</a></li>')

        inner_html = _render_markdown_fragment(section_markdown)
        section_html_parts.append(
            f'          <section id="{section_id}">\n'
            f"            <h2>{html.escape(heading)}</h2>\n"
            f"{inner_html}\n"
            f"          </section>"
        )

    toc_html = "\n                ".join(toc_items)
    sections_html = "\n\n".join(section_html_parts)

    generated_banner = html.escape(
        f"Generated from {input_path.as_posix()} — do not edit this file manually."
    )

    html_out = f"""<!doctype html>
<!-- {generated_banner} -->
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(title)} ({html.escape(doc_id)})</title>
  <style>
    :root{{
      --bg: #0b1020;
      --panel: #0f1730;
      --paper: #0e1430;
      --text: #e8ecff;
      --muted: #b8c0e6;
      --faint: #8a94c7;

      --border: rgba(232,236,255,0.12);
      --border-strong: rgba(232,236,255,0.18);
      --shadow: 0 12px 40px rgba(0,0,0,0.35);

      --accent: #6aa6ff;
      --accent-2: #8cf0d6;

      --ok: #27d17f;
      --warn: #ffcc66;
      --danger: #ff6b7a;
      --info: #7dd3fc;

      --code-bg: rgba(255,255,255,0.04);
      --code-border: rgba(255,255,255,0.10);

      --radius: 14px;
      --radius-sm: 10px;

      --maxw: 1000px;
    }}

    /* Base */
    html, body {{ height: 100%; }}
    body{{
      margin:0;
      background:
        radial-gradient(1200px 700px at 15% 10%, rgba(106,166,255,0.22), transparent 60%),
        radial-gradient(900px 650px at 85% 0%, rgba(140,240,214,0.14), transparent 60%),
        linear-gradient(180deg, var(--bg), #050714 70%);
      color: var(--text);
      font: 16px/1.55 ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji", "Segoe UI Emoji";
      letter-spacing: 0.1px;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
    }}

    a{{
      color: var(--accent);
      text-decoration: none;
    }}
    a:hover{{ text-decoration: underline; }}

    code, pre, kbd{{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    }}

    .wrap{{
      max-width: var(--maxw);
      margin: 42px auto;
      padding: 0 18px 70px;
    }}

    .topbar{{
      display:flex;
      align-items:flex-start;
      justify-content:space-between;
      gap: 18px;
      margin-bottom: 18px;
    }}

    .brand{{
      display:flex;
      flex-direction:column;
      gap: 8px;
    }}

    .kicker{{
      display:inline-block;
      font-size: 13px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--faint);
    }}

    h1{{
      margin: 0;
      font-size: 32px;
      letter-spacing: -0.02em;
      line-height: 1.1;
    }}

    .subtitle{{
      color: var(--muted);
      max-width: 60ch;
    }}

    .badges{{
      display:flex;
      flex-wrap:wrap;
      gap: 8px;
      justify-content:flex-end;
      margin-top: 2px;
    }}

    .badge{{
      border: 1px solid var(--border-strong);
      border-radius: 999px;
      padding: 6px 10px;
      font-size: 12px;
      color: var(--muted);
      background: rgba(255,255,255,0.03);
      white-space: nowrap;
    }}
    .badge strong{{ color: var(--text); font-weight: 600; }}
    .badge.ok{{ border-color: rgba(39,209,127,0.35); }}
    .badge.warn{{ border-color: rgba(255,204,102,0.35); }}
    .badge.info{{ border-color: rgba(125,211,252,0.35); }}

    .panel{{
      background: rgba(255,255,255,0.03);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      overflow:hidden;
    }}

    .panel-inner{{ padding: 16px 18px; }}

    .meta{{
      display:flex;
      flex-wrap:wrap;
      gap: 12px;
    }}

    .meta-card{{
      flex: 1 1 200px;
      min-width: 200px;
      background: rgba(255,255,255,0.02);
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      padding: 12px 14px;
    }}
    .meta-card h3{{
      margin: 0 0 6px 0;
      font-size: 12px;
      color: var(--faint);
      text-transform: uppercase;
      letter-spacing: 0.12em;
    }}
    .meta-card .value{{
      color: var(--text);
      font-weight: 600;
    }}
    .meta-card .value small{{
      font-weight: 500;
      color: var(--muted);
    }}

    .grid{{
      display:grid;
      grid-template-columns: 240px 1fr;
      gap: 14px;
      padding: 16px 18px 18px;
    }}

    .toc .panel-inner{{ padding: 14px 14px; }}
    .toc h2{{
      margin: 0 0 8px 0;
      font-size: 13px;
      color: var(--faint);
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }}
    .toc ol{{
      margin: 0;
      padding-left: 18px;
      color: var(--muted);
      font-size: 14px;
    }}
    .toc li{{ margin: 6px 0; }}

    /* Content */
    main{{ padding: 18px; }}
    section{{
      border-top: 1px solid var(--border);
      padding-top: 22px;
      margin-top: 18px;
    }}
    section:first-child{{
      border-top: none;
      padding-top: 0;
      margin-top: 0;
    }}

    h2{{
      margin: 0 0 10px 0;
      font-size: 22px;
      letter-spacing: -0.01em;
    }}
    h3{{
      margin: 18px 0 10px 0;
      font-size: 17px;
      letter-spacing: -0.01em;
      color: var(--text);
    }}
    p{{
      margin: 10px 0;
      color: var(--muted);
    }}

    ul{{
      margin: 10px 0 10px 18px;
      color: var(--muted);
    }}
    li{{ margin: 6px 0; }}

    /* Code blocks */
    pre{{
      margin: 10px 0 14px;
      padding: 14px 14px;
      background: var(--code-bg);
      border: 1px solid var(--code-border);
      border-radius: var(--radius-sm);
      overflow:auto;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
    }}
    pre code{{
      color: var(--text);
      font-size: 13px;
      line-height: 1.5;
      display:block;
      white-space: pre;
    }}
    code{{
      color: var(--text);
      background: rgba(255,255,255,0.04);
      border: 1px solid rgba(255,255,255,0.06);
      padding: 1px 6px;
      border-radius: 8px;
      font-size: 0.95em;
    }}

    /* Callouts */
    .callout{{
      margin: 12px 0 14px;
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      padding: 12px 14px;
      background: rgba(255,255,255,0.02);
    }}
    .callout .title{{
      display:flex;
      align-items:center;
      gap: 10px;
      font-size: 13px;
      font-weight: 700;
      color: var(--text);
      text-transform: uppercase;
      letter-spacing: 0.12em;
    }}
    .callout .title .dot{{
      width: 10px;
      height: 10px;
      border-radius: 99px;
      background: var(--info);
      box-shadow: 0 0 0 3px rgba(125,211,252,0.12);
      flex: 0 0 auto;
    }}
    .callout p{{ margin: 6px 0; color: var(--muted); }}
    .callout.note .title .dot{{ background: var(--info); box-shadow: 0 0 0 3px rgba(125,211,252,0.12); }}
    .callout.warn{{ border-color: rgba(255,204,102,0.30); }}
    .callout.warn .title .dot{{ background: var(--warn); box-shadow: 0 0 0 3px rgba(255,204,102,0.12); }}
    .callout.danger{{ border-color: rgba(255,107,122,0.35); }}
    .callout.danger .title .dot{{ background: var(--danger); box-shadow: 0 0 0 3px rgba(255,107,122,0.12); }}
    .callout.critical{{ border-color: rgba(140,240,214,0.30); }}
    .callout.critical .title .dot{{ background: var(--accent-2); box-shadow: 0 0 0 3px rgba(140,240,214,0.12); }}

    footer{{
      margin-top: 24px;
      color: var(--faint);
      font-size: 13px;
      border-top: 1px solid var(--border);
      padding-top: 14px;
    }}

    @media (max-width: 960px){{
      .grid{{ grid-template-columns: 1fr; }}
      .badges{{ justify-content:flex-start; }}
    }}
  </style>
</head>

<body>
  <div class="wrap">
    <div class="topbar">
      <div class="brand">
        <div class="kicker">Runbook</div>
        <h1>{html.escape(title.removeprefix("Runbook: ").strip())}</h1>
        <div class="subtitle">
          {html.escape(subtitle)}
        </div>
      </div>
      <div class="badges" aria-label="document metadata badges">
        <div class="badge ok"><strong>Status:</strong> {html.escape(status)}</div>
        <div class="badge info"><strong>System:</strong> {html.escape(system)}</div>
        <div class="badge"><strong>ID:</strong> {html.escape(doc_id)}</div>
      </div>
    </div>

    <div class="panel">
      <div class="panel-inner">
        <div class="meta" aria-label="document metadata">
          <div class="meta-card">
            <h3>Owners</h3>
            <div class="value">{html.escape(owners)}</div>
          </div>
          <div class="meta-card">
            <h3>Lifecycle</h3>
            <div class="value">
              Created <small>{html.escape(created)}</small><br />
              Updated <small>{html.escape(updated)}</small>
            </div>
          </div>
        </div>
      </div>

      <div class="grid">
        <aside class="toc">
          <div class="panel">
            <div class="panel-inner">
              <h2>Contents</h2>
              <ol>
                {toc_html}
              </ol>
            </div>
          </div>
        </aside>

        <main>
{sections_html}
          <footer>
            Document: <strong>{html.escape(doc_id)}</strong> — “{html.escape(title)}” — Updated <strong>{html.escape(updated)}</strong>.
          </footer>
        </main>
      </div>
    </div>
  </div>
</body>
</html>
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_out, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export a runbook Markdown file to a printable HTML file."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=_repo_root() / "docs/runbooks/runbook-home-server.md",
        help="Input runbook Markdown file (default: docs/runbooks/runbook-home-server.md)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_repo_root() / "stakeholders/server_runbook_pdf.html",
        help="Output HTML file (default: stakeholders/server_runbook_pdf.html)",
    )
    args = parser.parse_args()

    export_runbook_pdf_html(input_path=args.input, output_path=args.output)
    print(f"Wrote HTML: {args.output}")


if __name__ == "__main__":
    main()
