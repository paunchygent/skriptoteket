from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

import yaml

type YamlMapping = dict[str, object]

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
DEFAULT_SKILLS_ROOTS = (Path(".claude/skills"),)
IGNORE_DIR_NAMES = {".git", ".venv", "__pycache__", "node_modules"}


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    location: Path


@dataclass(frozen=True)
class Violation:
    path: Path
    message: str


def normalize_path(path: Path) -> str:
    return str(path).replace("\\", "/")


def _to_str_key_mapping(value: object) -> YamlMapping | None:
    if not isinstance(value, dict):
        return None
    return {str(k): v for k, v in value.items()}


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


def _iter_skill_files(root: Path) -> list[Path]:
    if not root.exists():
        return []

    skill_files: list[Path] = []
    for path in root.rglob("SKILL.md"):
        if any(part in IGNORE_DIR_NAMES for part in path.parts):
            continue
        if not path.is_file():
            continue
        skill_files.append(path)
    return skill_files


def discover_skills(roots: list[Path], absolute_locations: bool) -> tuple[list[Skill], list[Violation]]:
    skills: list[Skill] = []
    violations: list[Violation] = []

    for root in roots:
        if not root.exists():
            violations.append(Violation(root, "Skills root does not exist."))
            continue
        if not root.is_dir():
            violations.append(Violation(root, "Skills root is not a directory."))
            continue

        for skill_file in _iter_skill_files(root):
            text = skill_file.read_text(encoding="utf-8", errors="replace")
            fm, err = parse_frontmatter(text)
            if err:
                violations.append(Violation(skill_file, err))
                continue
            assert fm is not None

            name = fm.get("name")
            description = fm.get("description")
            if not isinstance(name, str) or not name.strip():
                violations.append(Violation(skill_file, "Frontmatter must include a non-empty 'name' string."))
                continue
            if not isinstance(description, str) or not description.strip():
                violations.append(
                    Violation(skill_file, "Frontmatter must include a non-empty 'description' string.")
                )
                continue

            location = skill_file.resolve() if absolute_locations else skill_file
            skills.append(
                Skill(
                    name=name.strip(),
                    description=" ".join(description.split()),
                    location=location,
                )
            )

    # Enforce unique skill names
    name_to_paths: dict[str, list[Path]] = {}
    for skill in skills:
        name_to_paths.setdefault(skill.name, []).append(skill.location)
    for name, paths in name_to_paths.items():
        if len(paths) > 1:
            path_list = ", ".join(normalize_path(p) for p in paths)
            violations.append(Violation(paths[0], f"Duplicate skill name '{name}' found in: {path_list}"))

    skills.sort(key=lambda skill: skill.name)
    return skills, violations


def render_available_skills_xml(skills: list[Skill]) -> str:
    lines: list[str] = ["<available_skills>"]
    for skill in skills:
        lines.extend(
            [
                "  <skill>",
                f"    <name>{escape(skill.name)}</name>",
                f"    <description>{escape(skill.description)}</description>",
                f"    <location>{escape(normalize_path(skill.location))}</location>",
                "  </skill>",
            ]
        )
    lines.append("</available_skills>")
    return "\n".join(lines)


def render_available_skills_json(skills: list[Skill]) -> str:
    payload = [
        {
            "name": skill.name,
            "description": skill.description,
            "location": normalize_path(skill.location),
        }
        for skill in skills
    ]
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.skills_prompt",
        description="Generate an <available_skills> prompt snippet from SKILL.md files.",
    )
    parser.add_argument(
        "--root",
        dest="roots",
        action="append",
        default=[],
        help="Skills root directory to scan (repeatable). Default: .claude/skills",
    )
    parser.add_argument(
        "--format",
        choices=("xml", "json"),
        default="xml",
        help="Output format (default: xml).",
    )
    parser.add_argument(
        "--relative",
        action="store_true",
        help="Emit relative SKILL.md locations instead of absolute paths.",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Exit non-zero if any skill is invalid (prints violations to stderr).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    roots = [Path(root) for root in args.roots] if args.roots else list(DEFAULT_SKILLS_ROOTS)

    skills, violations = discover_skills(roots=roots, absolute_locations=not args.relative)

    if args.format == "xml":
        print(render_available_skills_xml(skills))
    else:
        print(render_available_skills_json(skills))

    if violations:
        for violation in violations:
            print(f"[skills] {normalize_path(violation.path)}: {violation.message}", file=sys.stderr)
        if args.validate:
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
