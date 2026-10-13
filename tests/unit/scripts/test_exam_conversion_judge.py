"""Challenge the saved-document judge with mutations of recorded corpus conversions."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.exam_conversion_eval.judge import main
from tests.unit.scripts.exam_conversion_corpus_support import replayed, with_item

_STEM = "sa24_solid_gold_3_unit_3_discuss_and_argue_med_facit"
_GAP_STEM = "bf26_diagnostic_grammar_test_ht26_med_facit"
_POINTS_LABEL = "Questions 1–45, Question 1"
ROOT = Path(__file__).resolve().parents[3]


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
    assert main([_STEM, str(path)]) == 0
    baseline = capsys.readouterr().out
    assert "title ok" in baseline
    assert "points 0" in baseline

    index, item = next(
        (i, item) for i, item in enumerate(document.items) if item.points is not None
    )
    assert item.points is not None
    changed = item.model_copy(update={"points": item.points + 1})
    save(with_item(document, index, changed))
    assert main([_STEM, str(path)]) == 1
    output = capsys.readouterr().out
    assert "points 1" in output
    assert f"[{index}] {_POINTS_LABEL} points points: expected=" in output
    assert f"actual={changed.points!r}" in output


def test_a_wrong_title_fails_even_when_all_items_match(tmp_path: Path, capsys):
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
    assert f"{len(document.items)}/{len(document.items)} items match" in output


def test_every_missing_question_mismatch_is_printed(tmp_path: Path, capsys):
    document, _ = replayed(_STEM)
    path = tmp_path / "missing-items.json"
    changed = document.model_copy(update={"items": document.items[:-2], "parents": ()})
    path.write_text(changed.model_dump_json(), encoding="utf-8")
    assert main([_STEM, str(path)]) == 1
    output = capsys.readouterr().out
    assert f"[{len(document.items) - 2}]" in output
    assert f"[{len(document.items) - 1}]" in output
    assert output.count("content_present missing_item:") == 2


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
    assert baseline.returncode == 0
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


def test_a_crashed_conversion_never_reports_an_observed_title(capsys):
    from scripts.exam_conversion_eval.compare import compare_exam
    from scripts.exam_conversion_eval.gold import GoldExam
    from scripts.exam_conversion_eval.judge import _CORPUS
    from scripts.exam_conversion_eval.report import print_comparison

    gold = GoldExam.model_validate_json(
        (_CORPUS / "gold" / f"{_STEM}.json").read_text(encoding="utf-8")
    )
    print_comparison(compare_exam(gold, ()), crashed=True)

    out = capsys.readouterr().out
    assert "title ok" not in out
    assert f"title FAIL: gold={gold.title!r} actual=None (conversion crashed)" in out
