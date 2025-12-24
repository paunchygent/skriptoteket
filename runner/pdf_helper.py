from __future__ import annotations

from pathlib import Path, PurePosixPath

from tool_errors import ToolUserError

_WORK_DIR = "/work/"


def _validate_relative_pdf_path(relative_path: str) -> PurePosixPath:
    candidate = relative_path.strip()
    if not candidate:
        raise ToolUserError("Ogiltigt filnamn. Filnamnet måste sluta med .pdf.")
    if "\x00" in candidate:
        raise ToolUserError("Ogiltigt filnamn. Filnamnet innehåller ogiltiga tecken.")

    candidate = candidate.replace("\\", "/")
    path = PurePosixPath(candidate)

    if path.is_absolute():
        raise ToolUserError("Ogiltigt filnamn. Filnamnet måste vara relativt under output.")
    if any(part in {"..", "."} for part in path.parts):
        raise ToolUserError("Ogiltigt filnamn. Filnamnet får inte innehålla '..' eller '.'.")
    if path.suffix.lower() != ".pdf":
        raise ToolUserError("Ogiltigt filnamn. Filnamnet måste sluta med .pdf.")

    return path


def _safe_join_output_dir(*, output_dir: str, relative_path: PurePosixPath) -> Path:
    output_root = Path(output_dir)
    try:
        output_root.mkdir(parents=True, exist_ok=True)
    except Exception as exc:  # noqa: BLE001 - boundary helper
        raise ToolUserError("Kunde inte skapa output-katalogen för PDF.") from exc

    output_root_resolved = output_root.resolve()
    output_path = output_root.joinpath(*relative_path.parts)
    output_path_resolved = output_path.resolve()
    if (
        output_root_resolved != output_path_resolved
        and output_root_resolved not in output_path_resolved.parents
    ):
        raise ToolUserError("Ogiltigt filnamn. PDF måste sparas under output-katalogen.")
    return output_path


def save_as_pdf(html: str, output_dir: str, filename: str) -> str:
    """Render HTML to a PDF under output_dir so it becomes a normal artifact."""

    relative_pdf_path = _validate_relative_pdf_path(filename)
    pdf_path = _safe_join_output_dir(output_dir=output_dir, relative_path=relative_pdf_path)

    try:
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as exc:  # noqa: BLE001 - boundary helper
        raise ToolUserError("Kunde inte skapa undermappar för PDF-utdata.") from exc

    try:
        from weasyprint import HTML  # imported lazily; tool scripts may not need PDF support

        HTML(string=html, base_url=_WORK_DIR).write_pdf(
            target=str(pdf_path),
            pdf_identifier=None,
            uncompressed_pdf=False,
        )
    except ToolUserError:
        raise
    except Exception as exc:  # noqa: BLE001 - boundary helper
        raise ToolUserError(
            "PDF-rendering misslyckades. Kontrollera att HTML/CSS är giltig och "
            "att filnamnet slutar med .pdf."
        ) from exc

    return str(pdf_path)
