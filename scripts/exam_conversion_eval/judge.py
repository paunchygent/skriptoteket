"""Judge a saved staging document against a corpus exam without calling a provider."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError

from scripts.exam_conversion_eval.compare import compare_native_exam
from scripts.exam_conversion_eval.gold import GoldExam
from scripts.exam_conversion_eval.report import print_comparison
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (
    PythonDocxExamChunker,
)

_CORPUS = Path("tests/fixtures/exam_conversion/docx_corpus")


def main(argv: Sequence[str] | None = None) -> int:
    """Print every comparator mismatch and return 1 when the exam fails."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exam", choices=sorted(path.stem for path in _CORPUS.glob("*.docx")))
    parser.add_argument(
        "document", type=Path, help="Saved API envelope or bare native document JSON."
    )
    args = parser.parse_args(argv)
    try:
        gold = GoldExam.model_validate_json(
            (_CORPUS / "gold" / f"{args.exam}.json").read_text(encoding="utf-8")
        )
        payload = json.loads(args.document.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and "document" in payload:
            payload = payload["document"]
        document = NativeExamDocument.model_validate(payload)
        corpus_docx = _CORPUS / f"{args.exam}.docx"
        chunks = PythonDocxExamChunker().chunk(content=corpus_docx.read_bytes()).chunks
    except (OSError, ValueError, ValidationError) as error:
        parser.error(str(error))
    comparison = compare_native_exam(gold, document, [chunk.text for chunk in chunks])
    matched = sum(item.passed for item in comparison.items)
    print(
        f"{args.exam}: {matched}/{len(comparison.items)} items match;"
        f" gold {len(gold.questions)}, converted {len(document.items)}"
    )
    print_comparison(comparison)
    return 0 if comparison.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
