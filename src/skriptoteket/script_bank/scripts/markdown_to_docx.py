import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from skriptoteket_toolkit import read_inputs, read_settings  # type: ignore[import-not-found]

# Optional preinstalled libs
try:
    import pypandoc  # type: ignore
except Exception:
    pypandoc = None  # type: ignore

try:
    from docx import Document  # type: ignore
    from docx.enum.style import WD_STYLE_TYPE  # type: ignore
    from docx.oxml.ns import qn  # type: ignore
    from docx.shared import Inches, Pt, RGBColor  # type: ignore
except Exception:
    Document = None  # type: ignore
    WD_STYLE_TYPE = None  # type: ignore


# =========================
# Contract v2 payload helper
# =========================


def contract_v2(
    outputs: list[dict], next_actions: list[dict] | None = None, state: Any = None
) -> dict:
    return {"outputs": outputs, "next_actions": next_actions or [], "state": state}


# =========================
# UI output helpers (dicts)
# =========================


def o_markdown(markdown: str) -> dict:
    return {"kind": "markdown", "markdown": markdown}


def o_notice(level: str, message: str) -> dict:
    return {"kind": "notice", "level": level, "message": message}


def o_json(title: str, value: Any) -> dict:
    return {"kind": "json", "title": title, "value": value}


def o_table(title: str | None, columns: list[dict], rows: list[dict]) -> dict:
    payload: dict = {"kind": "table", "columns": columns, "rows": rows}
    if title:
        payload["title"] = title
    return payload


# =========================
# Constants
# =========================

PROFILE_STANDARD = "standard"
PROFILE_PRINT_BW = "print_bw"
PROFILE_PRINT_COLOR = "print_color"

SCOPE_FIRST = "first"
SCOPE_ALL = "all"


def _profile_label(profile: str) -> str:
    return {
        PROFILE_STANDARD: "Standard",
        PROFILE_PRINT_BW: "Print (svartvit)",
        PROFILE_PRINT_COLOR: "Print (färg)",
    }.get(profile, profile)


def _profile_desc(profile: str) -> str:
    return {
        PROFILE_STANDARD: "Modern standardstil med tydliga rubriker.",
        PROFILE_PRINT_BW: "Utskriftsvänlig typografi utan färg (svart).",
        PROFILE_PRINT_COLOR: "Utskriftsvänlig typografi med diskreta färgaccenter i rubriker.",
    }.get(profile, "")


# =========================
# Platform IO:
# - settings from memory.json
# - per-run inputs from SKRIPTOTEKET_INPUTS
# =========================


def _load_settings_from_memory() -> tuple[dict, str]:
    return (read_settings(), "SKRIPTOTEKET_MEMORY_PATH")


def _load_inputs_from_env() -> tuple[dict, str]:
    return (read_inputs(), "SKRIPTOTEKET_INPUTS")


# =========================
# Unwrap + coercion helpers
# =========================


def _unwrap_value(v: Any) -> Any:
    if isinstance(v, dict) and "value" in v:
        return v.get("value")
    return v


def _as_bool(v: Any, default: bool = False) -> bool:
    v = _unwrap_value(v)
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        s = v.strip().lower()
        if s in {"true", "1", "yes", "y", "on"}:
            return True
        if s in {"false", "0", "no", "n", "off"}:
            return False
    return default


def _as_str(v: Any, default: str = "") -> str:
    v = _unwrap_value(v)
    return v if isinstance(v, str) else default


def _coerce_profile(v: Any, default: str) -> str:
    s = _as_str(v, default).strip()
    if s in {"use_default", "default", ""}:
        return default
    if s in {PROFILE_STANDARD, PROFILE_PRINT_BW, PROFILE_PRINT_COLOR}:
        return s
    return default


def _coerce_scope(v: Any, default: str) -> str:
    s = _as_str(v, default).strip()
    if s in {SCOPE_FIRST, SCOPE_ALL}:
        return s
    return default


# =========================
# File helpers
# =========================


def _mk_file(path: Path, name: str | None = None) -> dict:
    return {"path": path, "name": name or path.name}


def _safe_stem(s: str) -> str:
    s = s.strip().replace("\n", " ").replace("\r", " ")
    s = re.sub(r"[^\w\-.() ]+", "_", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s).strip()
    return s or "output"


def _unique_path(dirpath: Path, filename: str) -> Path:
    base = Path(filename).stem
    ext = Path(filename).suffix or ".docx"
    cand = dirpath / (base + ext)
    i = 2
    while cand.exists():
        cand = dirpath / f"{base} ({i}){ext}"
        i += 1
    return cand


def _human_size(num_bytes: int) -> str:
    n = float(num_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024.0:
            return f"{int(n)} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} TB"


def _normalize_markdown_files(input_root: Path, value: Any) -> list[dict]:
    value = _unwrap_value(value)

    def one(v: Any) -> list[dict]:
        v = _unwrap_value(v)
        if v is None:
            return []
        if isinstance(v, list):
            out: list[dict] = []
            for it in v:
                out.extend(one(it))
            return out
        if isinstance(v, str):
            p = Path(v)
            if not p.is_absolute():
                p = input_root / v
            return [_mk_file(p)]
        if isinstance(v, dict):
            vv = v
            if isinstance(vv, dict) and "value" in vv and isinstance(vv.get("value"), dict):
                vv = vv["value"]

            path_val = vv.get("path") or vv.get("file_path") or vv.get("filepath")
            name_val = vv.get("name") or vv.get("filename") or vv.get("original_filename")

            if isinstance(path_val, str):
                p = Path(path_val)
                if not p.is_absolute():
                    p = input_root / path_val
                return [_mk_file(p, str(name_val) if isinstance(name_val, str) else None)]

            if isinstance(name_val, str):
                p = input_root / name_val
                return [_mk_file(p)]
        return []

    files = one(value)

    seen: set[str] = set()
    uniq: list[dict] = []
    for f in files:
        p = f.get("path")
        if not isinstance(p, Path):
            continue
        k = str(p)
        if k in seen:
            continue
        seen.add(k)
        uniq.append(f)
    return uniq


def _scan_input_dir_for_markdown(input_root: Path) -> list[dict]:
    if not input_root.exists():
        return []
    candidates: list[Path] = []
    for p in input_root.rglob("*"):
        if p.is_file() and p.suffix.lower() in {".md", ".markdown"}:
            candidates.append(p)
    candidates.sort(key=lambda x: x.name.lower())
    return [_mk_file(p) for p in candidates]


# =========================
# DOCX reference doc (simple, non-brittle)
# =========================


def _ensure_style(doc: Any, name: str, style_type: Any) -> Any | None:
    """
    Ensure a style exists in the reference doc. If it already exists, return it.
    If not, try to create it. If that fails, return None.
    """
    try:
        _ = doc.styles[name]
        return _
    except Exception:
        pass

    if WD_STYLE_TYPE is None:
        return None

    try:
        return doc.styles.add_style(name, style_type)
    except Exception:
        return None


def _set_style_font(
    doc: Any,
    style_name: str,
    *,
    font_name: str | None = None,
    size_pt: float | None = None,
    bold: bool | None = None,
    color: RGBColor | None = None,
    underline: bool | None = None,
) -> None:
    try:
        style = doc.styles[style_name]
    except Exception:
        return

    try:
        font = style.font
        if font_name is not None:
            font.name = font_name
            try:
                font.element.rPr.rFonts.set(qn("w:eastAsia"), font_name)
            except Exception:
                pass
        if size_pt is not None:
            font.size = Pt(size_pt)
        if bold is not None:
            font.bold = bold
        if color is not None:
            font.color.rgb = color
        if underline is not None:
            font.underline = underline
    except Exception:
        return


def _set_style_paragraph(
    doc: Any,
    style_name: str,
    *,
    space_before_pt: float | None = None,
    space_after_pt: float | None = None,
    line_spacing: float | None = None,
) -> None:
    try:
        style = doc.styles[style_name]
    except Exception:
        return

    try:
        fmt = style.paragraph_format
        if space_before_pt is not None:
            fmt.space_before = Pt(space_before_pt)
        if space_after_pt is not None:
            fmt.space_after = Pt(space_after_pt)
        if line_spacing is not None:
            fmt.line_spacing = line_spacing
    except Exception:
        return


def _apply_docx_profile_styles(doc: Any, profile: str) -> None:
    if Document is None:
        return

    # Margins
    try:
        section = doc.sections[0]
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)
    except Exception:
        pass

    navy = RGBColor(0x1C, 0x2E, 0x4A)  # HuleEdu navy
    burgundy = RGBColor(0x4D, 0x15, 0x21)  # HuleEdu burgundy
    black = RGBColor(0, 0, 0)

    if profile == PROFILE_PRINT_BW:
        body_font = "Liberation Serif"
        heading_font = "Liberation Serif"
        code_font = "Liberation Mono"
        body_size = 12
        h1_size, h2_size, h3_size = 20, 14, 12
        heading_color = black
        link_color = black
        body_line_spacing = 1.1
        heading_space_before = (14, 12, 10)
        heading_space_after = (6, 6, 4)
    elif profile == PROFILE_PRINT_COLOR:
        body_font = "Noto Sans"
        heading_font = "Noto Sans"
        code_font = "Liberation Mono"
        body_size = 11
        h1_size, h2_size, h3_size = 22, 16, 13
        heading_color = burgundy
        link_color = burgundy
        body_line_spacing = 1.2
        heading_space_before = (18, 14, 12)
        heading_space_after = (8, 6, 4)
    else:
        body_font = "Noto Serif"
        heading_font = "Noto Sans"
        code_font = "Liberation Mono"
        body_size = 11
        h1_size, h2_size, h3_size = 21, 15, 13
        heading_color = navy
        link_color = navy
        body_line_spacing = 1.15
        heading_space_before = (16, 12, 10)
        heading_space_after = (6, 5, 4)

    code_size = 10.5 if body_size <= 11 else 11

    # Common paragraph styles
    _set_style_font(doc, "Normal", font_name=body_font, size_pt=body_size, bold=False, color=black)
    _set_style_font(
        doc, "Heading 1", font_name=heading_font, size_pt=h1_size, bold=True, color=heading_color
    )
    _set_style_font(
        doc, "Heading 2", font_name=heading_font, size_pt=h2_size, bold=True, color=heading_color
    )
    _set_style_font(
        doc, "Heading 3", font_name=heading_font, size_pt=h3_size, bold=True, color=heading_color
    )

    for s in ("List Paragraph", "List Bullet", "List Number"):
        _set_style_font(doc, s, font_name=body_font, size_pt=body_size, bold=False, color=black)

    # Paragraph spacing + line height
    _set_style_paragraph(
        doc, "Normal", space_before_pt=0, space_after_pt=6, line_spacing=body_line_spacing
    )
    _set_style_paragraph(
        doc,
        "Heading 1",
        space_before_pt=heading_space_before[0],
        space_after_pt=heading_space_after[0],
        line_spacing=1.1,
    )
    _set_style_paragraph(
        doc,
        "Heading 2",
        space_before_pt=heading_space_before[1],
        space_after_pt=heading_space_after[1],
        line_spacing=1.1,
    )
    _set_style_paragraph(
        doc,
        "Heading 3",
        space_before_pt=heading_space_before[2],
        space_after_pt=heading_space_after[2],
        line_spacing=1.1,
    )
    for s in ("List Paragraph", "List Bullet", "List Number"):
        _set_style_paragraph(
            doc, s, space_before_pt=0, space_after_pt=4, line_spacing=body_line_spacing
        )

    # Hyperlinks
    if profile == PROFILE_PRINT_BW:
        _set_style_font(doc, "Hyperlink", color=black, underline=True)
        _set_style_font(doc, "FollowedHyperlink", color=black, underline=True)
    else:
        _set_style_font(doc, "Hyperlink", color=link_color, underline=True)
        _set_style_font(doc, "FollowedHyperlink", color=link_color, underline=True)

    # Code-related styles Pandoc commonly uses in DOCX
    for s in ("Verbatim Char", "Source Code", "Code"):
        _set_style_font(doc, s, font_name=code_font, size_pt=code_size, color=black)
    _set_style_paragraph(doc, "Source Code", space_before_pt=6, space_after_pt=6, line_spacing=1.0)


def _make_reference_docx(profile: str, tmpdir: Path) -> Path:
    """
    Reference doc produced by python-docx only (no extra pandoc subprocess step).
    We explicitly ensure key styles exist, so Pandoc has something to map to.
    """
    ref_path = tmpdir / f"reference_{profile}.docx"
    if Document is None:
        return ref_path

    doc = Document()

    # Ensure styles that matter for "no color" exist
    if WD_STYLE_TYPE is not None:
        _ensure_style(doc, "Hyperlink", WD_STYLE_TYPE.CHARACTER)
        _ensure_style(doc, "FollowedHyperlink", WD_STYLE_TYPE.CHARACTER)
        _ensure_style(doc, "Verbatim Char", WD_STYLE_TYPE.CHARACTER)
        _ensure_style(doc, "Code", WD_STYLE_TYPE.CHARACTER)
        _ensure_style(doc, "Source Code", WD_STYLE_TYPE.PARAGRAPH)

    _apply_docx_profile_styles(doc, profile)
    doc.add_paragraph("Reference document for Pandoc DOCX styling (generated).")
    doc.save(str(ref_path))
    return ref_path


# =========================
# Pandoc conversion
# =========================


def _pandoc_available() -> bool:
    if pypandoc is None:
        return False
    try:
        _ = pypandoc.get_pandoc_version()
        return True
    except Exception:
        return False


def _convert_with_pandoc(
    md_path: Path, out_docx: Path, profile: str, tmpdir: Path
) -> tuple[bool, str]:
    if pypandoc is None:
        return False, "pypandoc saknas."

    reference = _make_reference_docx(profile, tmpdir)
    extra_args: list[str] = []

    if reference.exists():
        extra_args.append(f"--reference-doc={str(reference)}")

    # BW: disable syntax highlighting to avoid color injection in DOCX code spans/blocks
    # (Pandoc supports --syntax-highlighting=none; this is the correct modern knob.)
    if profile == PROFILE_PRINT_BW:
        extra_args.append("--syntax-highlighting=none")

    last_err = ""
    for fmt in ("gfm", "markdown"):
        try:
            pypandoc.convert_file(
                str(md_path),
                to="docx",
                format=fmt,
                outputfile=str(out_docx),
                extra_args=extra_args,
            )
            return (
                True,
                f"Pandoc OK (format={fmt}, reference-doc={'ja' if reference.exists() else 'nej'}).",
            )
        except Exception as e:
            last_err = str(e)

    return False, f"Pandoc misslyckades: {last_err}"


# =========================
# Entrypoint
# =========================


def run_tool(input_dir: str, output_dir: str) -> dict:
    outputs: list[dict] = []

    input_root = Path(input_dir)
    out_root = Path(output_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    settings, settings_src = _load_settings_from_memory()
    inputs, inputs_src = _load_inputs_from_env()

    # If pandoc is not available: fail explicitly (no “mystery markdown” output)
    if not _pandoc_available():
        return contract_v2(
            [
                o_notice(
                    "error",
                    "Pandoc är inte tillgängligt i runnern. DOCX-konvertering kan inte köras.",
                ),
                o_json("Debug", {"inputs_src": inputs_src, "settings_src": settings_src}),
            ]
        )

    # --- Settings defaults (persistent) ---
    global_default_profile = _coerce_profile(settings.get("default_profile"), PROFILE_STANDARD)
    global_enable_comparison = _as_bool(settings.get("enable_comparison"), False)
    global_cmp_profile_raw = _as_str(settings.get("comparison_profile"), "").strip()
    global_cmp_profile = (
        global_cmp_profile_raw
        if global_cmp_profile_raw in {PROFILE_STANDARD, PROFILE_PRINT_BW, PROFILE_PRINT_COLOR}
        else ""
    )
    global_cmp_scope = _coerce_scope(settings.get("comparison_scope"), SCOPE_FIRST)
    enable_debug_view = _as_bool(settings.get("enable_debug_view"), False)

    # --- Inputs override (per-run) ---
    selected_profile = _coerce_profile(inputs.get("profile"), global_default_profile)
    make_cmp = _as_bool(inputs.get("make_comparison"), global_enable_comparison)

    cmp_profile_in = _as_str(inputs.get("comparison_profile"), "").strip()
    if cmp_profile_in in {"auto", "use_default", "default", ""}:
        cmp_profile_in = ""
    cmp_profile = (
        cmp_profile_in
        if cmp_profile_in in {PROFILE_STANDARD, PROFILE_PRINT_BW, PROFILE_PRINT_COLOR}
        else (global_cmp_profile or "")
    )

    cmp_scope_in = _as_str(inputs.get("comparison_scope"), "").strip()
    cmp_scope = _coerce_scope(cmp_scope_in, global_cmp_scope)

    cmp_profile_final = cmp_profile if cmp_profile else None
    if make_cmp and (cmp_profile_final is None or cmp_profile_final == selected_profile):
        cmp_profile_final = (
            PROFILE_PRINT_BW if selected_profile != PROFILE_PRINT_BW else PROFILE_STANDARD
        )

    # --- Resolve files ---
    files: list[dict] = []
    if "markdown_files" in inputs:
        files = _normalize_markdown_files(input_root, inputs.get("markdown_files"))
    if not files:
        files = _scan_input_dir_for_markdown(input_root)

    if not files:
        return contract_v2(
            [
                o_notice("error", "Inga markdown-filer hittades i input_dir."),
                o_json(
                    "Debug",
                    {"inputs_src": inputs_src, "settings_src": settings_src, "inputs": inputs},
                ),
            ]
        )

    outputs.append(
        o_markdown(
            "# Markdown → DOCX\n\n"
            f"**Inputs-källa:** `{inputs_src}`  \n"
            f"**Settings-källa:** `{settings_src}`  \n"
            f"**Profil (global):** {_profile_label(global_default_profile)}  \n"
            f"**Profil (körning):** {_profile_label(selected_profile)}  \n"
            f"{_profile_desc(selected_profile)}  \n"
            f"**Jämförelse (global):** {'på' if global_enable_comparison else 'av'}  \n"
            f"**Jämförelse (körning):** {'på' if make_cmp else 'av'}  \n"
            f"**Antal filer:** {len(files)}\n"
        )
    )

    results: list[dict] = []
    notes: list[str] = []

    with tempfile.TemporaryDirectory(prefix="md2docx_") as td:
        tmpdir = Path(td)

        def convert_one(src: dict, profile: str, suffix: str) -> None:
            src_path: Path = src["path"]
            src_name = str(src.get("name") or src_path.name)

            base = _safe_stem(Path(src_name).stem)
            out_name = f"{base}{suffix}.docx"
            out_tmp = tmpdir / out_name

            ok, msg = _convert_with_pandoc(src_path, out_tmp, profile, tmpdir)

            if ok and out_tmp.exists():
                final_path = _unique_path(out_root, out_name)
                shutil.copyfile(out_tmp, final_path)
                size = final_path.stat().st_size
                results.append(
                    {
                        "source": src_name,
                        "profile": _profile_label(profile),
                        "output": final_path.name,
                        "size": _human_size(size),
                        "status": "OK",
                    }
                )
                notes.append(f"{src_name} ({profile}): {msg}")
            else:
                results.append(
                    {
                        "source": src_name,
                        "profile": _profile_label(profile),
                        "output": out_name,
                        "size": "-",
                        "status": f"Fel: {msg}",
                    }
                )
                notes.append(f"{src_name} ({profile}): FEL: {msg}")

        for f in files:
            convert_one(f, selected_profile, suffix=f"__{selected_profile}")

        if make_cmp and cmp_profile_final:
            targets = files if cmp_scope == SCOPE_ALL else files[:1]
            for f in targets:
                convert_one(f, cmp_profile_final, suffix=f"__{cmp_profile_final}")

    outputs.append(
        o_table(
            "Resultat",
            columns=[
                {"key": "source", "label": "Källa (.md)"},
                {"key": "profile", "label": "Profil"},
                {"key": "output", "label": "Utfil (.docx)"},
                {"key": "size", "label": "Storlek"},
                {"key": "status", "label": "Status"},
            ],
            rows=results,
        )
    )

    outputs.append(
        o_markdown("## Konverteringsnoteringar\n\n```text\n" + "\n".join(notes[:200]) + "\n```")
    )

    if enable_debug_view:
        outputs.append(
            o_json(
                "Debug",
                {
                    "inputs_src": inputs_src,
                    "settings_src": settings_src,
                    "inputs_raw": inputs,
                    "settings_raw": settings,
                    "resolved": {
                        "global_default_profile": global_default_profile,
                        "selected_profile": selected_profile,
                        "make_comparison": make_cmp,
                        "comparison_profile_final": cmp_profile_final,
                        "comparison_scope": cmp_scope,
                    },
                },
            )
        )

    return contract_v2(outputs)
