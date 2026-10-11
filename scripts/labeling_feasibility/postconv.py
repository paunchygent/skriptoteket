"""Post-conversion predicate checks and retry routing over recorded converter output.

Provider input is source chunks plus the recorded converted item; gold is joined only by the
evaluator functions at the bottom of this module.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from scripts.exam_conversion_eval.gold import GoldExam
from scripts.labeling_feasibility.api import OpenAIClient
from scripts.labeling_feasibility.evaluate import _keyed_equal
from scripts.labeling_feasibility.methods import MethodResult, decide
from scripts.labeling_feasibility.projection import Reference, _covers, _f1, tokens
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk

RECORDINGS = Path("tests/fixtures/exam_conversion")
# Every recorded whole-exam conversion fixture, keyed by corpus exam.
RECORDED_CONVERSIONS: dict[str, tuple[str, ...]] = {
    "bf26_diagnostic_grammar_test_ht26_med_facit": (
        "bf26_diagnostic_grammar_docx_build_response.json",
    ),
    "bf26_english_1_unit_test_kap_1_2_med_facit": (
        "bf26_english_1_docx_build_response.json",
        "bf26_english_1_docx_build_response_round1.json",
        "bf26_english_1_docx_build_response_round2.json",
    ),
    "chapter_4_poetry_and_lyrics_quiz_med_facit": ("chapter_4_poetry_docx_build_response.json",),
    "metodprov_vetenskaplig_metod_med_facit": ("metodprov_docx_build_response.json",),
    "sa24_solid_gold_3_unit_3_discuss_and_argue_med_facit": (
        "sa24_solid_gold_3_docx_build_response_round1.json",
    ),
    "svenska_2_grammatik_omprov_variant_1_med_facit": (
        "svenska_2_grammatik_variant_1_docx_build_response.json",
    ),
    "svenska_2_grammatik_omprov_variant_2_med_facit": (
        "svenska_2_grammatik_variant_2_docx_build_response.json",
    ),
    "svenska_2_kursavslutande_prov_med_facit": (
        "svenska_2_kursavslutande_prov_docx_build_response.json",
        "svenska_2_kursavslutande_prov_docx_build_response_v2.json",
        "svenska_2_kursavslutande_prov_docx_build_response_v3.json",
    ),
}


def visible_lines(item: dict[str, Any]) -> list[str]:
    """Student-visible title and body lines; gaps shown as [___] with their cue, options apart."""
    lines = [item.get("title") or ""]
    for row in item.get("body") or []:
        parts = []
        for segment in row.get("segments") or []:
            if segment.get("kind") == "gap":
                hint = segment.get("hint")
                parts.append(f"[___] ({hint})" if hint else "[___]")
            else:
                parts.append(segment.get("text") or "")
        lines += "".join(parts).split("\n")
    return [line for line in lines if line.strip()]


def render_item(index: int, item: dict[str, Any], text: dict[str, str], *, with_kind: bool) -> str:
    lines = [f"### Item i{index}", "Source:"]
    lines += [f"[{anchor}] {text[anchor]}" for anchor in item["source_anchors"] if anchor in text]
    lines.append("Student-visible item:")
    lines += visible_lines(item)
    options = [choice["text"] for choice in item.get("choices") or []]
    if options:
        lines.append("Options: " + " | ".join(options))
    if with_kind:
        lines.append(f"Converted item kind: {item['kind']}")
    return "\n".join(lines)


def exam_instructions(recording: dict[str, Any]) -> list[str]:
    return [
        line for entry in recording.get("instructions") or [] for line in entry["text"].split("\n")
    ]


async def check_conversion(
    client: OpenAIClient, label: str, recording: dict[str, Any], chunks: tuple[DocxChunk, ...]
) -> MethodResult:
    text = {chunk.anchor: chunk.marked_text for chunk in chunks}
    items = recording["items"]
    shown = "\n".join(exam_instructions(recording))
    rendered = f"Exam-level instructions shown to students:\n{shown}\n\n" + "\n\n".join(
        render_item(i, item, text, with_kind=False) for i, item in enumerate(items)
    )
    questions = []
    for index in range(len(items)):
        questions += [
            {
                "type": "predicate",
                "name": f"leak_i{index}",
                "instructions": f"The student-visible text of item i{index} (title and body, not its options) "
                "reveals a correct answer, a keyed value or a sample answer that the student should produce.",
            },
            {
                "type": "predicate",
                "name": f"labels_i{index}",
                "instructions": f"Item i{index} carries labels the exam platform owns: a question number, a points "
                "label, option letters or numbers on its options, printed blank markers such as runs of "
                "underscores, or answer-key labels.",
            },
            {
                "type": "predicate",
                "name": f"missing_i{index}",
                "instructions": f"The source shows an instruction, word bank, passage or other wording that the "
                f"student needs for item i{index}, and it is missing from both the student-visible item and "
                "the exam-level instructions.",
            },
        ]
    calls, answers = await decide(client, label, rendered, questions)
    return MethodResult(calls, answers)


async def route_retries(
    client: OpenAIClient,
    label: str,
    recording: dict[str, Any],
    chunks: tuple[DocxChunk, ...],
    failed: list[int],
) -> MethodResult:
    text = {chunk.anchor: chunk.marked_text for chunk in chunks}
    items = recording["items"]
    rendered = "\n\n".join(render_item(i, items[i], text, with_kind=True) for i in failed)
    questions = [
        {
            "type": "choice",
            "name": f"route_i{index}",
            "instructions": f"Item i{index} failed review. Compare its source with the converted item. "
            "Does the converted item have the wrong item kind for what the source asks the student to do, "
            "or is the kind right and only its content wrong?",
            "choices": [
                {
                    "value": "relabel",
                    "description": "The item kind is wrong; the item must be relabeled.",
                },
                {
                    "value": "reconvert",
                    "description": "The kind is right; only the content must be redone.",
                },
            ],
        }
        for index in failed
    ]
    calls, answers = await decide(client, label, rendered, questions)
    return MethodResult(calls, answers)


# Evaluator side: gold joins here only.


def map_items(reference: Reference, recording: dict[str, Any]) -> dict[int, int]:
    owner = reference.owner_of()
    mapping = {}
    for index, item in enumerate(recording["items"]):
        votes = Counter(owner[a] for a in item["source_anchors"] if a in owner)
        if votes:
            mapping[index] = votes.most_common(1)[0][0]
    return mapping


def check_truth(
    gold: GoldExam, recording: dict[str, Any], item: dict[str, Any], gold_index: int
) -> dict[str, bool]:
    """Principles 6-8 of TASK-SKRIPT-39-05-03 judged against gold, per converted item."""
    source = gold.questions[gold_index]
    visible = visible_lines(item)
    visible_tokens = [token for line in visible for token in tokens(line)]
    visible_text = " " + " ".join(visible_tokens) + " "
    prompt_text = " " + " ".join(tokens(source.prompt)) + " "
    keyed = list(source.correct_choices) + [v for gap in source.gaps for v in gap.accepted_values]
    leak = any(
        f" {' '.join(tokens(v))} " in visible_text and f" {' '.join(tokens(v))} " not in prompt_text
        for v in keyed
        if tokens(v)
    )
    leak = leak or any(
        _f1(tokens(line), tokens(note)) >= 0.6
        for line in visible
        for note in source.notes
        if tokens(line)
    )
    gold_prompt_lines = [
        toks for toks in (tokens(line) for line in source.prompt.split("\n")) if toks
    ]
    keyed_tokens = Counter(t for v in keyed for t in tokens(v))
    extra: Counter[str] = Counter()
    for line in visible:
        toks = tokens(line)
        best = max(gold_prompt_lines, key=lambda g: _f1(toks, g), default=[])
        if toks and best and _f1(toks, best) >= 0.5:
            added = Counter(toks) - Counter(best)
            leak = leak or bool(added & keyed_tokens)
            extra += added - keyed_tokens
    raw = "\n".join(visible).replace("[___]", "")
    gold_choices = {tuple(tokens(choice)) for choice in source.choices}
    lettered = any(
        len(toks := tokens(choice["text"])) > 1
        and len(toks[0]) == 1
        and tuple(toks) not in gold_choices
        for choice in item.get("choices") or []
    )
    labels = (
        sum(extra.values()) >= 2
        or any(token.isdigit() for token in extra)
        or lettered
        or ("___" in raw and "___" not in source.prompt.replace("[___]", ""))
    )
    shown = visible + exam_instructions(recording)
    gold_lines = [tokens(line) for line in source.prompt.split("\n")]
    missing = any(
        len(line) >= 3
        and not any(_covers(tokens(v), line) or _f1(tokens(v), line) >= 0.6 for v in shown)
        for line in gold_lines
    )
    return {"leak": leak, "labels": labels, "missing": missing}


def failed_items(gold: GoldExam, recording: dict[str, Any], mapping: dict[int, int]) -> list[int]:
    failed = []
    for index, gold_index in mapping.items():
        item, source = recording["items"][index], gold.questions[gold_index]
        keyed_wrong = source.kind in {
            "single_choice",
            "multiple_response",
            "gap_fill",
        } and not _keyed_equal(source, item)
        if item["kind"] != source.kind or keyed_wrong:
            failed.append(index)
    return failed


def score_checks(
    gold: GoldExam, recording: dict[str, Any], mapping: dict[int, int], answers: dict[str, Any]
) -> dict[str, Any]:
    counts: dict[str, Counter[str]] = {name: Counter() for name in ("leak", "labels", "missing")}
    for index, gold_index in mapping.items():
        truth = check_truth(gold, recording, recording["items"][index], gold_index)
        for name in counts:
            answer = answers.get(f"{name}_i{index}")
            if not answer or "probability" not in answer:
                counts[name]["unanswered"] += 1
                continue
            predicted = answer["probability"] >= 0.5
            counts[name][f"{'T' if truth[name] else 'F'}{'T' if predicted else 'F'}"] += 1
    return {name: dict(c) for name, c in counts.items()}


def score_routes(
    gold: GoldExam, recording: dict[str, Any], mapping: dict[int, int], answers: dict[str, Any]
) -> dict[str, Any]:
    rows = []
    for name, answer in answers.items():
        index = int(name.removeprefix("route_i"))
        truth = (
            "relabel"
            if recording["items"][index]["kind"] != gold.questions[mapping[index]].kind
            else "reconvert"
        )
        rows.append({"item": index, "truth": truth, "pred": answer.get("choice")})
    return {"n": len(rows), "correct": sum(r["truth"] == r["pred"] for r in rows), "rows": rows}
