"""Evaluate saved labeling runs against gold and write report.json and report.md."""

from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from scripts.exam_conversion_eval.gold import GoldExam
from scripts.labeling_feasibility import evaluate, postconv
from scripts.labeling_feasibility.converted import ConvertedExam, ConvertedItem
from scripts.labeling_feasibility.projection import Reference, project
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


def load_reference(docx: Path) -> tuple[GoldExam, Any, Reference]:
    gold = GoldExam.model_validate_json((CORPUS / "gold" / f"{docx.stem}.json").read_text())
    chunks = PythonDocxExamChunker().chunk(content=docx.read_bytes()).chunks
    return gold, chunks, project(docx.stem, gold, chunks)


def _read(path: Path) -> dict[str, Any] | None:
    return json.loads(path.read_text()) if path.exists() else None


def evaluate_exam_run(
    exam_dir: Path, gold: GoldExam, chunks: Any, reference: Reference
) -> dict[str, Any]:
    saved = {name: _read(exam_dir / f"{name}.json") for name in METHODS}
    result: dict[str, Any] = {"cost": {n: s["summary"] for n, s in saved.items() if s}}
    groupings = {}
    if saved["grouping_a"] and saved["grouping_a"]["output"]:
        groupings["a"] = saved["grouping_a"]["output"]
    for key in ("b", "b2"):
        saved_b = saved[f"grouping_{key}"]
        if saved_b:
            groupings[key] = saved_b["output"]["grouping"]
    matches = {
        key: evaluate.GroupingMatch(reference, grouping) for key, grouping in groupings.items()
    }
    for key, match in matches.items():
        boundary = match.boundary()
        result[f"grouping_{key}"] = {
            "boundary": boundary,
            "scope": match.scope(),
            "facit": match.facit(),
        }
        kind_saved = saved[f"kind_{key}"]
        if kind_saved:
            result[f"kind_{key}"] = evaluate.kind_scores(
                match, kind_saved["output"], set(boundary["exact_item_indexes"])
            )
    if "a" in matches:
        match, exact = matches["a"], set(result["grouping_a"]["boundary"]["exact_item_indexes"])
        if saved["kind_a_images"]:
            result["kind_a_images"] = evaluate.kind_scores(
                match, saved["kind_a_images"]["output"], exact
            )
        if saved["ambiguity_a"] and "kind_a" in result:
            result["ambiguity_a"] = evaluate.ambiguity_scores(
                match, saved["ambiguity_a"]["output"], result["kind_a"]["rows"]
            )
        if saved["slots_a"]:
            result["slots_a"] = evaluate.slot_scores(
                reference, gold, chunks, saved["slots_a"]["output"]
            )
        if saved["facit_a"]:
            result["facit_a"] = evaluate.facit_placement_scores(
                match, saved["facit_a"]["output"], chunks
            )
        if saved["points_a"]:
            result["points_a"] = evaluate.points_scores(match, saved["points_a"]["output"])
    return result


def evaluate_postconv(
    run_dir: Path, docx: Path, gold: GoldExam, reference: Reference
) -> dict[str, Any]:
    results = {}
    for name in postconv.RECORDED_CONVERSIONS[docx.stem]:
        recording = json.loads((postconv.RECORDINGS / name).read_text())
        base = run_dir / docx.stem / "postconv" / name.removesuffix(".json")
        checks = _read(base.with_name(base.name + "-checks.json"))
        if not checks:
            continue
        mapping = postconv.map_items(reference, recording)
        entry: dict[str, Any] = {
            "items": len(recording["items"]),
            "checks": postconv.score_checks(gold, recording, mapping, checks["output"]),
            "checks_cost": checks["summary"],
        }
        routes = _read(base.with_name(base.name + "-routes.json"))
        if routes:
            entry["routes"] = postconv.score_routes(gold, recording, mapping, routes["output"])
            entry["routes_cost"] = routes["summary"]
        results[name] = entry
    return results


def load_converted_exam(exam: str) -> ConvertedExam:
    """Join an exam's v14 batch items, including per-question retry replies."""
    items: list[ConvertedItem] = []
    for name in postconv.RECORDED_CONVERSIONS[exam]:
        batch: ConvertedExam = json.loads((postconv.RECORDINGS / name).read_text())
        items += batch["items"]
    return {"items": items}


def build_report(evidence_dir: Path) -> dict[str, Any]:
    exams: dict[str, Any] = {}
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


def summarize(exams: dict[str, Any]) -> dict[str, Any]:
    """Corpus-level totals per method per run, then median and range across runs."""
    per_run: dict[str, dict[str, Counter[str]]] = defaultdict(lambda: defaultdict(Counter))
    costs: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for exam in exams.values():
        for run, result in exam["runs"].items():
            for key in ("a", "b", "b2"):
                block = result.get(f"grouping_{key}")
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
                block = result.get(name)
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
            if result.get("slots_a"):
                c = result["slots_a"]["confusion"]
                per_run["slots_a"][run].update({k: c.get(k, 0) for k in ("TT", "TF", "FT", "FF")})
                per_run["slots_a"][run]["excluded"] += result["slots_a"]["excluded_lines"]
            if result.get("points_a"):
                per_run["points_a"][run].update(
                    {"n": result["points_a"]["n"], "correct": result["points_a"]["correct"]}
                )
            if result.get("facit_a"):
                f = result["facit_a"]
                per_run["facit_a"][run].update(
                    {
                        k: f[k]
                        for k in (
                            "ref_keys",
                            "asked",
                            "decisions_correct",
                            "positional_code_correct",
                            "grouping_own_correct",
                        )
                    }
                )
            if result.get("ambiguity_a"):
                for band, values in result["ambiguity_a"].items():
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
                if "routes" in entry:
                    per_run["retry_routing"][run].update(
                        {"n": entry["routes"]["n"], "correct": entry["routes"]["correct"]}
                    )
                    per_run["retry_routing"][run].update(
                        f"truth_{row['truth']}" for row in entry["routes"]["rows"]
                    )
                    costs["retry_routing"][run].append(entry["routes_cost"])
    cost_summary = {}
    for method, runs in costs.items():
        run_totals = []
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


def write_markdown(report: dict[str, Any], path: Path) -> None:
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
                block = result.get(f"grouping_{key}")
                if block:
                    b, s = block["boundary"], block["scope"]
                    parts.append(
                        f"{key.upper()}: exact {b['exact_items']}/{b['gold_items']}, split {b['split_items']}, merged {b['merged_questions']}, "
                        f"lost {len(b['lost_anchors'])}, dup {len(b['duplicated_anchors'])}, edges P{s['edge_precision']} R{s['edge_recall']}, facit {block['facit']['accuracy']}"
                    )
            for name in ("kind_a", "kind_b", "kind_b2", "kind_a_images"):
                if name in result:
                    parts.append(f"{name} {result[name]['accuracy']}")
            if "slots_a" in result:
                parts.append(
                    f"slots acc {result['slots_a']['accuracy']} P{result['slots_a']['precision']} R{result['slots_a']['recall']}"
                )
            if "points_a" in result:
                parts.append(f"points {result['points_a']['accuracy']}")
            if "facit_a" in result:
                f = result["facit_a"]
                parts.append(
                    f"facit decisions {f['decisions_correct']}/{f['asked']} positional {f['positional_code_correct']}"
                )
            lines.append(f"- {run}: " + "; ".join(parts))
    path.write_text("\n".join(lines) + "\n")
