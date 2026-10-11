"""One-off move of the eight v1 gold files to the v2 parent structure (TASK-SKRIPT-39-05-03).

A parent is a maximal run of consecutive gold items that share their leading prompt lines
and sit under one section instruction in the source DOCX. The shared lines move into the
parent's ``instruction``; every other byte of every item stays as it was.

Run from the repository root with ``PYTHONPATH=src``:

    python -m scripts.exam_conversion_eval.move_gold_to_parents --summary <summary.md>
    python -m scripts.exam_conversion_eval.move_gold_to_parents --summary <summary.md> --write
    python -m scripts.exam_conversion_eval.move_gold_to_parents --summary <summary.md> --check

The default run only reports. ``--write`` rewrites the gold files and refuses files that
already hold schema v2. ``--check`` validates the moved files against the v1 originals
read from ``--baseline-ref`` and appends its output to the summary.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)

from .gold import GoldExam

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS_DIR = REPO_ROOT / "tests/fixtures/exam_conversion/docx_corpus"
V1 = "exam_conversion_gold_v1"
V2 = "exam_conversion_gold_v2"
CHECK_HEADING = "## Check output"
PARTIAL_LINE_MIN_CHARS = 20

JsonDict = dict[str, Any]

_LIST_LABEL = re.compile(r"^(?:\d+[.)]|[A-Za-z][.)]|Fråga \d+\.)\s+")
_POINT_SUFFIX = re.compile(r"\s*\(\d+(?:[.,]\d+)?\s*(?:points?|poäng)\)\s*$")
_RANGE_LABEL = re.compile(r"^(?P<stem>.*?)(?P<tail>\d+|[A-Za-z])$")


@dataclass
class Finding:
    case: str
    exam: str
    text: str


@dataclass
class ParentInfo:
    label: str
    instruction: tuple[str, ...]
    shared_lines: int
    child_labels: tuple[str, ...]
    child_kinds: tuple[str, ...]
    points: float


@dataclass
class ExamPlan:
    stem: str
    items: list[JsonDict]
    parents: list[ParentInfo] = field(default_factory=list)
    standalone: int = 0
    findings: list[Finding] = field(default_factory=list)
    before_items: int = 0
    before_points: float = 0


def norm_line(line: str) -> str:
    """Compare a gold prompt line with a DOCX line: drop list label, points, blank cells."""
    cells = [cell.strip() for cell in line.split(" | ")]
    kept = [cell for cell in cells if cell and set(cell) != {"_"}]
    text = " | ".join(kept)
    text = _POINT_SUFFIX.sub("", " ".join(text.split()))
    return _LIST_LABEL.sub("", text).strip()


def docx_line_counts(docx_path: Path) -> Counter[str]:
    counts: Counter[str] = Counter()
    for chunk in PythonDocxExamChunker().chunk(content=docx_path.read_bytes()):
        for line in chunk.text.split("\n"):
            key = norm_line(line)
            if key:
                counts[key] += 1
    return counts


def _prompt_lines(item: JsonDict) -> list[str]:
    return str(item["prompt"]).split("\n")


def _first_line_runs(items: Sequence[JsonDict]) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    start = 0
    for index in range(1, len(items) + 1):
        if index == len(items) or (
            _prompt_lines(items[index])[0] != _prompt_lines(items[start])[0]
        ):
            runs.append((start, index))
            start = index
    return runs


def _common_prefix(prompts: Sequence[list[str]]) -> list[str]:
    prefix: list[str] = []
    for position in range(min(len(prompt) for prompt in prompts)):
        line = prompts[0][position]
        if any(prompt[position] != line for prompt in prompts):
            break
        prefix.append(line)
    return prefix


def _parent_label(children: Sequence[JsonDict]) -> str:
    first = _RANGE_LABEL.match(str(children[0]["source_label"]))
    last = _RANGE_LABEL.match(str(children[-1]["source_label"]))
    if first and last and first["stem"] == last["stem"]:
        return f"{first['stem']}{first['tail']}–{last['tail']}"
    return f"{children[0]['source_label']} – {children[-1]['source_label']}"


def _char_prefix(texts: Sequence[str]) -> str:
    prefix = texts[0]
    for text in texts[1:]:
        length = 0
        while length < min(len(prefix), len(text)) and prefix[length] == text[length]:
            length += 1
        prefix = prefix[:length]
    return prefix


def _sum_points(items: Sequence[JsonDict]) -> float:
    return float(sum(item["points"] for item in items if item.get("points") is not None))


def plan_exam(stem: str, gold: JsonDict, docx_counts: Counter[str]) -> ExamPlan:
    items: list[JsonDict] = gold["items"]
    plan = ExamPlan(stem=stem, items=[], before_items=len(items), before_points=_sum_points(items))
    runs = _first_line_runs(items)
    runs_per_first_line = Counter(_prompt_lines(items[start])[0] for start, _ in runs)
    for start, end in runs:
        group = items[start:end]
        if len(group) == 1:
            plan.items.append(group[0])
            plan.standalone += 1
            continue
        parent = _plan_run(plan, items, start, end, runs_per_first_line, docx_counts)
        if parent is None:
            plan.items.extend(group)
            plan.standalone += len(group)
        else:
            plan.items.append(parent)
    return plan


def _plan_run(
    plan: ExamPlan,
    items: Sequence[JsonDict],
    start: int,
    end: int,
    runs_per_first_line: Counter[str],
    docx_counts: Counter[str],
) -> JsonDict | None:
    group = items[start:end]
    labels = "; ".join(str(item["source_label"]) for item in group)
    prompts = [_prompt_lines(item) for item in group]
    shared = _common_prefix(prompts)
    first = shared[0]
    expected = runs_per_first_line[first]
    found = docx_counts[norm_line(first)]
    if found != expected:
        plan.findings.append(
            Finding(
                "d",
                plan.stem,
                f"first shared line {first!r} appears in {found} DOCX place(s) but gold "
                f"holds it in {expected} run(s); run [{labels}] stays standalone",
            )
        )
        return None
    instruction = [first]
    stopped_early = False
    for line in shared[1:]:
        count = docx_counts[norm_line(line)]
        if count != expected:
            plan.findings.append(
                Finding(
                    "b",
                    plan.stem,
                    f"run [{labels}]: shared line {line!r} is in all children but appears in "
                    f"{count} DOCX place(s) for {expected} run(s); it stays in the children",
                )
            )
            stopped_early = True
            break
        instruction.append(line)
    if any(len(prompt) <= len(instruction) for prompt in prompts):
        plan.findings.append(
            Finding("c", plan.stem, f"run [{labels}]: a child prompt would be empty; standalone")
        )
        return None
    kinds = [str(item["kind"]) for item in group]
    if len(set(kinds)) > 1:
        plan.findings.append(
            Finding(
                "a",
                plan.stem,
                "mixed kinds in run "
                + ", ".join(f"{item['source_label']}={item['kind']}" for item in group)
                + f"; shared instruction {instruction!r}; run stays standalone",
            )
        )
        return None
    if not stopped_early:
        _note_partial_sharing(plan, prompts, len(instruction), labels)
    _note_neighbours(plan, items, start, end, instruction[0], labels)
    children = []
    for item, prompt in zip(group, prompts, strict=True):
        child = dict(item)
        child["prompt"] = "\n".join(prompt[len(instruction) :])
        children.append(child)
    label = _parent_label(group)
    plan.parents.append(
        ParentInfo(
            label=label,
            instruction=tuple(instruction),
            shared_lines=len(shared),
            child_labels=tuple(str(item["source_label"]) for item in group),
            child_kinds=tuple(kinds),
            points=_sum_points(group),
        )
    )
    return {
        "kind": "parent",
        "source_label": label,
        "instruction": "\n".join(instruction),
        "children": children,
    }


def _note_partial_sharing(
    plan: ExamPlan, prompts: list[list[str]], taken: int, labels: str
) -> None:
    following = [prompt[taken] for prompt in prompts]
    shared = _char_prefix(following)
    if len(shared) >= PARTIAL_LINE_MIN_CHARS:
        plan.findings.append(
            Finding(
                "b",
                plan.stem,
                f"run [{labels}]: every child's next line starts with the same text inside "
                f"the line, which the line rule leaves in the children: {shared!r}",
            )
        )


def _note_neighbours(
    plan: ExamPlan, items: Sequence[JsonDict], start: int, end: int, first: str, labels: str
) -> None:
    for index in (start - 1, end):
        if 0 <= index < len(items) and first in str(items[index]["prompt"]):
            plan.findings.append(
                Finding(
                    "b",
                    plan.stem,
                    f"run [{labels}]: neighbour {items[index]['source_label']} contains the "
                    f"instruction {first!r} but not as its first line",
                )
            )


def _dump(data: JsonDict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def build_plans(gold_dir: Path, corpus_dir: Path) -> list[tuple[Path, JsonDict, ExamPlan]]:
    result = []
    for path in sorted(gold_dir.glob("*.json")):
        gold = json.loads(path.read_text(encoding="utf-8"))
        if gold["schema_version"] != V1:
            raise SystemExit(f"{path.name} is already {gold['schema_version']}; refusing to move")
        counts = docx_line_counts(corpus_dir / gold["source_filename"])
        result.append((path, gold, plan_exam(path.stem, gold, counts)))
    return result


def moved_document(gold: JsonDict, plan: ExamPlan) -> JsonDict:
    moved = dict(gold)
    moved["schema_version"] = V2
    moved["items"] = plan.items
    return moved


def _points_text(value: float) -> str:
    return str(int(value)) if value == int(value) else str(value)


def render_summary(plans: Sequence[ExamPlan]) -> str:
    out = ["# Gold move to parents: summary", ""]
    ordered = [f for case in "abcd" for plan in plans for f in plan.findings if f.case == case]
    titles = {
        "a": "(a) Runs with mixed kinds (stop condition, ST-SKRIPT-39-06 P4)",
        "b": "(b) Shared text the DOCX does not carry as one section instruction",
        "c": "(c) Children whose prompt would become empty",
        "d": "(d) DOCX instruction counts that differ from gold runs",
    }
    out.append("## Cases")
    for case, title in titles.items():
        out += ["", f"### {title}", ""]
        found = [f for f in ordered if f.case == case]
        out += [f"- `{f.exam}`: {f.text}" for f in found] or ["- None."]
    out += ["", "## Per exam"]
    total_before = [0, 0.0]
    total_after = [0, 0.0]
    for plan in plans:
        children = sum(len(p.child_labels) for p in plan.parents)
        points = sum(p.points for p in plan.parents) + _sum_points(
            [i for i in plan.items if i.get("kind") != "parent"]
        )
        out += [
            "",
            f"### `{plan.stem}`",
            "",
            f"- Before: {plan.before_items} items, {_points_text(plan.before_points)} points.",
            f"- After: {len(plan.parents)} parents holding {children} children, "
            f"{plan.standalone} standalone items; {children + plan.standalone} questions, "
            f"{_points_text(points)} points.",
        ]
        for parent in plan.parents:
            out += [
                "",
                f"- Parent `{parent.label}`: {len(parent.child_labels)} children "
                f"({', '.join(sorted(set(parent.child_kinds)))}), "
                f"{_points_text(parent.points)} points.",
                f"  - Children: {'; '.join(parent.child_labels)}",
                f"  - Shared prompt lines: {parent.shared_lines}; "
                f"moved into the instruction: {len(parent.instruction)}.",
                "  - Instruction:",
                *[f"    > {line}" for line in parent.instruction],
            ]
        total_before[0] += plan.before_items
        total_before[1] += plan.before_points
        total_after[0] += children + plan.standalone
        total_after[1] += points
    out += [
        "",
        "## Totals",
        "",
        f"- Before: {total_before[0]} items, {_points_text(total_before[1])} points.",
        f"- After: {total_after[0]} questions, {_points_text(total_after[1])} points.",
        "",
    ]
    return "\n".join(out)


def baseline_gold(path: Path, ref: str) -> JsonDict:
    relative = path.relative_to(REPO_ROOT).as_posix()
    shown = subprocess.run(
        ["git", "show", f"{ref}:{relative}"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(shown.stdout)  # type: ignore[no-any-return]


def check_exam(moved_path: Path, ref: str) -> list[str]:
    """Return problems found; an empty list means the moved file equals its original."""
    moved = json.loads(moved_path.read_text(encoding="utf-8"))
    original = baseline_gold(moved_path, ref)
    problems: list[str] = []
    if original["schema_version"] != V1:
        return [f"baseline at {ref} is {original['schema_version']}, not {V1}"]
    exam = GoldExam.model_validate(moved)
    if moved_path.read_text(encoding="utf-8") != _dump(moved):
        problems.append("file is not formatted like the original files")
    if {k: v for k, v in moved.items() if k not in ("items", "schema_version")} != {
        k: v for k, v in original.items() if k not in ("items", "schema_version")
    }:
        problems.append("a top-level field other than items changed")
    if list(moved) != list(original):
        problems.append("top-level key order changed")
    rebuilt: list[JsonDict] = []
    for item in moved["items"]:
        if item.get("kind") == "parent":
            for child in item["children"]:
                restored = dict(child)
                restored["prompt"] = item["instruction"] + "\n" + child["prompt"]
                rebuilt.append(restored)
        else:
            rebuilt.append(item)
    if len(rebuilt) != len(original["items"]):
        problems.append(f"{len(rebuilt)} questions after, {len(original['items'])} before")
    for index, (after, before) in enumerate(zip(rebuilt, original["items"], strict=False)):
        if after != before or list(after) != list(before):
            problems.append(f"question {index + 1} ({before['source_label']}) differs")
    if _sum_points(rebuilt) != _sum_points(original["items"]):
        problems.append("points total changed")
    if len(exam.questions) != len(original["items"]):
        problems.append("GoldExam.questions count differs from the original")
    return problems


def run_check(gold_dir: Path, ref: str) -> tuple[list[str], bool]:
    lines = []
    clean = True
    for path in sorted(gold_dir.glob("*.json")):
        problems = check_exam(path, ref)
        moved = json.loads(path.read_text(encoding="utf-8"))
        original = baseline_gold(path, ref)
        parents = [i for i in moved["items"] if i.get("kind") == "parent"]
        children = sum(len(p["children"]) for p in parents)
        standalone = len(moved["items"]) - len(parents)
        status = "ok" if not problems else "FAIL: " + "; ".join(problems)
        lines.append(
            f"- `{path.name}`: {len(parents)} parents, {children} children, {standalone} "
            f"standalone = {children + standalone} questions (was {len(original['items'])}), "
            f"{_points_text(_sum_points(original['items']))} points before; {status}"
        )
        clean = clean and not problems
    return lines, clean


def write_check_section(summary: Path, lines: Sequence[str], ref: str) -> None:
    text = summary.read_text(encoding="utf-8") if summary.exists() else ""
    text = text.split("\n" + CHECK_HEADING)[0].rstrip("\n") + "\n"
    body = [
        "",
        CHECK_HEADING,
        "",
        f"Command: `--check --baseline-ref {ref}`; each moved file validated with `GoldExam`, "
        "every original prompt rebuilt as instruction + newline + child prompt, all other "
        "fields and key order compared with the original.",
        "",
        *lines,
        "",
    ]
    summary.write_text(text + "\n".join(body), encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    parser.add_argument("--gold-dir", type=Path, default=CORPUS_DIR / "gold")
    parser.add_argument("--corpus-dir", type=Path, default=CORPUS_DIR)
    parser.add_argument("--summary", type=Path, help="Markdown summary to write")
    parser.add_argument("--baseline-ref", default="HEAD", help="Git ref holding the v1 files")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="rewrite the gold files")
    mode.add_argument("--check", action="store_true", help="validate moved files")
    args = parser.parse_args(argv)

    if args.check:
        lines, clean = run_check(args.gold_dir, args.baseline_ref)
        print("\n".join(lines))
        if args.summary:
            write_check_section(args.summary, lines, args.baseline_ref)
        return 0 if clean else 1

    built = build_plans(args.gold_dir, args.corpus_dir)
    summary = render_summary([plan for _, _, plan in built])
    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(summary, encoding="utf-8")
    else:
        print(summary)
    if args.write:
        for path, gold, plan in built:
            path.write_text(_dump(moved_document(gold, plan)), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
