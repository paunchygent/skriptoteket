"""
HTML → PDF med förhandsgranskning (Skriptoteket demo).

Demonstrerar alla Skriptoteket-funktioner:
- Tvåstegsflöde: förhandsgranska → konvertera
- html_sandboxed: Live HTML-förhandsgranskning
- vega_lite: Filstorleksjämförelse
- next_actions: Navigering mellan steg
- state: Spåra arbetsflödessteg
- settings: Användarpreferenser (sidstorlek, orientering)
- artifacts: PDF-nedladdning

Entrypoint: run_tool(input_dir: str, output_dir: str) -> dict
"""

from __future__ import annotations

import hashlib
import json
import traceback
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path

from skriptoteket_toolkit import (
    ManifestFile,
    get_action_parts,
    list_input_files,
    read_settings,
)

from .html_prep import build_page_css, wrap_preview_html
from .rendering import try_weasyprint

# ─── HJÄLPFUNKTIONER ───


def _notice(level: str, message: str) -> dict[str, object]:
    return {"kind": "notice", "level": level, "message": message}


def _markdown(md: str) -> dict[str, object]:
    return {"kind": "markdown", "markdown": md}


def _shorten_for_table(message: str, *, max_chars: int = 200) -> str:
    normalized = " ".join(message.split())
    if len(normalized) <= max_chars:
        return normalized
    if max_chars <= 3:
        return "..."
    return normalized[: max_chars - 3] + "..."


def _select_input_files(*, input_dir: Path) -> list[ManifestFile]:
    manifest_files = list_input_files()
    if manifest_files:
        return manifest_files

    if not input_dir.is_dir():
        return []

    return [
        {"name": path.name, "path": str(path), "bytes": path.stat().st_size}
        for path in sorted(input_dir.glob("*"))
        if path.is_file()
    ]


def _select_html_sources(*, input_files: list[ManifestFile]) -> list[Path]:
    html_files = [
        Path(file["path"])
        for file in input_files
        if Path(file["name"]).suffix.lower() in {".html", ".htm"}
    ]
    return sorted(html_files, key=lambda path: path.name.lower())


# ─── STEG 1: FÖRHANDSGRANSKNING ───


def _handle_preview(*, input_files: list[ManifestFile]) -> dict[str, object]:
    html_sources = _select_html_sources(input_files=input_files)

    if not html_sources:
        return {
            "outputs": [
                _notice("error", "Ingen HTML-fil hittades. Ladda upp minst en .html/.htm-fil.")
            ],
            "next_actions": [],
            "state": None,
        }

    # Läs användarinställningar för standardvärden
    settings = read_settings()
    default_page_size = settings.get("default_page_size", "a4")
    default_orientation = settings.get("default_orientation", "portrait")

    # Läs första HTML-filen för förhandsgranskning (max 96KB för html_sandboxed)
    first_html = html_sources[0]
    try:
        html_content = first_html.read_text(encoding="utf-8", errors="replace")
        # Begränsa till 90KB för att ha marginal
        if len(html_content) > 90_000:
            html_content = html_content[:90_000] + "\n<!-- ... (trunkerad) -->"
    except OSError:
        html_content = "<p>Kunde inte läsa HTML-filen.</p>"

    html_content = wrap_preview_html(html=html_content)

    # Bygg outputs
    outputs: list[dict[str, object]] = [
        _notice("info", f"Förhandsgranska {len(html_sources)} HTML-fil(er) innan konvertering."),
        _markdown(
            f"**Första fil:** `{first_html.name}`\n\n"
            "Granska förhandsgranskningen nedan. När du är nöjd, klicka **Konvertera till PDF**."
        ),
        {"kind": "html_sandboxed", "html": html_content},
        {
            "kind": "table",
            "title": "Uppladdade filer",
            "columns": [
                {"key": "name", "label": "Namn"},
                {"key": "bytes", "label": "Storlek (byte)"},
            ],
            "rows": [{"name": f["name"], "bytes": f["bytes"]} for f in input_files],
        },
    ]

    # Bygg next_actions
    next_actions = [
        {
            "action_id": "convert",
            "label": "Konvertera till PDF",
            "kind": "form",
            "fields": [
                {
                    "name": "page_size",
                    "label": "Sidstorlek",
                    "kind": "enum",
                    "options": [
                        {"value": "a4", "label": "A4"},
                        {"value": "letter", "label": "Letter"},
                    ],
                },
                {
                    "name": "orientation",
                    "label": "Orientering",
                    "kind": "enum",
                    "options": [
                        {"value": "portrait", "label": "Stående"},
                        {"value": "landscape", "label": "Liggande"},
                    ],
                },
            ],
        },
        {
            "action_id": "reset",
            "label": "Börja om",
            "kind": "form",
            "fields": [],
        },
    ]

    # Spara state för nästa steg
    state = {
        "step": "preview",
        "html_files": [str(p) for p in html_sources],
        "input_files": input_files,
        "default_page_size": default_page_size,
        "default_orientation": default_orientation,
    }

    return {"outputs": outputs, "next_actions": next_actions, "state": state}


# ─── STEG 2: KONVERTERING ───


def _handle_action(
    *,
    action_id: str,
    input_data: Mapping[str, object],
    state: Mapping[str, object],
    output_dir: Path,
) -> dict[str, object]:
    # Hantera "börja om"
    if action_id == "reset":
        return {
            "outputs": [_notice("info", "Ladda upp nya filer för att fortsätta.")],
            "next_actions": [],
            "state": None,
        }

    # Hantera okänd action
    if action_id != "convert":
        return {
            "outputs": [_notice("error", f"Okänd action: '{action_id}'")],
            "next_actions": [],
            "state": None,
        }

    # Hämta konverteringsinställningar
    page_size = str(input_data.get("page_size", "a4"))
    orientation = str(input_data.get("orientation", "portrait"))
    page_css = build_page_css(page_size=page_size, orientation=orientation)
    pdf_css_fingerprint = hashlib.sha256(page_css.encode("utf-8")).hexdigest()[:8]

    # Hämta filinfo från state
    raw_html_files = state.get("html_files")
    html_file_paths = (
        [path for path in raw_html_files if isinstance(path, str)]
        if isinstance(raw_html_files, list)
        else []
    )

    if not html_file_paths:
        return {
            "outputs": [_notice("error", "Ingen HTML-fil i state. Börja om.")],
            "next_actions": [],
            "state": None,
        }

    output_dir.mkdir(parents=True, exist_ok=True)

    # Konvertera alla HTML-filer
    used_pdf_names: set[str] = set()
    pdf_rows: list[dict[str, object]] = []
    chart_data: list[dict[str, object]] = []
    error_log_lines: list[str] = []
    perf_entries: list[dict[str, object]] = []

    for html_path_str in html_file_paths:
        source = Path(html_path_str)
        if not source.exists():
            continue

        html_size = source.stat().st_size

        # Generera unikt PDF-namn
        pdf_name_base = f"{source.stem}.pdf"
        pdf_name = pdf_name_base
        counter = 2
        while pdf_name in used_pdf_names:
            pdf_name = f"{source.stem}_{counter}.pdf"
            counter += 1
        used_pdf_names.add(pdf_name)
        pdf_path = output_dir / pdf_name

        # Försök konvertera
        backend: str | None = None
        errors: list[str] = []
        weasyprint_traceback: str | None = None

        try:
            backend = try_weasyprint(
                source=source,
                pdf_path=pdf_path,
                page_size=page_size,
                orientation=orientation,
                perf_log=perf_entries,
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"WeasyPrint: {exc}")
            weasyprint_traceback = traceback.format_exc()

        if backend is None:
            full_message = " | ".join(errors) if errors else "Okänt fel"
            log_entry = f"{source.name}: {full_message}"
            if weasyprint_traceback:
                log_entry += "\n" + weasyprint_traceback.rstrip()
            error_log_lines.append(log_entry)
            pdf_rows.append(
                {
                    "source": source.name,
                    "pdf": pdf_name,
                    "status": "fel",
                    "bytes": 0,
                    "message": _shorten_for_table(full_message),
                }
            )
            continue

        if not pdf_path.exists():
            error_log_lines.append(f"{source.name}: Ingen PDF skapades")
            pdf_rows.append(
                {
                    "source": source.name,
                    "pdf": pdf_name,
                    "status": "fel",
                    "bytes": 0,
                    "message": "Ingen PDF skapades",
                }
            )
            continue

        pdf_size = pdf_path.stat().st_size
        pdf_rows.append(
            {
                "source": source.name,
                "pdf": pdf_name,
                "status": "ok",
                "bytes": pdf_size,
                "message": "",
            }
        )

        # Data för vega-lite diagram
        chart_data.append({"file": source.name, "type": "HTML", "bytes": html_size})
        chart_data.append({"file": pdf_name, "type": "PDF", "bytes": pdf_size})

    # Räkna resultat
    ok_count = sum(1 for row in pdf_rows if row["status"] == "ok")
    error_count = len(pdf_rows) - ok_count
    level = "info" if error_count == 0 else ("warning" if ok_count > 0 else "error")

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Bygg outputs
    error_suffix = f" ({error_count} fel)." if error_count else "."
    orient_label = "Liggande" if orientation == "landscape" else "Stående"
    outputs: list[dict[str, object]] = [
        _notice(level, f"{ok_count} PDF skapades{error_suffix}"),
        _markdown(
            f"**Konverterat:** {timestamp}\n\n"
            f"**Sidstorlek:** {page_size.upper()} | **Orientering:** {orient_label}\n\n"
            f"**PDF CSS:** `{pdf_css_fingerprint}`"
        ),
    ]

    if error_log_lines:
        (output_dir / "conversion-errors.txt").write_text(
            "\n".join(error_log_lines) + "\n",
            encoding="utf-8",
        )
        outputs.append(
            _markdown(
                "Fullständiga felmeddelanden finns i artefakten `conversion-errors.txt`. "
                "(Tabellen visar en kort sammanfattning.)"
            )
        )

    if perf_entries:
        (output_dir / "conversion-perf.json").write_text(
            json.dumps(perf_entries, indent=2) + "\n",
            encoding="utf-8",
        )
        outputs.append(
            _markdown(
                "Prestandalogg finns i artefakten `conversion-perf.json` "
                "(tider per steg/återförsök)."
            )
        )

    # Lägg till vega-lite diagram om vi har data
    if chart_data:
        outputs.append(
            {
                "kind": "vega_lite",
                "spec": {
                    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                    "width": 300,
                    "height": 200,
                    "title": "Filstorlek: HTML → PDF",
                    "data": {"values": chart_data},
                    "mark": "bar",
                    "encoding": {
                        "x": {"field": "file", "type": "nominal", "title": "Fil"},
                        "y": {"field": "bytes", "type": "quantitative", "title": "Storlek (byte)"},
                        "color": {"field": "type", "type": "nominal", "title": "Typ"},
                    },
                },
            }
        )

    # Resultattabell
    outputs.append(
        {
            "kind": "table",
            "title": "Konverteringsresultat",
            "columns": [
                {"key": "source", "label": "HTML"},
                {"key": "pdf", "label": "PDF"},
                {"key": "status", "label": "Status"},
                {"key": "bytes", "label": "Storlek (byte)"},
                {"key": "message", "label": "Meddelande"},
            ],
            "rows": pdf_rows,
        }
    )

    # next_actions för att börja om
    next_actions = [
        {
            "action_id": "reset",
            "label": "Konvertera nya filer",
            "kind": "form",
            "fields": [],
        },
    ]

    return {"outputs": outputs, "next_actions": next_actions, "state": None}


# ─── HUVUDENTRYPOINT ───


def run_tool(input_dir: str, output_dir: str) -> dict[str, object]:
    input_root = Path(input_dir)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    action_id, action_input, action_state = get_action_parts()
    if action_id is not None:
        return _handle_action(
            action_id=action_id,
            input_data=action_input,
            state=action_state,
            output_dir=output,
        )

    input_files = _select_input_files(input_dir=input_root)

    # Vanlig körning: visa förhandsgranskning
    if not input_files:
        return {
            "outputs": [_notice("error", "Ingen fil uppladdad. Ladda upp minst en HTML-fil.")],
            "next_actions": [],
            "state": None,
        }

    return _handle_preview(input_files=input_files)
