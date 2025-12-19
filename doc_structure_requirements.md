# Nedan är ett “cementerat” **Documentation-as-Code kontrakt** som detta projekt ska följa

(1) följer en mycket vanlig och tydlig repo-konvention,
(2) ger **maskinläsbara regler** för placering/naming/frontmatter,
(3) ger **LLM-instruktioner** som är svåra att missförstå,
(4) blockerar fel via **git pre-commit**.

Jag utgår från att ni vill ha en docs-katalog som kan byggas med standardverktyg (t.ex. MkDocs), där `docs/` är sibling till configfilen, vilket är standardbeteendet. ([mkdocs.org][1])

---

## 1. Canonical docs-struktur (allowlist)

**Regel:** Endast dessa top-level folders får finnas under `docs/`:

```text
docs/
  index.md                # entrypoint (eller README.md om ni föredrar)
  adr/
  prd/
  releases/
  backlog/
    epics/
    stories/
  runbooks/
  reference/
  templates/
  _meta/                  # maskinläsbara kontrakt + schemas
```

**Regel:** Inga nya `docs/<nytt>/...` får introduceras utan att `docs/_meta/docs-contract.yaml` uppdateras (dvs governance via PR).

---

## 2. Docs Contract: naming + frontmatter + placering (maskinläsbart)

Skapa filen: **`docs/_meta/docs-contract.yaml`**

```yaml
version: 1

# Enda tillåtna parent-folders direkt under docs/
allowed_top_level:
  - adr
  - prd
  - releases
  - backlog
  - runbooks
  - reference
  - templates
  - _meta

# Filer som får sakna frontmatter (exakta paths)
frontmatter_exempt:
  - docs/index.md
  - docs/README.md
  - docs/_meta/README.md

frontmatter:
  delimiters: ["---", "---"]
  common_required:
    - type
    - id
    - title
    - status
    - owners
    - created
  common_optional:
    - updated
    - tags
    - links

# Regler per dokumenttyp.
types:
  adr:
    folder: docs/adr
    filename_regex: "^adr-\\d{4}-[a-z0-9-]+\\.md$"
    id_regex: "^ADR-\\d{4}$"
    status_allowed: ["proposed", "accepted", "superseded", "deprecated"]
    required: ["deciders"]
    optional: ["context", "decision", "consequences"]

  prd:
    folder: docs/prd
    filename_regex: "^prd-[a-z0-9-]+-v\\d+\\.\\d+(?:\\.\\d+)?\\.md$"
    id_regex: "^PRD-[a-z0-9-]+-v\\d+\\.\\d+(?:\\.\\d+)?$"
    status_allowed: ["draft", "active", "superseded"]
    required: ["product", "version"]
    optional: ["goals", "non_goals", "metrics"]

  release:
    folder: docs/releases
    filename_regex: "^release-[a-z0-9-]+-v\\d+\\.\\d+(?:\\.\\d+)?\\.md$"
    id_regex: "^REL-[a-z0-9-]+-v\\d+\\.\\d+(?:\\.\\d+)?$"
    status_allowed: ["draft", "published", "superseded"]
    required: ["product", "version"]
    optional: ["released"]

  epic:
    folder: docs/backlog/epics
    filename_regex: "^epic-\\d{2}-[a-z0-9-]+\\.md$"
    id_regex: "^EPIC-\\d{2}$"
    status_allowed: ["proposed", "active", "done", "dropped"]
    required: ["outcome"]
    optional: ["risks", "dependencies"]

  story:
    folder: docs/backlog/stories
    filename_regex: "^story-\\d{2}-\\d{2}-[a-z0-9-]+\\.md$"
    id_regex: "^ST-\\d{2}-\\d{2}$"
    status_allowed: ["ready", "in_progress", "done", "blocked"]
    required: ["epic", "acceptance_criteria"]
    optional: ["ui_impact", "data_impact", "risks", "dependencies"]

  runbook:
    folder: docs/runbooks
    filename_regex: "^runbook-[a-z0-9-]+\\.md$"
    id_regex: "^RUN-[a-z0-9-]+$"
    status_allowed: ["active", "deprecated"]
    required: ["system"]
    optional: ["alerts", "steps", "rollback"]

  reference:
    folder: docs/reference
    filename_regex: "^ref-[a-z0-9-]+\\.md$"
    id_regex: "^REF-[a-z0-9-]+$"
    status_allowed: ["active", "deprecated"]
    required: ["topic"]
    optional: ["examples"]

  template:
    folder: docs/templates
    filename_regex: "^template-[a-z0-9-]+\\.md$"
    id_regex: "^TPL-[a-z0-9-]+$"
    status_allowed: ["active"]
    required: ["for_type"]
    optional: ["notes"]
```

**Kommentar:** ADR-formatet med `Status/Context/Decision/Consequences` är en etablerad standard (Michael Nygard/Cognitect-linjen). ([Cognitect.com][2])

---

## 3. Frontmatter-spec (normativ)

Frontmatter ska alltid ligga först i filen och följa YAML.

Exempel (ADR):

```markdown
---
type: adr
id: ADR-0001
title: "Server-driven UI + HTMX"
status: accepted
owners: ["@platform"]
deciders: ["@tech-lead"]
created: 2025-12-13
updated: 2025-12-13
tags: ["ui", "architecture"]
links:
  - rel: supersedes
    id: ADR-0000
---

## Context
...

## Decision
...

## Consequences
...
```

---

## 4. LLM-signalering: instruktioner som agent-verktyg faktiskt läser

### 4.1 Root: `AGENTS.md` (generiskt för alla agenter)

Skapa **`AGENTS.md`** i repo-roten:

```markdown
# Agent Instructions (Repository Contract)

## Non-negotiable constraints
1. DO NOT create new top-level directories under `docs/` or anywhere else.
2. Documentation files MUST comply with `docs/_meta/docs-contract.yaml`.
3. Every documentation Markdown file under `docs/` MUST include YAML frontmatter unless explicitly exempt in the contract.
4. Naming MUST match the regex for its document type in the contract.
5. If you need a new doc type or folder: propose an ADR/PRD change; do not implement the folder.

## Where to find the rules
- Contract: `docs/_meta/docs-contract.yaml`
- Templates: `docs/templates/`
- Validator: `scripts/validate_docs.py`

## Working procedure for docs changes
- Start from the closest template in `docs/templates/`.
- Keep `id` consistent with filename (validator enforces this).
- Keep `created/updated` in ISO-8601 date format (YYYY-MM-DD).
```

### 4.2 GitHub Copilot: `.github/copilot-instructions.md`

GitHub stödjer repo-instruktioner via `.github/copilot-instructions.md`. ([GitHub Docs][3])
Skapa filen:

```markdown
# Repository instructions for Copilot

Follow `AGENTS.md`.

Documentation contract:
- MUST follow `docs/_meta/docs-contract.yaml`
- MUST NOT create new parent folders
- MUST include YAML frontmatter for docs (unless exempt)
- MUST follow naming regex per document type

Before proposing a change:
- Run: `pdm run docs-validate`
```

### 4.3 Agent-hjälpfiler: `.agent/` (sessioner + handoff)

Utöver `docs/` (produkt/arkitektur) finns en liten agent-mapp för att göra arbetet **reproducerbart mellan sessioner**:

```text
.agent/
  readme-first.md                          # Start här (vad ska läsas, var ska kod läggas, kommandon)
  handoff.md                               # Uppdateras i slutet av varje session
  next-session-instruction-prompt-template.md  # Prompt-mall för nästa session
  rules/                                   # Normativa kodregler (index i 000-rule-index.md)
  AGENTS.md                                # Kort arkitekturöversikt för agenter
```

**Regel:** Dessa filer får aldrig innehålla hemligheter (API-nycklar, tokens, personuppgifter).

---

## 5. Pre-commit: blockera fel placering + fel frontmatter + fel namn

`pre-commit` är standardlösningen för att hantera hooks repeterbart via configfil. ([pre-commit.com][4])

### 5.1 Lägg till dev dependency och PDM scripts

I `pyproject.toml` (dev deps + scripts):

```toml
[project.optional-dependencies]
dev = [
  "pytest>=8.0",
  "ruff>=0.5",
  "pre-commit>=3.7",
]

[tool.pdm.scripts]
docs-validate = "python scripts/validate_docs.py"
```

### 5.2 `.pre-commit-config.yaml`

Skapa **`.pre-commit-config.yaml`**:

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: end-of-file-fixer
      - id: trailing-whitespace
      - id: check-yaml

  - repo: local
    hooks:
      - id: docs-contract-validate
        name: Docs contract validate (placement + naming + frontmatter)
        entry: pdm run docs-validate
        language: system
        files: ^docs/.*\.md$
        pass_filenames: true
```

### 5.3 Validator: `scripts/validate_docs.py`

Skapa **`scripts/validate_docs.py`**:

```python
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml


CONTRACT_PATH = Path("docs/_meta/docs-contract.yaml")


FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass(frozen=True)
class Violation:
    path: str
    message: str


def load_contract() -> dict[str, Any]:
    if not CONTRACT_PATH.exists():
        raise SystemExit(
            f"[docs-validate] Missing contract: {CONTRACT_PATH}\n"
            f"Create it or restore it. This file is the source of truth."
        )
    data = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8")) or {}
    if "types" not in data:
        raise SystemExit("[docs-validate] Contract missing required key: types")
    return data


def parse_frontmatter(text: str) -> tuple[dict[str, Any] | None, str | None]:
    if not text.startswith("---"):
        return None, "Missing YAML frontmatter block at top of file."
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None, "Frontmatter not closed. Expected a second '---' delimiter."
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except Exception as e:  # noqa: BLE001
        return None, f"Invalid YAML in frontmatter: {e}"
    if not isinstance(fm, dict):
        return None, "Frontmatter must parse to a YAML mapping/object."
    return fm, None


def is_iso_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def top_level_folder(path: Path) -> str | None:
    parts = path.parts
    # expect: docs/<top>/...
    if len(parts) >= 2 and parts[0] == "docs":
        return parts[1]
    return None


def validate_path_rules(p: Path, contract: dict[str, Any]) -> list[Violation]:
    v: list[Violation] = []

    if p.parts[0] != "docs":
        return v

    top = top_level_folder(p)
    allowed_top = set(contract.get("allowed_top_level", []))

    # docs root files: only those in exempt list
    if len(p.parts) == 2:
        # docs/<file>
        if str(p).replace("\\", "/") not in set(contract.get("frontmatter_exempt", [])):
            v.append(Violation(str(p), "Docs root files are not allowed (except exempt list)."))
        return v

    if top is None or top not in allowed_top:
        v.append(
            Violation(
                str(p),
                f"Illegal docs parent folder: '{top}'. Allowed: {sorted(allowed_top)}.",
            )
        )
    return v


def match_type_by_folder(p: Path, contract: dict[str, Any]) -> str | None:
    # Determine doc type by the folder rule in contract.
    norm = str(p).replace("\\", "/")
    for doc_type, rule in contract["types"].items():
        folder = rule["folder"].rstrip("/")
        if norm.startswith(folder + "/"):
            return doc_type
    return None


def validate_doc(p: Path, contract: dict[str, Any]) -> list[Violation]:
    violations: list[Violation] = []
    norm = str(p).replace("\\", "/")

    violations.extend(validate_path_rules(p, contract))
    if violations:
        return violations

    exempt = set(contract.get("frontmatter_exempt", []))
    if norm in exempt:
        return violations

    doc_type = match_type_by_folder(p, contract)
    if doc_type is None:
        violations.append(Violation(norm, "Unable to determine document type from folder."))
        return violations

    rule = contract["types"][doc_type]

    # filename regex
    if not re.match(rule["filename_regex"], p.name):
        violations.append(
            Violation(
                norm,
                f"Filename does not match {doc_type} convention: {rule['filename_regex']}",
            )
        )

    text = p.read_text(encoding="utf-8", errors="replace")
    fm, err = parse_frontmatter(text)
    if err:
        violations.append(Violation(norm, err))
        return violations

    # common required keys
    common_req = contract["frontmatter"].get("common_required", [])
    for key in common_req:
        if key not in fm:
            violations.append(Violation(norm, f"Missing required frontmatter key: '{key}'"))

    # type must match
    if fm.get("type") != doc_type:
        violations.append(
            Violation(norm, f"Frontmatter type '{fm.get('type')}' must equal '{doc_type}'.")
        )

    # id regex
    id_regex = rule["id_regex"]
    if "id" in fm and not re.match(id_regex, str(fm["id"])):
        violations.append(Violation(norm, f"Frontmatter id invalid for {doc_type}: {id_regex}"))

    # status allowed
    allowed_status = set(rule.get("status_allowed", []))
    if "status" in fm and fm["status"] not in allowed_status:
        violations.append(
            Violation(
                norm,
                f"Invalid status '{fm['status']}'. Allowed: {sorted(allowed_status)}.",
            )
        )

    # created/updated date format
    if "created" in fm and not is_iso_date(fm["created"]):
        violations.append(Violation(norm, "Frontmatter 'created' must be YYYY-MM-DD."))
    if "updated" in fm and not is_iso_date(fm["updated"]):
        violations.append(Violation(norm, "Frontmatter 'updated' must be YYYY-MM-DD."))

    # owners must be string or list[str]
    owners = fm.get("owners")
    if owners is None:
        pass
    elif isinstance(owners, str):
        pass
    elif isinstance(owners, list) and all(isinstance(x, str) for x in owners):
        pass
    else:
        violations.append(Violation(norm, "Frontmatter 'owners' must be string or list of strings."))

    # type-specific required keys
    for key in rule.get("required", []):
        if key not in fm:
            violations.append(Violation(norm, f"Missing required '{doc_type}' key: '{key}'"))

    # tighten unknown keys (optional but recommended)
    common_opt = set(contract["frontmatter"].get("common_optional", []))
    allowed_keys = set(common_req) | common_opt | set(rule.get("required", [])) | set(rule.get("optional", []))
    unknown = sorted(set(fm.keys()) - allowed_keys)
    if unknown:
        violations.append(
            Violation(
                norm,
                f"Unknown frontmatter keys not allowed: {unknown}. "
                f"Update contract if needed.",
            )
        )

    return violations


def iter_docs(files: list[str]) -> list[Path]:
    if files:
        return [Path(f) for f in files if f.startswith("docs/") and f.endswith(".md")]
    return list(Path("docs").rglob("*.md"))


def main(argv: list[str]) -> int:
    contract = load_contract()
    paths = iter_docs(argv[1:])
    violations: list[Violation] = []

    for p in paths:
        if not p.exists():
            continue
        violations.extend(validate_doc(p, contract))

    if violations:
        print("\n[docs-validate] Contract violations found:\n")
        for v in violations:
            print(f"- {v.path}: {v.message}")
        print(
            "\nFix the issues above.\n"
            f"Rules: docs/_meta/docs-contract.yaml\n"
            f"Templates: docs/templates/\n"
            f"Validator: scripts/validate_docs.py\n"
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

### 5.4 Installera hooks (developer setup)

Efter `pdm install`:

```bash
pdm run pre-commit install
```

---

## 6. Templates (för att minska fel och styra LLM beteende)

Skapa minst dessa filer i `docs/templates/` (en per typ), t.ex.:

**`docs/templates/template-adr.md`**

```markdown
---
type: template
id: TPL-adr
title: "ADR template"
status: active
owners: ["@platform"]
created: 2025-12-13
for_type: adr
---

# ADR-0000: Title

---
type: adr
id: ADR-0000
title: "Title"
status: proposed
owners: ["@platform"]
deciders: ["@tech-lead"]
created: 2025-12-13
---

## Context
## Decision
## Consequences
```

Detta gör det trivialt för både människor och LLM:er att “copy → fill” utan att bryta kontraktet.

---

## 7. Rekommenderad CI-spegel (så att reglerna inte kan kringgås)

Utöver pre-commit: kör samma validering i CI, exempelvis:

```bash
pdm run docs-validate
```

Detta är samma princip som pre-commit bygger på: alla hooks måste passera innan en ändring accepteras. ([pre-commit.com][4])

---

### Compliance score

Bias: 10/10, Directness: 10/10, Penalty: 0 → Final: 10/10

[1]: https://www.mkdocs.org/user-guide/writing-your-docs/?utm_source=chatgpt.com "Writing Your Docs"
[2]: https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions?utm_source=chatgpt.com "Documenting Architecture Decisions - Cognitect.com"
[3]: https://docs.github.com/copilot/customizing-copilot/adding-custom-instructions-for-github-copilot?utm_source=chatgpt.com "Adding repository custom instructions for GitHub Copilot"
[4]: https://pre-commit.com/?utm_source=chatgpt.com "pre-commit"
