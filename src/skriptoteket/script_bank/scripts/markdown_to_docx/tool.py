from __future__ import annotations

import re
import shutil
import tempfile
from pathlib import Path

from skriptoteket_toolkit import JsonValue

from .inputs import (
    MarkdownFile,
    as_bool,
    as_str,
    coerce_profile,
    coerce_scope,
    load_inputs_from_env,
    load_settings_from_memory,
    normalize_markdown_files,
    scan_input_dir_for_markdown,
)
from .profiles import (
    PROFILE_PRINT_BW,
    PROFILE_PRINT_COLOR,
    PROFILE_STANDARD,
    SCOPE_ALL,
    SCOPE_FIRST,
    profile_desc,
    profile_label,
)
from .styling import make_reference_docx

# Optional preinstalled libs
try:
    import pypandoc
except Exception:
    _HAS_PYPANDOC = False
else:
    _HAS_PYPANDOC = True


# =========================
# Contract v2 payload helper
# =========================


def contract_v2(
    outputs: list[dict[str, object]],
    next_actions: list[dict[str, object]] | None = None,
    state: JsonValue = None,
) -> dict[str, object]:
    return {"outputs": outputs, "next_actions": next_actions or [], "state": state}


# =========================
# UI output helpers (dicts)
# =========================


def o_markdown(markdown: str) -> dict[str, object]:
    return {"kind": "markdown", "markdown": markdown}


def o_notice(level: str, message: str) -> dict[str, object]:
    return {"kind": "notice", "level": level, "message": message}


def o_json(title: str, value: JsonValue) -> dict[str, object]:
    return {"kind": "json", "title": title, "value": value}


def o_table(
    title: str | None, columns: list[dict[str, str]], rows: list[dict[str, str]]
) -> dict[str, object]:
    payload: dict[str, object] = {"kind": "table", "columns": columns, "rows": rows}
    if title:
        payload["title"] = title
    return payload


# =========================
# File helpers
# =========================


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


# =========================
# Pandoc conversion
# =========================


def _pandoc_available() -> bool:
    if not _HAS_PYPANDOC:
        return False
    try:
        _ = pypandoc.get_pandoc_version()
        return True
    except Exception:
        return False


def _convert_with_pandoc(
    md_path: Path, out_docx: Path, profile: str, tmpdir: Path
) -> tuple[bool, str]:
    if not _HAS_PYPANDOC:
        return False, "pypandoc saknas."

    reference = make_reference_docx(profile, tmpdir)
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


def run_tool(input_dir: str, output_dir: str) -> dict[str, object]:
    outputs: list[dict[str, object]] = []

    input_root = Path(input_dir)
    out_root = Path(output_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    settings, settings_src = load_settings_from_memory()
    inputs, inputs_src = load_inputs_from_env()

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
    global_default_profile = coerce_profile(settings.get("default_profile"), PROFILE_STANDARD)
    global_enable_comparison = as_bool(settings.get("enable_comparison"), False)
    global_cmp_profile_raw = as_str(settings.get("comparison_profile"), "").strip()
    global_cmp_profile = (
        global_cmp_profile_raw
        if global_cmp_profile_raw in {PROFILE_STANDARD, PROFILE_PRINT_BW, PROFILE_PRINT_COLOR}
        else ""
    )
    global_cmp_scope = coerce_scope(settings.get("comparison_scope"), SCOPE_FIRST)
    enable_debug_view = as_bool(settings.get("enable_debug_view"), False)

    # --- Inputs override (per-run) ---
    selected_profile = coerce_profile(inputs.get("profile"), global_default_profile)
    make_cmp = as_bool(inputs.get("make_comparison"), global_enable_comparison)

    cmp_profile_in = as_str(inputs.get("comparison_profile"), "").strip()
    if cmp_profile_in in {"auto", "use_default", "default", ""}:
        cmp_profile_in = ""
    cmp_profile = (
        cmp_profile_in
        if cmp_profile_in in {PROFILE_STANDARD, PROFILE_PRINT_BW, PROFILE_PRINT_COLOR}
        else (global_cmp_profile or "")
    )

    cmp_scope_in = as_str(inputs.get("comparison_scope"), "").strip()
    cmp_scope = coerce_scope(cmp_scope_in, global_cmp_scope)

    cmp_profile_final = cmp_profile if cmp_profile else None
    if make_cmp and (cmp_profile_final is None or cmp_profile_final == selected_profile):
        cmp_profile_final = (
            PROFILE_PRINT_BW if selected_profile != PROFILE_PRINT_BW else PROFILE_STANDARD
        )

    # --- Resolve files ---
    files: list[MarkdownFile] = []
    if "markdown_files" in inputs:
        files = normalize_markdown_files(input_root, inputs.get("markdown_files"))
    if not files:
        files = scan_input_dir_for_markdown(input_root)

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
            f"**Profil (global):** {profile_label(global_default_profile)}  \n"
            f"**Profil (körning):** {profile_label(selected_profile)}  \n"
            f"{profile_desc(selected_profile)}  \n"
            f"**Jämförelse (global):** {'på' if global_enable_comparison else 'av'}  \n"
            f"**Jämförelse (körning):** {'på' if make_cmp else 'av'}  \n"
            f"**Antal filer:** {len(files)}\n"
        )
    )

    results: list[dict[str, str]] = []
    notes: list[str] = []

    with tempfile.TemporaryDirectory(prefix="md2docx_") as td:
        tmpdir = Path(td)

        def convert_one(src: MarkdownFile, profile: str, suffix: str) -> None:
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
                        "profile": profile_label(profile),
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
                        "profile": profile_label(profile),
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
