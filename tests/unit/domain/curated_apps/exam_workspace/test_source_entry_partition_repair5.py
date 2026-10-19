"""Seeded source conservation across the one native-entry ownership partition."""

import random
import re

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.source_entry_ownership import (
    EntrySurface,
    plan_entry_ownership,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_formatting import SourceFormatting

pytestmark = pytest.mark.unit


def test_seeded_every_source_word_has_exactly_one_owner():
    rng = random.Random(3909086)
    for case in range(96):
        matching = rng.choice([False, True])
        count = 2 if matching else rng.randint(2, 5)
        sequences = ("match_left", "match_right") if matching else ("choices",)
        models: dict[str, list[str]] = {sequence: [] for sequence in sequences}
        source_parts = []
        labelled = rng.choice([False, True])
        for ordinal in range(1, count + 1):
            for side, sequence in enumerate(sequences):
                repeated = rng.choice([True, False])
                noun = "repeated" if repeated else f"concept_{ordinal}_{side}"
                literal = rng.choice(["", " «why A. is literal»", ' "answer key:"', " q(2 p)"])
                source = f"Explain the shared {noun}{literal}."
                model = source if rng.choice([True, False]) else f"The shared {noun}{literal}."
                models[sequence].append(model)
                prefix = ""
                if labelled:
                    prefix = f"{ordinal}. " if side == 0 and matching else f"{chr(64 + ordinal)}. "
                source_parts.append(prefix + source)
        text = rng.choice([" ", "\n", "; "]).join(source_parts)
        text += rng.choice(["", " (2 p)", "\nSvar:\nprivate_answer\nExplanation."])
        chunks = (DocxChunk("body:0001", "paragraph", text, text),)
        surfaces = tuple(
            EntrySurface(sequence, tuple(models[sequence]), SourceFormatting(chunks, foreign=()))
            for sequence in sequences
        )
        ownership = plan_entry_ownership(chunks, surfaces)
        owners = sorted(ownership.owners, key=lambda owner: owner.start)
        assert len(owners) == count * len(sequences)
        assert all(owner.start >= 0 and owner.end > owner.start for owner in owners), case
        assert all(left.end <= right.start for left, right in zip(owners, owners[1:])), case
        for word in re.finditer(r"\w+", text):
            allocations = sum(
                owner.start <= word.start() and word.end() <= owner.end for owner in owners
            )
            assert allocations == 1, (case, word.group(), text, owners)
