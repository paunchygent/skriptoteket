from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pdfplumber

CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
MULTISPACE = re.compile(r"\s+")


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _load_lines(path: Path) -> list[str]:
    lines: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in text.splitlines():
                normalized = CONTROL_CHARS.sub("", line).replace("\u00ad", "")
                normalized = normalized.strip()
                if normalized:
                    lines.append(normalized)
    return lines


def _is_noise_line(line: str) -> bool:
    lowered = line.casefold()
    if lowered.startswith("lista med faroangivelser"):
        return True
    if lowered.startswith("lista på skyddsangivelser"):
        return True
    if lowered.startswith("bilaga") or lowered.startswith("del "):
        return True
    if re.fullmatch(r"\d+", line):
        return True
    return False


def _extract_codes(line: str, prefixes: tuple[str, ...]) -> tuple[list[str], str | None, bool]:
    prefix_pattern = "|".join(prefixes)
    match = re.match(
        rf"^((?:{prefix_pattern})\d{{3}}(?:\s*\+\s*(?:{prefix_pattern})\d{{3}})*)\s*(.*)$",
        line,
    )
    if not match:
        return ([], None, False)
    code_block = match.group(1)
    remainder = match.group(2).strip() if match.group(2) else ""
    codes = [token.strip() for token in re.split(r"\s*\+\s*", code_block) if token.strip()]
    trailing_plus = line.strip().endswith("+")
    if remainder.startswith("+"):
        remainder = remainder.lstrip("+").strip()
        trailing_plus = True
    return (codes, remainder if remainder else None, trailing_plus)


def _join_text(parts: list[str]) -> str:
    merged = ""
    for part in parts:
        if not part:
            continue
        if merged.endswith("-") and part[0:1].isalpha():
            merged = merged[:-1] + part
        else:
            merged = f"{merged} {part}" if merged else part
    merged = CONTROL_CHARS.sub("", merged).replace("\u00ad", "")
    return MULTISPACE.sub(" ", merged).strip()


def _parse_statements(lines: Iterable[str], prefixes: tuple[str, ...]) -> dict[str, str]:
    entries: dict[str, str] = {}
    current_codes: list[str] = []
    current_text: list[str] = []
    pending_codes = False

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if _is_noise_line(line) and not current_codes:
            continue

        codes, text, trailing_plus = _extract_codes(line, prefixes)
        if codes:
            if current_codes and pending_codes:
                current_codes.extend(codes)
                if text:
                    current_text.append(text)
                pending_codes = trailing_plus
                continue
            if current_codes and current_text:
                key = "+".join(current_codes)
                entries[key] = _join_text(current_text)
                current_codes = []
                current_text = []
            current_codes = codes
            pending_codes = trailing_plus or text is None
            if text:
                current_text.append(text)
                pending_codes = trailing_plus
            continue

        if current_codes:
            current_text.append(line)

    if current_codes and current_text:
        key = "+".join(current_codes)
        entries[key] = _join_text(current_text)

    return entries


def _build_payload(
    *,
    h_pdf: Path,
    p_pdf: Path,
    h_url: str | None,
    p_url: str | None,
    supplemental_path: Path | None,
) -> dict:
    h_lines = _load_lines(h_pdf)
    p_lines = _load_lines(p_pdf)

    hazard = _parse_statements(h_lines, ("H", "EUH"))
    precaution = _parse_statements(p_lines, ("P",))
    supplemental = None
    if supplemental_path and supplemental_path.is_file():
        supplemental = json.loads(supplemental_path.read_text(encoding="utf-8"))
        supplemental_hazard = supplemental.get("statements", {}).get("hazard", {})
        supplemental_precaution = supplemental.get("statements", {}).get("precautionary", {})
        for code, text in supplemental_hazard.items():
            if code not in hazard and isinstance(text, str):
                hazard[code] = text
        for code, text in supplemental_precaution.items():
            if code not in precaution and isinstance(text, str):
                precaution[code] = text

    return {
        "version": 1,
        "language": "sv-SE",
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "sources": {
            "h_statements": {
                "path": str(h_pdf),
                "url": h_url,
                "sha256": _sha256(h_pdf),
            },
            "p_statements": {
                "path": str(p_pdf),
                "url": p_url,
                "sha256": _sha256(p_pdf),
            },
        },
        "signal_words": {
            "danger": "Fara",
            "warning": "Varning",
        },
        "statements": {
            "hazard": hazard,
            "precautionary": precaution,
        },
        "supplemental_sources": supplemental.get("sources") if supplemental else [],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--h-pdf", type=Path, required=True)
    parser.add_argument("--p-pdf", type=Path, required=True)
    parser.add_argument("--h-url", type=str, default=None)
    parser.add_argument("--p-url", type=str, default=None)
    parser.add_argument(
        "--supplemental",
        type=Path,
        default=Path("data/clp_sv/supplemental_sv_v1.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/clp_sv/glossary_sv_v1.json"),
    )
    args = parser.parse_args()

    payload = _build_payload(
        h_pdf=args.h_pdf,
        p_pdf=args.p_pdf,
        h_url=args.h_url,
        p_url=args.p_url,
        supplemental_path=args.supplemental,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"Wrote {args.output} ({len(payload['statements']['hazard'])} H/EUH, "
        f"{len(payload['statements']['precautionary'])} P)"
    )


if __name__ == "__main__":
    main()
