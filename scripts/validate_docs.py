from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

type YamlMapping = dict[str, object]

CONTRACT_PATH = Path("docs/_meta/docs-contract.yaml")
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass(frozen=True)
class Violation:
    path: str
    message: str


def normalize_path(path: Path) -> str:
    return str(path).replace("\\", "/")


def _to_str_key_mapping(value: object) -> YamlMapping | None:
    if not isinstance(value, dict):
        return None
    return {str(k): v for k, v in value.items()}


def load_contract() -> YamlMapping:
    if not CONTRACT_PATH.exists():
        raise SystemExit(
            f"[docs-validate] Missing contract: {CONTRACT_PATH}\n"
            "Create it or restore it. This file is the source of truth."
        )

    raw_contract = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8")) or {}
    contract = _to_str_key_mapping(raw_contract)
    if contract is None:
        raise SystemExit("[docs-validate] Contract must parse to a YAML mapping/object.")

    if "types" not in contract:
        raise SystemExit("[docs-validate] Contract missing required key: types")
    if "frontmatter" not in contract:
        raise SystemExit("[docs-validate] Contract missing required key: frontmatter")

    return contract


def parse_frontmatter(text: str) -> tuple[YamlMapping | None, str | None]:
    if not text.startswith("---"):
        return None, "Missing YAML frontmatter block at top of file."

    match = FRONTMATTER_RE.match(text)
    if not match:
        return None, "Frontmatter not closed. Expected a second '---' delimiter."

    try:
        raw_frontmatter = yaml.safe_load(match.group(1)) or {}
    except Exception as exc:  # noqa: BLE001
        return None, f"Invalid YAML in frontmatter: {exc}"

    frontmatter = _to_str_key_mapping(raw_frontmatter)
    if frontmatter is None:
        return None, "Frontmatter must parse to a YAML mapping/object."
    return frontmatter, None


def is_iso_date(value: object) -> bool:
    if isinstance(value, date):
        return True
    if isinstance(value, str):
        try:
            date.fromisoformat(value)
            return True
        except ValueError:
            return False
    return False


def top_level_folder(path: Path) -> str | None:
    parts = path.parts
    # expected: docs/<top>/...
    if len(parts) >= 2 and parts[0] == "docs":
        return parts[1]
    return None


def validate_path_rules(path: Path, contract: YamlMapping) -> list[Violation]:
    violations: list[Violation] = []

    if not path.parts or path.parts[0] != "docs":
        return violations

    norm = normalize_path(path)
    allowed_top = set(contract.get("allowed_top_level", []))

    # docs root files: only those explicitly exempt
    if len(path.parts) == 2:
        if norm not in set(contract.get("frontmatter_exempt", [])):
            violations.append(
                Violation(norm, "Docs root files are not allowed (except exempt list).")
            )
        return violations

    top = top_level_folder(path)
    if top is None or top not in allowed_top:
        violations.append(
            Violation(
                norm,
                f"Illegal docs parent folder: '{top}'. Allowed: {sorted(allowed_top)}.",
            )
        )

    return violations


def match_type_by_folder(path: Path, contract: YamlMapping) -> str | None:
    norm = normalize_path(path)
    for doc_type, rule in contract["types"].items():
        folder = str(rule["folder"]).rstrip("/").replace("\\", "/")
        if norm.startswith(folder + "/"):
            return str(doc_type)
    return None


def expected_id_from_filename(doc_type: str, filename: str) -> str | None:
    if doc_type == "adr":
        match = re.match(r"^adr-(\d{4})-[a-z0-9-]+\.md$", filename)
        return f"ADR-{match.group(1)}" if match else None
    if doc_type == "sprint":
        match = re.match(r"^sprint-(\d{4}-\d{2}-\d{2})-[a-z0-9-]+\.md$", filename)
        return f"SPR-{match.group(1)}" if match else None
    if doc_type == "prd":
        match = re.match(r"^prd-([a-z0-9-]+)-v(\d+\.\d+(?:\.\d+)?)\.md$", filename)
        return f"PRD-{match.group(1)}-v{match.group(2)}" if match else None
    if doc_type == "release":
        match = re.match(r"^release-([a-z0-9-]+)-v(\d+\.\d+(?:\.\d+)?)\.md$", filename)
        return f"REL-{match.group(1)}-v{match.group(2)}" if match else None
    if doc_type == "epic":
        match = re.match(r"^epic-(\d{2})-[a-z0-9-]+\.md$", filename)
        return f"EPIC-{match.group(1)}" if match else None
    if doc_type == "story":
        match = re.match(r"^story-(\d{2})-(\d{2})-[a-z0-9-]+\.md$", filename)
        return f"ST-{match.group(1)}-{match.group(2)}" if match else None
    if doc_type == "runbook":
        match = re.match(r"^runbook-([a-z0-9-]+)\.md$", filename)
        return f"RUN-{match.group(1)}" if match else None
    if doc_type == "reference":
        match = re.match(r"^ref-([a-z0-9-]+)\.md$", filename)
        return f"REF-{match.group(1)}" if match else None
    if doc_type == "template":
        match = re.match(r"^template-([a-z0-9-]+)\.md$", filename)
        return f"TPL-{match.group(1)}" if match else None
    return None


def validate_doc(path: Path, contract: YamlMapping) -> list[Violation]:
    violations: list[Violation] = []
    norm = normalize_path(path)

    violations.extend(validate_path_rules(path, contract))
    if violations:
        return violations

    exempt = set(contract.get("frontmatter_exempt", []))
    if norm in exempt:
        return violations

    doc_type = match_type_by_folder(path, contract)
    if doc_type is None:
        violations.append(Violation(norm, "Unable to determine document type from folder."))
        return violations

    rule = contract["types"][doc_type]

    # filename regex
    filename_regex = str(rule["filename_regex"])
    if not re.match(filename_regex, path.name):
        violations.append(
            Violation(norm, f"Filename does not match {doc_type} convention: {filename_regex}")
        )

    text = path.read_text(encoding="utf-8", errors="replace")
    fm, err = parse_frontmatter(text)
    if err:
        violations.append(Violation(norm, err))
        return violations
    assert fm is not None

    common_req = contract["frontmatter"].get("common_required", [])
    for key in common_req:
        if key not in fm:
            violations.append(Violation(norm, f"Missing required frontmatter key: '{key}'"))

    if fm.get("type") != doc_type:
        violations.append(
            Violation(norm, f"Frontmatter type '{fm.get('type')}' must equal '{doc_type}'.")
        )

    id_regex = str(rule["id_regex"])
    if "id" in fm and not re.match(id_regex, str(fm["id"])):
        violations.append(Violation(norm, f"Frontmatter id invalid for {doc_type}: {id_regex}"))

    expected_id = expected_id_from_filename(doc_type, path.name)
    if expected_id and "id" in fm and str(fm["id"]) != expected_id:
        violations.append(
            Violation(norm, f"Frontmatter id must match filename: expected '{expected_id}'.")
        )

    allowed_status = set(rule.get("status_allowed", []))
    if "status" in fm and fm["status"] not in allowed_status:
        violations.append(
            Violation(
                norm,
                f"Invalid status '{fm['status']}'. Allowed: {sorted(allowed_status)}.",
            )
        )

    if "created" in fm and not is_iso_date(fm["created"]):
        violations.append(Violation(norm, "Frontmatter 'created' must be YYYY-MM-DD."))
    if "updated" in fm and not is_iso_date(fm["updated"]):
        violations.append(Violation(norm, "Frontmatter 'updated' must be YYYY-MM-DD."))

    owners = fm.get("owners")
    if owners is None:
        pass
    elif isinstance(owners, str):
        pass
    elif isinstance(owners, list) and all(isinstance(item, str) for item in owners):
        pass
    else:
        violations.append(
            Violation(norm, "Frontmatter 'owners' must be string or list of strings.")
        )

    for key in rule.get("required", []):
        if key not in fm:
            violations.append(Violation(norm, f"Missing required '{doc_type}' key: '{key}'"))

    common_opt = set(contract["frontmatter"].get("common_optional", []))
    allowed_keys = (
        set(common_req) | common_opt | set(rule.get("required", [])) | set(rule.get("optional", []))
    )
    unknown = sorted(set(fm.keys()) - allowed_keys)
    if unknown:
        violations.append(
            Violation(
                norm,
                f"Unknown frontmatter keys not allowed: {unknown}. Update contract if needed.",
            )
        )

    if doc_type == "sprint":
        # Sprint-specific validation is intentionally shallow (frontmatter only), but strict on types.
        starts = fm.get("starts")
        ends = fm.get("ends")
        if starts is not None and not is_iso_date(starts):
            violations.append(Violation(norm, "Frontmatter 'starts' must be YYYY-MM-DD."))
        if ends is not None and not is_iso_date(ends):
            violations.append(Violation(norm, "Frontmatter 'ends' must be YYYY-MM-DD."))
        if isinstance(starts, str) and isinstance(ends, str):
            try:
                start_date = date.fromisoformat(starts)
                end_date = date.fromisoformat(ends)
                if start_date > end_date:
                    violations.append(
                        Violation(norm, "Frontmatter 'starts' must be on/before 'ends'.")
                    )
            except ValueError:
                # Covered by is_iso_date validation above.
                pass

        objective = fm.get("objective")
        if objective is not None and not isinstance(objective, str):
            violations.append(Violation(norm, "Frontmatter 'objective' must be a string."))

        for key in ("stories", "epics", "adrs"):
            value = fm.get(key)
            if value is None:
                continue
            if not (isinstance(value, list) and all(isinstance(item, str) for item in value)):
                violations.append(
                    Violation(norm, f"Frontmatter '{key}' must be a list of strings.")
                )

        prd = fm.get("prd")
        if prd is not None and not isinstance(prd, str):
            violations.append(Violation(norm, "Frontmatter 'prd' must be a string."))

    if doc_type == "release":
        released = fm.get("released")
        if released is not None and not is_iso_date(released):
            violations.append(Violation(norm, "Frontmatter 'released' must be YYYY-MM-DD."))

    return violations


def iter_docs(files: list[str]) -> list[Path]:
    if files:
        paths: list[Path] = []
        for file in files:
            path = Path(file)
            if path.suffix != ".md":
                continue
            if not path.parts or path.parts[0] != "docs":
                continue
            paths.append(path)
        return paths

    docs_root = Path("docs")
    if not docs_root.exists():
        return []
    return list(docs_root.rglob("*.md"))


def main(argv: list[str]) -> int:
    contract = load_contract()
    paths = iter_docs(argv[1:])
    violations: list[Violation] = []

    for path in paths:
        if not path.exists():
            continue
        violations.extend(validate_doc(path, contract))

    if violations:
        print("\n[docs-validate] Contract violations found:\n")
        for violation in violations:
            print(f"- {violation.path}: {violation.message}")
        print(
            "\nFix the issues above.\n"
            "Rules: docs/_meta/docs-contract.yaml\n"
            "Templates: docs/templates/\n"
            "Validator: scripts/validate_docs.py\n"
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
