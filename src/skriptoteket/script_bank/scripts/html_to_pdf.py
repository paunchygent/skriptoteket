"""
Skriptoteket-kompatibel HTML-till-PDF-konverterare (stöder flera filer).

Entrypoint: run_tool(input_dir: str, output_dir: str) -> dict

- Tar emot en uppladdad HTML-fil (.html/.htm)
- Om flera filer laddas upp hittar skriptet HTML-filer via SKRIPTOTEKET_INPUT_MANIFEST
- Stöder externa resurser som laddas upp tillsammans med HTML-filen:
  - Relativa CSS-länkar som <link rel="stylesheet" href="style.css">
  - Relativa bildlänkar som <img src="image.png">
  - genom att injicera <base href="file:///.../"> i HTML
- Renderar till PDF med pdf_helper.save_as_pdf
- Skriver PDF-artefakten till output_dir
- Returnerar Skriptoteket Contract v2-payload (outputs/next_actions/state)

Inga projektlokala imports. Ingen sys.path-manipulation. Inga dolda beroenden.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict


class ManifestFile(TypedDict):
    name: str
    path: str
    bytes: int


def _notice(level: str, message: str) -> dict[str, object]:
    return {"kind": "notice", "level": level, "message": message}


def _markdown(md: str) -> dict[str, object]:
    return {"kind": "markdown", "markdown": md}


def _result(*, outputs: list[dict[str, object]]) -> dict[str, object]:
    return {"outputs": outputs, "next_actions": [], "state": None}


def _error_result(message: str) -> dict[str, object]:
    return _result(outputs=[_notice("error", message)])


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


def _with_base_href(html: str, *, base_href: str) -> str:
    lower = html.lower()
    if "<base" in lower:
        return html

    insert = f'<base href="{base_href}" />'

    head_index = lower.find("<head")
    if head_index == -1:
        return insert + "\n" + html

    head_end = lower.find(">", head_index)
    if head_end == -1:
        return insert + "\n" + html

    return html[: head_end + 1] + "\n" + insert + html[head_end + 1 :]


def _save_pdf(*, html_content: str, output_dir: Path, filename: str) -> Path:
    try:
        from pdf_helper import save_as_pdf  # type: ignore
    except Exception as exc:
        raise RuntimeError("pdf_helper is not available in the runtime.") from exc

    pdf_path = save_as_pdf(html_content, str(output_dir), filename)
    return Path(pdf_path)


def run_tool(input_dir: str, output_dir: str) -> dict[str, object]:
    input_root = Path(input_dir)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    if not input_root.is_dir():
        return _error_result("Indatakatalogen kunde inte hittas eller läsas.")

    input_files = _select_input_files(input_dir=input_root)
    html_sources = _select_html_sources(input_files=input_files)

    if not html_sources:
        return _error_result("Ingen HTML-fil hittades. Ladda upp minst en .html/.htm-fil.")

    used_pdf_names: set[str] = set()
    pdf_rows: list[dict[str, object]] = []

    for source in html_sources:
        pdf_name_base = f"{source.stem}.pdf"
        pdf_name = pdf_name_base
        counter = 2
        while pdf_name in used_pdf_names:
            pdf_name = f"{source.stem}_{counter}.pdf"
            counter += 1
        used_pdf_names.add(pdf_name)

        try:
            html_content = source.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            pdf_rows.append(
                {
                    "source": source.name,
                    "pdf": pdf_name,
                    "backend": "pdf_helper",
                    "bytes": 0,
                    "status": "error",
                    "message": f"Kunde inte läsa HTML: {exc}",
                }
            )
            continue

        base_href = source.parent.resolve().as_uri() + "/"
        html_with_base = _with_base_href(html_content, base_href=base_href)

        try:
            pdf_path = _save_pdf(
                html_content=html_with_base,
                output_dir=output,
                filename=pdf_name,
            )
        except Exception as exc:  # noqa: BLE001
            pdf_rows.append(
                {
                    "source": source.name,
                    "pdf": pdf_name,
                    "backend": "pdf_helper",
                    "bytes": 0,
                    "status": "error",
                    "message": f"Konverteringen misslyckades: {exc}",
                }
            )
            continue

        if not pdf_path.exists() or not pdf_path.is_file():
            pdf_rows.append(
                {
                    "source": source.name,
                    "pdf": pdf_name,
                    "backend": "pdf_helper",
                    "bytes": 0,
                    "status": "error",
                    "message": "Konverteringen kördes, men ingen PDF skapades.",
                }
            )
            continue

        pdf_rows.append(
            {
                "source": source.name,
                "pdf": pdf_path.name,
                "backend": "pdf_helper",
                "bytes": pdf_path.stat().st_size,
                "status": "ok",
                "message": "",
            }
        )

    ok_count = sum(1 for row in pdf_rows if row["status"] == "ok")
    error_count = len(pdf_rows) - ok_count

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    level = "info" if error_count == 0 else "warning"
    if ok_count == 0:
        level = "error"

    outputs: list[dict[str, object]] = [
        _notice(
            level,
            (f"{ok_count} PDF skapades" + (f" ({error_count} fel)." if error_count else ".")),
        ),
        _markdown(
            f"Genererat {timestamp}.\n\n"
            "Tips: Om din HTML länkar externa CSS- eller bildfiler, ladda upp dem samtidigt "
            "i samma körning med korrekta relativa filnamn."
        ),
        {
            "kind": "table",
            "title": "PDF-resultat",
            "columns": [
                {"key": "source", "label": "HTML"},
                {"key": "pdf", "label": "PDF"},
                {"key": "backend", "label": "Backend"},
                {"key": "bytes", "label": "Byte"},
                {"key": "status", "label": "Status"},
                {"key": "message", "label": "Meddelande"},
            ],
            "rows": pdf_rows,
        },
    ]

    uploaded_files_rows = [
        {"name": file["name"], "bytes": file["bytes"]} for file in input_files if file["bytes"] >= 0
    ]
    if uploaded_files_rows:
        outputs.append(
            {
                "kind": "table",
                "title": "Uppladdade filer",
                "columns": [
                    {"key": "name", "label": "Namn"},
                    {"key": "bytes", "label": "Byte"},
                ],
                "rows": uploaded_files_rows,
            }
        )

    return _result(outputs=outputs)
