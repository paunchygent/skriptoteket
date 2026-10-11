from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from skriptoteket_toolkit import JsonValue, read_inputs, read_settings

from .profiles import (
    PROFILE_PRINT_BW,
    PROFILE_PRINT_COLOR,
    PROFILE_STANDARD,
    SCOPE_ALL,
    SCOPE_FIRST,
)


class MarkdownFile(TypedDict):
    path: Path
    name: str


# =========================
# Platform IO:
# - settings from memory.json
# - per-run inputs from request.json
# =========================


def load_settings_from_memory() -> tuple[dict[str, JsonValue], str]:
    return (read_settings(), "SKRIPTOTEKET_MEMORY_PATH")


def load_inputs_from_env() -> tuple[dict[str, JsonValue], str]:
    return (read_inputs(), "request.json")


# =========================
# Unwrap + coercion helpers
# =========================


def _unwrap_value(v: object) -> object:
    if isinstance(v, dict) and "value" in v:
        return v.get("value")
    return v


def as_bool(v: object, default: bool = False) -> bool:
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


def as_str(v: object, default: str = "") -> str:
    v = _unwrap_value(v)
    return v if isinstance(v, str) else default


def coerce_profile(v: object, default: str) -> str:
    s = as_str(v, default).strip()
    if s in {"use_default", "default", ""}:
        return default
    if s in {PROFILE_STANDARD, PROFILE_PRINT_BW, PROFILE_PRINT_COLOR}:
        return s
    return default


def coerce_scope(v: object, default: str) -> str:
    s = as_str(v, default).strip()
    if s in {SCOPE_FIRST, SCOPE_ALL}:
        return s
    return default


# =========================
# File helpers
# =========================


def _mk_file(path: Path, name: str | None = None) -> MarkdownFile:
    return {"path": path, "name": name or path.name}


def normalize_markdown_files(input_root: Path, value: object) -> list[MarkdownFile]:
    value = _unwrap_value(value)

    def one(v: object) -> list[MarkdownFile]:
        v = _unwrap_value(v)
        if v is None:
            return []
        if isinstance(v, list):
            out: list[MarkdownFile] = []
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
    uniq: list[MarkdownFile] = []
    for f in files:
        k = str(f["path"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(f)
    return uniq


def scan_input_dir_for_markdown(input_root: Path) -> list[MarkdownFile]:
    if not input_root.exists():
        return []
    candidates: list[Path] = []
    for p in input_root.rglob("*"):
        if p.is_file() and p.suffix.lower() in {".md", ".markdown"}:
            candidates.append(p)
    candidates.sort(key=lambda x: x.name.lower())
    return [_mk_file(p) for p in candidates]
