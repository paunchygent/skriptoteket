"""Evaluate saved labeling runs against gold and write report.json and report.md."""

from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import TypedDict

from pydantic import JsonValue

from scripts.exam_conversion_eval.gold import GoldExam
from scripts.labeling_feasibility import evaluate, postconv
from scripts.labeling_feasibility.api import answer_map
from scripts.labeling_feasibility.converted import ConvertedExam, ConvertedItem, converted_exam
from scripts.labeling_feasibility.evaluate import (
    BaselineScore,
    FacitPlacementScore,
    GroupingScore,
    KindScores,
    PointsScore,
    SlotsScore,
)
from scripts.labeling_feasibility.method_models import Grouping, grouping_b_output
from scripts.labeling_feasibility.postconv import RoutesScore
from scripts.labeling_feasibility.projection import Reference, project
from scripts.labeling_feasibility.requests import (
    RunSummary,
    facit_answers,
    run_summary,
    saved_method,
    slots_output,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (
    PythonDocxExamChunker,
)

CORPUS = Path("tests/fixtures/exam_conversion/docx_corpus")
METHODS = (
    "grouping_a",
    "grouping_b",
    "grouping_b2",
    "kind_a",
    "kind_b",
    "kind_b2",
    "kind_a_images",
    "ambiguity_a",
    "slots_a",
    "facit_a",
    "points_a",
)


class ExamRunResult(TypedDict, total=False):
    """One exam's scores for one run, keyed as in report.json."""

    cost: dict[str, RunSummary]
    grouping_a: GroupingScore
    grouping_b: GroupingScore
    grouping_b2: GroupingScore
    kind_a: KindScores
    kind_b: KindScores
    kind_b2: KindScores
    kind_a_images: KindScores
    ambiguity_a: dict[str, dict[str, int]]
    slots_a: SlotsScore
    facit_a: FacitPlacementScore
    points_a: PointsScore


class PostconvEntry(TypedDict, total=False):
    """One recorded conversion's post-conversion check scores."""

    items: int
    checks: dict[str, dict[str, int]]
    checks_cost: RunSummary
    routes: RoutesScore
    routes_cost: RunSummary


class ExamData(TypedDict):
    chunks: int
    gold_items: int
    converter_today: BaselineScore
    runs: dict[str, ExamRunResult]
    postconv: dict[str, dict[str, PostconvEntry]]


class CostRunTotals(TypedDict):
    input_tokens: float
    output_tokens: float
    cost_usd: float
    calls: float
    failed: int
    median_exam_wall_seconds: float
    max_exam_wall_seconds: float


class ReportSummary(TypedDict):
    quality_per_run: dict[str, dict[str, dict[str, int]]]
    cost_per_run: dict[str, list[CostRunTotals]]


class ReportJson(TypedDict):
    exams: dict[str, ExamData]
    summary: ReportSummary


def load_reference(docx: Path) -> tuple[GoldExam, tuple[DocxChunk, ...], Reference]:
    gold = GoldExam.model_validate_json((CORPUS / "gold" / f"{docx.stem}.json").read_text())
    chunks = PythonDocxExamChunker().chunk(content=docx.read_bytes()).chunks
    return gold, chunks, project(docx.stem, gold, chunks)


def _read(path: Path) -> JsonValue | None:
    return json.loads(path.read_text()) if path.exists() else None


def _set_grouping(result: ExamRunResult, key: str, score: GroupingScore) -> None:
    if key == "a":
        result["grouping_a"] = score
    elif key == "b":
        result["grouping_b"] = score
    else:
        result["grouping_b2"] = score


def _grouping_block(result: ExamRunResult, key: str) -> GroupingScore | None:
    if key == "a":
        return result.get("grouping_a")
    if key == "b":
        return result.get("grouping_b")
    return result.get("grouping_b2")


def _kind_block(result: ExamRunResult, name: str) -> KindScores | None:
    if name == "kind_a":
        return result.get("kind_a")
    if name == "kind_b":
        return result.get("kind_b")
    if name == "kind_b2":
        return result.get("kind_b2")
    return result.get("kind_a_images")


def evaluate_exam_run(
    exam_dir: Path, gold: GoldExam, chunks: tuple[DocxChunk, ...], reference: Reference
) -> ExamRunResult:
    saved = {
        name: saved_method(value) if (value := _read(exam_dir / f"{name}.json")) else None
        for name in METHODS
    }
    result: ExamRunResult = {"cost": {n: run_summary(s["summary"]) for n, s in saved.items() if s}}
    groupings: dict[str, Grouping] = {}
    saved_a = saved["grouping_a"]
    if saved_a and saved_a["output"]:
        groupings["a"] = Grouping.from_json(saved_a["output"])
    for key in ("b", "b2"):
        saved_b = saved[f"grouping_{key}"]
        if saved_b:
            groupings[key] = Grouping.from_json(grouping_b_output(saved_b["output"])["grouping"])
    matches = {
        key: evaluate.GroupingMatch(reference, grouping) for key, grouping in groupings.items()
    }
    for key, match in matches.items():
        boundary = match.boundary()
        _set_grouping(
            result,
            key,
            {"boundary": boundary, "scope": match.scope(), "facit": match.facit()},
        )
        kind_saved = saved[f"kind_{key}"]
        if kind_saved:
            _set_kind(
                result,
                f"kind_{key}",
                evaluate.kind_scores(
                    match,
                    answer_map(kind_saved["output"]),
                    set(boundary["exact_item_indexes"]),
                ),
            )
    if "a" in matches:
        match = matches["a"]
        grouping_a_result = result["grouping_a"]
        exact = set(grouping_a_result["boundary"]["exact_item_indexes"])
        kind_images = saved["kind_a_images"]
        if kind_images:
            result["kind_a_images"] = evaluate.kind_scores(
                match, answer_map(kind_images["output"]), exact
            )
        ambiguity_saved = saved["ambiguity_a"]
        kind_a = result.get("kind_a")
        if ambiguity_saved and kind_a is not None:
            result["ambiguity_a"] = evaluate.ambiguity_scores(
                match, answer_map(ambiguity_saved["output"]), kind_a["rows"]
            )
        slots_saved = saved["slots_a"]
        if slots_saved:
            result["slots_a"] = evaluate.slot_scores(
                reference, gold, chunks, slots_output(slots_saved["output"])
            )
        facit_saved = saved["facit_a"]
        if facit_saved:
            result["facit_a"] = evaluate.facit_placement_scores(
                match, facit_answers(facit_saved["output"]), chunks
            )
        points_saved = saved["points_a"]
        if points_saved:
            result["points_a"] = evaluate.points_scores(match, answer_map(points_saved["output"]))
    return result


def _set_kind(result: ExamRunResult, name: str, score: KindScores) -> None:
    if name == "kind_a":
        result["kind_a"] = score
    elif name == "kind_b":
        result["kind_b"] = score
    elif name == "kind_b2":
        result["kind_b2"] = score
    else:
        result["kind_a_images"] = score


def evaluate_postconv(
    run_dir: Path, docx: Path, gold: GoldExam, reference: Reference
) -> dict[str, PostconvEntry]:
    results: dict[str, PostconvEntry] = {}
    for name in postconv.RECORDED_CONVERSIONS[docx.stem]:
        recording = converted_exam(json.loads((postconv.RECORDINGS / name).read_text()))
        base = run_dir / docx.stem / "postconv" / name.removesuffix(".json")
        checks_value = _read(base.with_name(base.name + "-checks.json"))
        if not checks_value:
            continue
        checks = saved_method(checks_value)
        mapping = postconv.map_items(reference, recording)
        entry: PostconvEntry = {
            "items": len(recording["items"]),
            "checks": postconv.score_checks(gold, recording, mapping, answer_map(checks["output"])),
            "checks_cost": run_summary(checks["summary"]),
        }
        routes_value = _read(base.with_name(base.name + "-routes.json"))
        if routes_value:
            routes = saved_method(routes_value)
            entry["routes"] = postconv.score_routes(
                gold, recording, mapping, answer_map(routes["output"])
            )
            entry["routes_cost"] = run_summary(routes["summary"])
        results[name] = entry
    return results


def load_converted_exam(exam: str) -> ConvertedExam:
    """Join an exam's v14 batch items, including per-question retry replies."""
    items: list[ConvertedItem] = []
    for name in postconv.RECORDED_CONVERSIONS[exam]:
        batch = converted_exam(json.loads((postconv.RECORDINGS / name).read_text()))
        items += batch["items"]
    return {"items": items}


def build_report(evidence_dir: Path) -> ReportJson:
    exams: dict[str, ExamData] = {}
    projection_dir = evidence_dir / "gold_projection"
    projection_dir.mkdir(parents=True, exist_ok=True)
    run_dirs = sorted((evidence_dir / "runs").glob("run*"))
    for docx in sorted(CORPUS.glob("*.docx")):
        gold, chunks, reference = load_reference(docx)
        (projection_dir / f"{docx.stem}.json").write_text(
            json.dumps(reference.to_json(), ensure_ascii=False, indent=2) + "\n"
        )
        exams[docx.stem] = {
            "chunks": len(chunks),
            "gold_items": len(gold.questions),
            "converter_today": evaluate.converter_baseline(
                reference, gold, load_converted_exam(docx.stem)
            ),
            "runs": {
                run.name: evaluate_exam_run(run / docx.stem, gold, chunks, reference)
                for run in run_dirs
                if (run / docx.stem).exists()
            },
            "postconv": {
                run.name: evaluate_postconv(run, docx, gold, reference)
                for run in run_dirs
                if (run / docx.stem / "postconv").exists()
            },
        }
    return {"exams": exams, "summary": summarize(exams)}


def summarize(exams: dict[str, ExamData]) -> ReportSummary:
    """Corpus-level totals per method per run, then median and range across runs."""
    per_run: defaultdict[str, defaultdict[str, Counter[str]]] = defaultdict(
        lambda: defaultdict(Counter)
    )
    costs: defaultdict[str, defaultdict[str, list[RunSummary]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for exam in exams.values():
        for run, result in exam["runs"].items():
            for key in ("a", "b", "b2"):
                block = _grouping_block(result, key)
                if not block:
                    continue
                b, s, f = block["boundary"], block["scope"], block["facit"]
                totals = per_run[f"grouping_{key}"][run]
                totals.update(
                    {
                        "gold_items": b["gold_items"],
                        "exact_items": b["exact_items"],
                        "split_items": b["split_items"],
                        "merged_questions": b["merged_questions"],
                        "misassigned_anchors": len(b["misassigned_anchors"]),
                        "lost_anchors": len(b["lost_anchors"]),
                        "duplicated_anchors": len(b["duplicated_anchors"]),
                        "invalid_anchors": len(b["invalid_anchors"]),
                        "ref_edges": s["ref_edges"],
                        "wrong_edges": s["wrong_edges"],
                        "missed_edges": s["missed_edges"],
                        "facit_keys": f["ref_keys"],
                        "facit_correct": f["correct"],
                    }
                )
            for name in ("kind_a", "kind_b", "kind_b2", "kind_a_images"):
                block = _kind_block(result, name)
                if block:
                    rows = block["rows"]
                    per_run[name][run].update(
                        {
                            "items": len(rows),
                            "correct": sum(r["gold"] == r["pred"] for r in rows),
                            "exact_group_items": sum(r["exact_group"] for r in rows),
                            "exact_group_correct": sum(
                                r["exact_group"] and r["gold"] == r["pred"] for r in rows
                            ),
                        }
                    )
            slots = result.get("slots_a")
            if slots:
                c = slots["confusion"]
                per_run["slots_a"][run].update({k: c.get(k, 0) for k in ("TT", "TF", "FT", "FF")})
                per_run["slots_a"][run]["excluded"] += slots["excluded_lines"]
            points = result.get("points_a")
            if points:
                per_run["points_a"][run].update({"n": points["n"], "correct": points["correct"]})
            facit = result.get("facit_a")
            if facit:
                per_run["facit_a"][run].update(
                    {
                        "ref_keys": facit["ref_keys"],
                        "asked": facit["asked"],
                        "decisions_correct": facit["decisions_correct"],
                        "positional_code_correct": facit["positional_code_correct"],
                        "grouping_own_correct": facit["grouping_own_correct"],
                    }
                )
            ambiguity = result.get("ambiguity_a")
            if ambiguity:
                for band, values in ambiguity.items():
                    for k, v in values.items():
                        per_run["ambiguity_a"][run][f"{band}:{k}"] += v
            for method, summary in result["cost"].items():
                costs[method][run].append(summary)
    for exam in exams.values():
        for run, files in exam.get("postconv", {}).items():
            for entry in files.values():
                for check, counts in entry["checks"].items():
                    per_run[f"postconv_{check}"][run].update(counts)
                costs["postconv_checks"][run].append(entry["checks_cost"])
                routes = entry.get("routes")
                if routes is not None:
                    per_run["retry_routing"][run].update(
                        {"n": routes["n"], "correct": routes["correct"]}
                    )
                    per_run["retry_routing"][run].update(
                        f"truth_{row['truth']}" for row in routes["rows"]
                    )
                    costs["retry_routing"][run].append(entry["routes_cost"])
    cost_summary: dict[str, list[CostRunTotals]] = {}
    for method, runs in costs.items():
        run_totals: list[CostRunTotals] = []
        for summaries in runs.values():
            run_totals.append(
                {
                    "input_tokens": sum(s["input_tokens"] for s in summaries),
                    "output_tokens": sum(s["output_tokens"] for s in summaries),
                    "cost_usd": sum(s["cost_usd"] or 0 for s in summaries),
                    "calls": sum(s["calls"] for s in summaries),
                    "failed": sum(not s["ok"] for s in summaries),
                    "median_exam_wall_seconds": statistics.median(
                        s["wall_seconds"] for s in summaries
                    ),
                    "max_exam_wall_seconds": max(s["wall_seconds"] for s in summaries),
                }
            )
        cost_summary[method] = run_totals
    return {
        "quality_per_run": {
            m: {r: dict(c) for r, c in runs.items()} for m, runs in per_run.items()
        },
        "cost_per_run": cost_summary,
    }


def write_markdown(report: ReportJson, path: Path) -> None:
    lines = ["# Labeling feasibility report", ""]
    quality = report["summary"]["quality_per_run"]
    cost = report["summary"]["cost_per_run"]
    lines.append("## Corpus totals per run")
    for method, runs in sorted(quality.items()):
        lines.append(f"\n### {method}\n")
        keys = sorted({k for counts in runs.values() for k in counts})
        lines.append("| run | " + " | ".join(keys) + " |")
        lines.append("|---|" + "---|" * len(keys))
        for run, counts in sorted(runs.items()):
            lines.append(f"| {run} | " + " | ".join(str(counts.get(k, 0)) for k in keys) + " |")
    lines.append("\n## Cost and time per run (all eight exams)\n")
    lines.append(
        "| method | run | calls | failed | input tokens | output tokens | USD | median exam wall s | max exam wall s |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for method, runs in sorted(cost.items()):
        for index, totals in enumerate(runs, start=1):
            lines.append(
                f"| {method} | {index} | {totals['calls']} | {totals['failed']} | {totals['input_tokens']} | "
                f"{totals['output_tokens']} | {totals['cost_usd']:.5f} | {totals['median_exam_wall_seconds']:.2f} | "
                f"{totals['max_exam_wall_seconds']:.2f} |"
            )
    lines.append("\n## Per exam (run medians are in report.json)\n")
    for exam, data in report["exams"].items():
        lines.append(f"\n### {exam} ({data['gold_items']} items, {data['chunks']} chunks)\n")
        c = data["converter_today"]
        lines.append(
            f"- Converter today (v14 batch recordings): kind {c['kind_accuracy']}, points {c['points_accuracy']}, keyed {c['keyed_accuracy']}"
        )
        for run, result in sorted(data["runs"].items()):
            parts = []
            for key in ("a", "b", "b2"):
                block = _grouping_block(result, key)
                if block:
                    b, s = block["boundary"], block["scope"]
                    parts.append(
                        f"{key.upper()}: exact {b['exact_items']}/{b['gold_items']}, split {b['split_items']}, merged {b['merged_questions']}, "
                        f"lost {len(b['lost_anchors'])}, dup {len(b['duplicated_anchors'])}, edges P{s['edge_precision']} R{s['edge_recall']}, facit {block['facit']['accuracy']}"
                    )
            for name in ("kind_a", "kind_b", "kind_b2", "kind_a_images"):
                block = _kind_block(result, name)
                if block:
                    parts.append(f"{name} {block['accuracy']}")
            slots = result.get("slots_a")
            if slots:
                parts.append(
                    f"slots acc {slots['accuracy']} P{slots['precision']} R{slots['recall']}"
                )
            points = result.get("points_a")
            if points:
                parts.append(f"points {points['accuracy']}")
            facit = result.get("facit_a")
            if facit:
                parts.append(
                    f"facit decisions {facit['decisions_correct']}/{facit['asked']} positional {facit['positional_code_correct']}"
                )
            lines.append(f"- {run}: " + "; ".join(parts))
    path.write_text("\n".join(lines) + "\n")
