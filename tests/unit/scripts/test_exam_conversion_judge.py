"""Challenge the saved-document judge with deliberate mutations of live corpus replays.

The replays are real, non-gold conversions, so a baseline run reports whatever the model
produced. Each test mutates one property and asserts the judge reports exactly that mismatch;
it never asks the raw replay to match gold.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.exam_conversion_eval.compare import compare_native_exam
from scripts.exam_conversion_eval.judge import main
from tests.unit.scripts.exam_conversion_corpus_support import (
    gold_exam,
    replayed,
    with_item,
)

_STEM = "sa24_solid_gold_3_unit_3_discuss_and_argue_med_facit"
_GAP_STEM = "bf26_diagnostic_grammar_test_ht26_med_facit"
_POINTS_LABEL = "Questions 1–45, Question 1"
ROOT = Path(__file__).resolve().parents[3]


def _principle_count(output: str, principle: str) -> int:
    """The judge's own count of failing items for one principle."""
    match = re.search(rf"failing items per principle:.*\b{principle} (\d+)", output)
    assert match is not None, output
    return int(match.group(1))


def _summary(document, stem: str) -> str:
    """The judge's item summary for `document`, computed by the comparator the judge uses."""
    comparison = compare_native_exam(gold_exam(stem), document)
    return f"{sum(item.passed for item in comparison.items)}/{len(comparison.items)} items match"


@pytest.mark.parametrize("envelope", [False, True])
def test_changed_points_fail_and_identify_the_question(tmp_path: Path, capsys, envelope: bool):
    document, _ = replayed(_STEM)
    path = tmp_path / "document.json"

    def save(value) -> None:
        payload = value.model_dump(mode="json")
        path.write_text(
            json.dumps({"document": payload} if envelope else payload), encoding="utf-8"
        )

    save(document)
    main([_STEM, str(path)])
    baseline = capsys.readouterr().out

    index, item = next(
        (i, item) for i, item in enumerate(document.items) if item.points is not None
    )
    assert item.points is not None
    changed = item.model_copy(update={"points": item.points + 1})
    save(with_item(document, index, changed))
    assert main([_STEM, str(path)]) == 1
    output = capsys.readouterr().out
    assert f"[{index}] {_POINTS_LABEL} points points: expected=" in output
    assert f"actual={changed.points!r}" in output
    assert _principle_count(output, "points") == _principle_count(baseline, "points") + 1


def test_a_wrong_title_fails_without_changing_the_item_verdicts(tmp_path: Path, capsys):
    document, _ = replayed(_STEM)
    path = tmp_path / "wrong-title.json"
    path.write_text(
        document.model_copy(update={"title": "Wrong exam title"}).model_dump_json(),
        encoding="utf-8",
    )
    assert main([_STEM, str(path)]) == 1
    output = capsys.readouterr().out
    assert "title FAIL" in output
    assert "actual='Wrong exam title'" in output
    assert _summary(document, _STEM) in output


def test_every_missing_question_mismatch_is_printed(tmp_path: Path, capsys):
    document, _ = replayed(_STEM)
    path = tmp_path / "missing-items.json"
    changed = document.model_copy(update={"items": document.items[:-2], "parents": ()})
    path.write_text(changed.model_dump_json(), encoding="utf-8")
    assert main([_STEM, str(path)]) == 1
    output = capsys.readouterr().out
    missing = [
        item
        for item in compare_native_exam(gold_exam(_STEM), changed).items
        if any(mismatch.reason == "missing_item" for mismatch in item.mismatches)
    ]
    assert len(missing) == 2
    for item in missing:
        assert f"[{item.index}] {item.source_label} content_present missing_item:" in output
    assert output.count("content_present missing_item:") == len(missing)


def test_a_long_wrong_answer_is_printed_without_truncation(tmp_path: Path, capsys):
    document, _ = replayed(_GAP_STEM)
    index, item = next((i, item) for i, item in enumerate(document.items) if item.gaps)
    wrong_answer = "wrong answer " * 60 + "final marker"
    gap = item.gaps[0].model_copy(update={"accepted_values": (wrong_answer,)})
    changed = item.model_copy(update={"gaps": (gap, *item.gaps[1:])})
    path = tmp_path / "wrong-answer.json"
    path.write_text(with_item(document, index, changed).model_dump_json(), encoding="utf-8")
    assert main([_GAP_STEM, str(path)]) == 1
    output = capsys.readouterr().out
    assert "scoring gap 1 misses:" in output
    assert "scoring gap 1 accepts extra:" in output
    assert f"actual={(wrong_answer,)!r}" in output


def _run_judge(exam: str, document: Path) -> subprocess.CompletedProcess[str]:
    """Run the judge CLI in a child process as an operator would, without PDM or a provider."""
    return subprocess.run(
        [sys.executable, "-m", "scripts.exam_conversion_eval.judge", exam, str(document)],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": os.pathsep.join((str(ROOT / "src"), str(ROOT)))},
        text=True,
        capture_output=True,
        check=False,
    )


def test_the_judge_cli_returns_the_verdict_and_names_the_changed_question(tmp_path: Path):
    document, _ = replayed(_STEM)
    path = tmp_path / "document.json"
    path.write_text(document.model_dump_json(), encoding="utf-8")
    baseline = _run_judge(_STEM, path)
    assert "items match" in baseline.stdout

    index, item = next(
        (i, item) for i, item in enumerate(document.items) if item.points is not None
    )
    assert item.points is not None
    changed = item.model_copy(update={"points": item.points + 1})
    path.write_text(with_item(document, index, changed).model_dump_json(), encoding="utf-8")
    failed = _run_judge(_STEM, path)
    assert failed.returncode == 1
    assert f"[{index}] {_POINTS_LABEL} points points: expected=" in failed.stdout
    assert f"actual={changed.points!r}" in failed.stdout
    assert f"actual={changed.points!r}" not in baseline.stdout


def test_a_crashed_conversion_never_reports_an_observed_title(capsys):
    from scripts.exam_conversion_eval.compare import compare_exam
    from scripts.exam_conversion_eval.report import print_comparison

    gold = gold_exam(_STEM)
    print_comparison(compare_exam(gold, ()), crashed=True)

    out = capsys.readouterr().out
    assert "title ok" not in out
    assert f"title FAIL: gold={gold.title!r} actual=None (conversion crashed)" in out
