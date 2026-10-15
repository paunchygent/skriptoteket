"""Labeling feasibility runner for TASK-SKRIPT-39-05-04 (no conversion)."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from collections.abc import Coroutine
from pathlib import Path
from typing import Any

import httpx

from scripts.labeling_feasibility import grouping, methods, postconv, report
from scripts.labeling_feasibility.api import OpenAIClient
from scripts.labeling_feasibility.method_models import Grouping
from scripts.labeling_feasibility.render import png_data_url, render_docx_pages
from scripts.labeling_feasibility.requests import MethodResult
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (
    PythonDocxExamChunker,
)

_CORPUS = Path("tests/fixtures/exam_conversion/docx_corpus")


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


async def _probe(client: OpenAIClient, evidence_dir: Path) -> None:
    text = "Markera ett svar.\nA. Ja\nB. Nej"
    decision = await client.decisions(
        label="probe",
        input_value=text,
        questions=[
            {
                "type": "predicate",
                "name": "asks_for_selection",
                "instructions": "The text asks the student to select one listed option.",
            },
            {
                "type": "choice",
                "name": "kind",
                "instructions": "Which response action does the text ask for?",
                "choices": [
                    {"value": "single_choice", "description": "Select exactly one listed option."},
                    {"value": "free_text", "description": "Write a free response."},
                ],
            },
            {
                "type": "score",
                "name": "ambiguity",
                "instructions": "How ambiguous is the requested response action?",
                "levels": [
                    {"label": "clear", "description": "One response action is evident."},
                    {
                        "label": "ambiguous",
                        "description": "Several response actions are plausible.",
                    },
                ],
            },
        ],
    )
    _write(evidence_dir / "probe" / "decisions.json", decision.to_json())
    response = await client.responses(
        label="probe",
        model="gpt-6-luna",
        instructions="Return the anchors of the chunks that list options.",
        user_text=json.dumps([{"anchor": "body:0001", "text": text}]),
        schema_name="probe",
        schema={
            "type": "object",
            "properties": {"anchors": {"type": "array", "items": {"type": "string"}}},
            "required": ["anchors"],
            "additionalProperties": False,
        },
        reasoning_effort="low",
        max_output_tokens=2000,
    )
    _write(evidence_dir / "probe" / "responses.json", response.to_json())
    print("decisions", decision.status_code, decision.usage, decision.headers)
    print("responses", response.status_code, response.usage, response.headers)


async def _probe_limits(client: OpenAIClient, evidence_dir: Path) -> None:
    """Find the largest accepted question count per Decisions request."""
    results = []
    for count in (100, 250, 500, 1000, 2000):
        questions = [
            {
                "type": "predicate",
                "name": f"q{index:04d}",
                "instructions": f"The text contains the number {index}.",
            }
            for index in range(count)
        ]
        record = await client.decisions(
            label=f"limit-{count}", input_value="1 2 3", questions=questions
        )
        results.append(
            {
                "questions": count,
                "status": record.status_code,
                "usage": record.usage,
                "duration_seconds": record.duration_seconds,
                "error": None if record.ok else record.body,
                "answers": len(record.body.get("answers") or []) if record.ok else 0,
            }
        )
        print(
            count,
            record.status_code,
            record.usage.get("input_tokens"),
            round(record.duration_seconds, 2),
        )
        if not record.ok:
            break
    _write(evidence_dir / "probe" / "decisions_question_limit.json", results)


def _save(path: Path, result: MethodResult, output: object) -> None:
    _write(
        path,
        {
            "summary": result.summary(),
            "calls": [call.to_json() for call in result.calls],
            "output": output,
        },
    )


def _grouping_json(output: object) -> object:
    if isinstance(output, Grouping):
        return output.to_json()
    if isinstance(output, dict) and isinstance(output.get("grouping"), Grouping):
        return {**output, "grouping": output["grouping"].to_json()}
    return output


def _method_jobs(
    client: OpenAIClient,
    label: str,
    docx: Path,
    scratch: Path,
    chunks: tuple[DocxChunk, ...],
    grouping_a: Grouping | None,
    grouping_b: Grouping,
) -> dict[str, Coroutine[Any, Any, MethodResult]]:
    jobs: dict[str, Coroutine[Any, Any, MethodResult]] = {
        "kind_b": methods.kind(client, f"{label}/kind_b", grouping_b, chunks)
    }
    if grouping_a is not None:
        images = [png_data_url(page) for page in render_docx_pages(docx, scratch / docx.stem)]
        jobs.update(
            {
                "kind_a": methods.kind(client, f"{label}/kind_a", grouping_a, chunks),
                "kind_a_images": methods.kind_with_images(
                    client, f"{label}/kind_a_images", grouping_a, chunks, images
                ),
                "ambiguity_a": methods.ambiguity(
                    client, f"{label}/ambiguity_a", grouping_a, chunks
                ),
                "slots_a": methods.answer_slots(client, f"{label}/slots_a", grouping_a, chunks),
                "facit_a": methods.facit_attachment(client, f"{label}/facit_a", grouping_a, chunks),
                "points_a": methods.points(client, f"{label}/points_a", grouping_a, chunks),
            }
        )
    return jobs


async def _run_jobs(
    jobs: dict[str, Coroutine[Any, Any, MethodResult]], wanted: set[str], exam_dir: Path, label: str
) -> None:
    selected = {name: job for name, job in jobs.items() if not wanted or name in wanted}
    for name, job in jobs.items():
        if name not in selected:
            job.close()
    results = await asyncio.gather(*selected.values())
    for name, result in zip(selected, results, strict=True):
        _save(exam_dir / f"{name}.json", result, result.output)
    print(
        label,
        "done",
        {name: result.summary()["ok"] for name, result in zip(selected, results, strict=True)},
    )


async def _label_exam(
    client: OpenAIClient, docx: Path, run_dir: Path, scratch: Path, wanted: set[str]
) -> None:
    exam_dir = run_dir / docx.stem
    chunks = PythonDocxExamChunker().chunk(content=docx.read_bytes())
    label = f"{run_dir.name}/{docx.stem}"
    if "grouping_b2" in wanted:
        await _label_exam_b2(client, chunks, exam_dir, label)
        return
    first = await asyncio.gather(
        grouping.grouping_a(client, f"{label}/grouping_a", chunks),
        grouping.grouping_b(client, f"{label}/grouping_b", chunks),
    )
    result_a, result_b = first
    _save(exam_dir / "grouping_a.json", result_a, _grouping_json(result_a.output))
    _save(exam_dir / "grouping_b.json", result_b, _grouping_json(result_b.output))
    grouping_a = result_a.output if isinstance(result_a.output, Grouping) else None
    grouping_b = result_b.output["grouping"]
    jobs = _method_jobs(client, label, docx, scratch, chunks, grouping_a, grouping_b)
    await _run_jobs(jobs, wanted, exam_dir, label)


async def _label_exam_b2(
    client: OpenAIClient, chunks: tuple[DocxChunk, ...], exam_dir: Path, label: str
) -> None:
    """Variant added after the B results: Grouping B with each chunk quoted in its question."""
    result = await grouping.grouping_b(client, f"{label}/grouping_b2", chunks, quote_chunks=True)
    _save(exam_dir / "grouping_b2.json", result, _grouping_json(result.output))
    kind = await methods.kind(client, f"{label}/kind_b2", result.output["grouping"], chunks)
    _save(exam_dir / "kind_b2.json", kind, kind.output)
    print(label, "done", {"grouping_b2": result.summary()["ok"], "kind_b2": kind.summary()["ok"]})


async def _retry_failed_exam(
    client: OpenAIClient, docx: Path, run_dir: Path, scratch: Path
) -> None:
    """Rerun failed downstream methods on the saved groupings; keep the failed attempt."""
    exam_dir = run_dir / docx.stem
    failed = {
        path.stem
        for path in exam_dir.glob("*.json")
        if not path.stem.startswith(("grouping_", "attempt"))
        and not json.loads(path.read_text())["summary"]["ok"]
    }
    if not failed:
        return
    for name in failed:
        (exam_dir / f"{name}.json").rename(exam_dir / f"attempt1-{name}.json")
    saved_a = json.loads((exam_dir / "grouping_a.json").read_text())["output"]
    saved_b = json.loads((exam_dir / "grouping_b.json").read_text())["output"]["grouping"]
    grouping_a = (
        Grouping.from_json(saved_a)
        if isinstance(saved_a, dict) and "questions" in saved_a
        else None
    )
    chunks = PythonDocxExamChunker().chunk(content=docx.read_bytes())
    label = f"{run_dir.name}/{docx.stem}"
    jobs = _method_jobs(
        client, label, docx, scratch, chunks, grouping_a, Grouping.from_json(saved_b)
    )
    await _run_jobs(jobs, failed, exam_dir, f"{label} retry")


async def _postconv_exam(client: OpenAIClient, docx: Path, run_dir: Path) -> None:
    gold, chunks, reference = report.load_reference(docx)
    for name in postconv.RECORDED_CONVERSIONS[docx.stem]:
        recording = json.loads((postconv.RECORDINGS / name).read_text())
        if not recording["items"]:
            continue
        label = f"{run_dir.name}/{docx.stem}/{name}"
        # Evaluator-side selection: which recorded items failed against gold. Only source and the
        # converted item reach the provider.
        failed = postconv.failed_items(gold, recording, postconv.map_items(reference, recording))
        checks, routes = await asyncio.gather(
            postconv.check_conversion(client, f"{label}/checks", recording, chunks),
            postconv.route_retries(client, f"{label}/routes", recording, chunks, failed)
            if failed
            else asyncio.sleep(0, result=None),
        )
        base = run_dir / docx.stem / "postconv" / name.removesuffix(".json")
        _save(base.with_name(base.name + "-checks.json"), checks, checks.output)
        if routes is not None:
            _save(base.with_name(base.name + "-routes.json"), routes, routes.output)
    print(run_dir.name, docx.stem, "postconv done")


async def _run(client: OpenAIClient, args: argparse.Namespace) -> None:
    exams = [
        docx
        for docx in sorted(args.corpus.glob("*.docx"))
        if not args.exams or any(e in docx.stem for e in args.exams)
    ]
    scratch = args.scratch_dir
    for run_number in args.runs:
        run_dir = args.evidence_dir / "runs" / f"run{run_number}"
        if args.command == "postconv":
            await asyncio.gather(*(_postconv_exam(client, docx, run_dir) for docx in exams))
        elif args.command == "retry-failed":
            await asyncio.gather(
                *(_retry_failed_exam(client, docx, run_dir, scratch) for docx in exams)
            )
        else:
            await asyncio.gather(
                *(
                    _label_exam(client, docx, run_dir, scratch, set(args.methods or ()))
                    for docx in exams
                )
            )


async def _main(args: argparse.Namespace) -> None:
    api_key = os.environ["OPENAI_LLM_ANSWER_KEY_API_KEY"]
    async with httpx.AsyncClient() as http:
        client = OpenAIClient(
            client=http, base_url="https://api.openai.com", api_key=api_key, timeout=300.0
        )
        if args.command == "probe":
            await _probe(client, args.evidence_dir)
        elif args.command == "probe-limits":
            await _probe_limits(client, args.evidence_dir)
        elif args.command in {"label", "postconv", "retry-failed"}:
            await _run(client, args)


def _evaluate(args: argparse.Namespace) -> None:
    built = report.build_report(args.evidence_dir)
    _write(args.evidence_dir / "report.json", built)
    report.write_markdown(built, args.evidence_dir / "report.md")
    print((args.evidence_dir / "report.md").read_text()[:6000])


def main() -> None:
    parser = argparse.ArgumentParser(prog="labeling_feasibility")
    parser.add_argument(
        "command",
        choices=("probe", "probe-limits", "label", "postconv", "retry-failed", "evaluate"),
    )
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--scratch-dir", type=Path, default=Path("/tmp/labeling-feasibility"))
    parser.add_argument("--runs", type=int, nargs="+", default=[1])
    parser.add_argument("--corpus", type=Path, default=_CORPUS)
    parser.add_argument("--exams", nargs="*", default=[])
    parser.add_argument("--methods", nargs="*", default=[])
    args = parser.parse_args()
    if args.command == "evaluate":
        _evaluate(args)
    else:
        asyncio.run(_main(args))


if __name__ == "__main__":
    main()
