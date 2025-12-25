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

import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict


class ManifestFile(TypedDict):
    name: str
    path: str
    bytes: int


# ─── HJÄLPFUNKTIONER ───


def _notice(level: str, message: str) -> dict[str, object]:
    return {"kind": "notice", "level": level, "message": message}


def _markdown(md: str) -> dict[str, object]:
    return {"kind": "markdown", "markdown": md}


def _read_input_manifest_files() -> list[ManifestFile]:
    raw = os.environ.get("SKRIPTOTEKET_INPUT_MANIFEST", "")
    if not raw.strip():
        return []
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, dict):
        return []
    files = payload.get("files")
    if not isinstance(files, list):
        return []

    result: list[ManifestFile] = []
    for item in files:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        path = item.get("path")
        bytes_ = item.get("bytes")
        if isinstance(name, str) and isinstance(path, str) and isinstance(bytes_, int):
            result.append({"name": name, "path": path, "bytes": bytes_})
    return result


def _select_input_files(*, input_dir: Path) -> list[ManifestFile]:
    manifest_files = _read_input_manifest_files()
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


def _read_user_settings() -> dict[str, object]:
    memory_path = os.environ.get("SKRIPTOTEKET_MEMORY_PATH")
    if not memory_path:
        return {}
    path = Path(memory_path)
    if not path.exists():
        return {}
    try:
        memory = json.loads(path.read_text(encoding="utf-8"))
        return memory.get("settings", {}) if isinstance(memory, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


@contextmanager
def _chdir(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


# ─── PDF-KONVERTERING ───


def _try_weasyprint(
    *, source: Path, pdf_path: Path, page_size: str, orientation: str
) -> str | None:
    try:
        from weasyprint import CSS, HTML  # type: ignore
    except Exception:
        return None

    # Bygg CSS för sidstorlek och orientering
    orient = "landscape" if orientation == "landscape" else "portrait"
    size_css = f"@page {{ size: {page_size} {orient}; }}"

    HTML(filename=str(source), base_url=str(source.parent.resolve())).write_pdf(
        str(pdf_path),
        stylesheets=[CSS(string=size_css)],
    )
    return "weasyprint"


def _try_pypandoc(
    *,
    source: Path,
    pdf_path: Path,
    page_size: str,
    orientation: str,  # noqa: ARG001
) -> str | None:
    try:
        import pypandoc  # type: ignore
    except Exception:
        return None

    # pypandoc stöder inte alla sidstorlekar direkt, men vi försöker
    extra_args = [f"--resource-path={source.parent}"]
    if page_size == "letter":
        extra_args.append("-V")
        extra_args.append("papersize=letter")

    with _chdir(source.parent):
        try:
            pypandoc.convert_file(
                str(source),
                to="pdf",
                outputfile=str(pdf_path),
                extra_args=["--pdf-engine=weasyprint", *extra_args],
            )
            return "pandoc(pypandoc, weasyprint-engine)"
        except Exception:
            pypandoc.convert_file(
                str(source),
                to="pdf",
                outputfile=str(pdf_path),
                extra_args=extra_args,
            )
            return "pandoc(pypandoc)"


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
    settings = _read_user_settings()
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


def _handle_action(*, action_path: Path, output_dir: Path) -> dict[str, object]:
    payload = json.loads(action_path.read_text(encoding="utf-8"))
    action_id = str(payload.get("action_id") or "").strip()
    input_data = payload.get("input") if isinstance(payload.get("input"), dict) else {}
    state = payload.get("state") if isinstance(payload.get("state"), dict) else {}

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

    # Hämta filinfo från state
    html_file_paths = state.get("html_files", [])

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

        try:
            backend = _try_weasyprint(
                source=source, pdf_path=pdf_path, page_size=page_size, orientation=orientation
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"WeasyPrint: {exc}")

        if backend is None:
            try:
                backend = _try_pypandoc(
                    source=source, pdf_path=pdf_path, page_size=page_size, orientation=orientation
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(f"pypandoc: {exc}")

        if backend is None:
            pdf_rows.append(
                {
                    "source": source.name,
                    "pdf": pdf_name,
                    "status": "fel",
                    "bytes": 0,
                    "message": " | ".join(errors) if errors else "Okänt fel",
                }
            )
            continue

        if not pdf_path.exists():
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
            f"**Sidstorlek:** {page_size.upper()} | **Orientering:** {orient_label}"
        ),
    ]

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

    input_files = _select_input_files(input_dir=input_root)

    # Kolla om detta är en action-körning (från next_actions)
    action_file = next(
        (item for item in input_files if item.get("name") == "action.json"),
        None,
    )

    if action_file is not None:
        return _handle_action(action_path=Path(str(action_file["path"])), output_dir=output)

    # Fallback: kolla om action.json finns i input_dir
    action_path = input_root / "action.json"
    if action_path.is_file():
        return _handle_action(action_path=action_path, output_dir=output)

    # Vanlig körning: visa förhandsgranskning
    # Filtrera bort action.json från input_files
    filtered_files = [f for f in input_files if f.get("name") != "action.json"]

    if not filtered_files:
        return {
            "outputs": [_notice("error", "Ingen fil uppladdad. Ladda upp minst en HTML-fil.")],
            "next_actions": [],
            "state": None,
        }

    return _handle_preview(input_files=filtered_files)
