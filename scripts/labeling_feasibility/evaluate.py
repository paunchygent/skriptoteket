"""Score provider output against the gold-derived chunk reference. Runs only after provider calls."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from scripts.exam_conversion_eval.gold import GoldExam
from scripts.labeling_feasibility.projection import Reference, _covers, _f1, tokens
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk

PROBABILITY_BANDS = ((0.99, 1.01), (0.95, 0.99), (0.8, 0.95), (0.0, 0.8))
SCORE_BANDS = ((0.0, 0.25), (0.25, 0.75), (0.75, 2.01))


def _band(value: float, bands: tuple[tuple[float, float], ...]) -> str:
    for low, high in bands:
        if low <= value < high:
            return f"{low:g}-{high:g}"
    return "n/a"


class GroupingMatch:
    """Map predicted questions onto reference items by owned-anchor overlap."""

    def __init__(self, reference: Reference, grouping: dict[str, Any]):
        self.reference = reference
        self.grouping = grouping
        self.questions = grouping["questions"]
        self.owned = {q["id"]: set(q["anchors"]) | set(q["key_anchors"]) for q in self.questions}
        self.context_governs = defaultdict(set)
        for context in grouping["contexts"]:
            self.context_governs[context["anchor"]].update(context["governs"])
        self.ref_owner = reference.owner_of()
        self.question_to_item: dict[str, int | None] = {}
        for qid, anchors in self.owned.items():
            votes = Counter(self.ref_owner[a] for a in anchors if a in self.ref_owner)
            self.question_to_item[qid] = votes.most_common(1)[0][0] if votes else None
        self.item_to_question: dict[int, str | None] = {}
        for item in reference.items:
            question_votes = Counter(
                qid for qid, anchors in self.owned.items() for a in anchors if a in item.owned
            )
            self.item_to_question[item.index] = (
                question_votes.most_common(1)[0][0] if question_votes else None
            )

    def _lenient(self, anchor: str, item_index: int, qid: str | None) -> bool:
        """A one-question instruction may sit in the question or govern it as context."""
        ref_single = self.reference.shared.get(anchor) == [item_index]
        pred_single = qid is not None and self.context_governs.get(anchor) == {qid}
        ref_content = anchor in self.reference.items[item_index].owned
        pred_content = qid is not None and anchor in self.owned.get(qid, set())
        return (ref_content and pred_single) or (ref_single and pred_content)

    def boundary(self) -> dict[str, Any]:
        ref = self.reference
        scored = set(self.ref_owner) | set(ref.shared)
        exact, exact_items = 0, []
        split = merged = 0
        for item in ref.items:
            qid = self.item_to_question[item.index]
            expected = item.owned | {a for a, run in ref.shared.items() if run == [item.index]}
            got = (self.owned.get(qid, set()) & scored) if qid else set()
            got |= {
                a
                for a, governs in self.context_governs.items()
                if qid and governs == {qid} and a in scored
            }
            if qid and all(self._lenient(a, item.index, qid) for a in expected ^ got):
                exact += 1
                exact_items.append(item.index)
            holders = {q for q, anchors in self.owned.items() if anchors & item.owned}
            if len(holders) > 1:
                split += 1
        for qid, anchors in self.owned.items():
            if len({self.ref_owner[a] for a in anchors if a in self.ref_owner}) > 1:
                merged += 1
        placed: Counter[str] = Counter()
        for anchors in self.owned.values():
            placed.update(anchors)
        placed.update(self.context_governs.keys())
        lost = sorted(a for a in scored if placed[a] == 0)
        duplicated = sorted(a for a, count in placed.items() if count > 1)
        misassigned = sorted(
            a
            for qid, anchors in self.owned.items()
            for a in anchors
            if a in self.ref_owner and self.question_to_item[qid] != self.ref_owner[a]
        )
        return {
            "gold_items": len(ref.items),
            "pred_questions": len(self.questions),
            "exact_items": exact,
            "exact_item_indexes": exact_items,
            "split_items": split,
            "merged_questions": merged,
            "misassigned_anchors": misassigned,
            "lost_anchors": lost,
            "duplicated_anchors": duplicated,
            "invalid_anchors": self.grouping.get("invalid_anchors", []),
            "title_correct": sorted(self.grouping["title"]) == sorted(ref.title),
        }

    def scope(self) -> dict[str, Any]:
        ref = self.reference
        ref_edges = {(a, i) for a, run in ref.shared.items() if len(run) > 1 for i in run}
        pred_edges = set()
        for anchor, governs in self.context_governs.items():
            items = {self.question_to_item.get(q) for q in governs} - {None}
            if len(governs) > 1 or anchor in ref.shared:
                pred_edges |= {(anchor, i) for i in items}
        true_positive = len(ref_edges & pred_edges)
        ref_multi = {a for a, run in ref.shared.items() if len(run) > 1}
        pred_multi = {a for a, governs in self.context_governs.items() if len(governs) > 1}
        return {
            "ref_edges": len(ref_edges),
            "pred_edges": len(pred_edges),
            "edge_precision": _ratio(true_positive, len(pred_edges)),
            "edge_recall": _ratio(true_positive, len(ref_edges)),
            "wrong_edges": len(pred_edges - ref_edges),
            "missed_edges": len(ref_edges - pred_edges),
            "shared_found": len(ref_multi & pred_multi),
            "shared_ref": len(ref_multi),
            "shared_pred": len(pred_multi),
            "shared_owned_by_question_in_ref": sorted(pred_multi & set(self.ref_owner)),
        }

    def facit(self) -> dict[str, Any]:
        keys = {a: item.index for item in self.reference.items for a in item.key}
        assigned = {
            a: qid for qid, q in ((q["id"], q) for q in self.questions) for a in q["key_anchors"]
        }
        correct = sum(
            1
            for a, owner in keys.items()
            if self.question_to_item.get(assigned.get(a, "")) == owner
        )
        return {"ref_keys": len(keys), "correct": correct, "accuracy": _ratio(correct, len(keys))}


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def kind_scores(
    match: GroupingMatch, answers: dict[str, dict[str, Any]], exact_items: set[int]
) -> dict[str, Any]:
    confusion: Counter[tuple[str, str]] = Counter()
    bands: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    rows = []
    for item in match.reference.items:
        qid = match.item_to_question[item.index]
        answer = answers.get(f"kind_{qid}") if qid else None
        predicted = answer.get("choice", "refusal") if answer else "missing"
        probability = 0.0
        if answer:
            probability = max(
                (p["probability"] for p in answer.get("probabilities", [])), default=0.0
            )
        confusion[(item.kind, predicted)] += 1
        correct = predicted == item.kind
        band = _band(probability, PROBABILITY_BANDS)
        bands[band][0] += 1
        bands[band][1] += int(correct)
        rows.append(
            {
                "item": item.index,
                "gold": item.kind,
                "pred": predicted,
                "p": probability,
                "exact_group": item.index in exact_items,
            }
        )
    exact_rows = [row for row in rows if row["exact_group"]]
    return {
        "accuracy": _ratio(sum(r["gold"] == r["pred"] for r in rows), len(rows)),
        "accuracy_exact_groups": _ratio(
            sum(r["gold"] == r["pred"] for r in exact_rows), len(exact_rows)
        ),
        "confusion": {
            f"{gold}->{pred}": count for (gold, pred), count in sorted(confusion.items())
        },
        "calibration": {band: {"n": n, "correct": c} for band, (n, c) in sorted(bands.items())},
        "rows": rows,
    }


def ambiguity_scores(
    match: GroupingMatch, answers: dict[str, dict[str, Any]], kind_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    by_item = {row["item"]: row for row in kind_rows}
    bands: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    for item in match.reference.items:
        qid = match.item_to_question[item.index]
        answer = answers.get(f"ambiguity_{qid}") if qid else None
        if not answer or "score" not in answer:
            continue
        band = _band(float(answer["score"]), SCORE_BANDS)
        row = by_item[item.index]
        bands[band][0] += 1
        bands[band][1] += int(row["gold"] != row["pred"])
        bands[band][2] += int(not row["exact_group"])
    return {
        band: {"n": n, "kind_wrong": k, "group_wrong": g}
        for band, (n, k, g) in sorted(bands.items())
    }


def slot_scores(
    reference: Reference, gold: GoldExam, chunks: tuple[DocxChunk, ...], output: dict[str, Any]
) -> dict[str, Any]:
    text = {chunk.anchor: chunk.marked_text for chunk in chunks}
    owner = reference.owner_of()
    gold_lines: dict[int, list[tuple[list[str], bool]]] = {}
    for item in reference.items:
        source = gold.questions[item.index]
        lines = [(tokens(line), "[___]" in line) for line in source.prompt.split("\n")]
        lines += [(tokens(choice), False) for choice in source.choices]
        gold_lines[item.index] = [(toks, gap) for toks, gap in lines if toks]
    confusion: Counter[str] = Counter()
    bands: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    excluded = 0
    for line_id in output["lines"]:
        anchor, number = line_id.rsplit("#", 1)
        name = f"slot_{line_id.replace('body:', '').replace('#', '_')}"
        answer = output["answers"].get(name)
        if anchor not in owner or not answer or "probability" not in answer:
            excluded += 1
            continue
        line = tokens(text[anchor].split("\n")[int(number) - 1])
        truth = _slot_truth(line, gold_lines[owner[anchor]])
        if truth is None:
            excluded += 1
            continue
        predicted = answer["probability"] >= 0.5
        confusion[f"{'T' if truth else 'F'}{'T' if predicted else 'F'}"] += 1
        confidence = max(answer["probability"], 1 - answer["probability"])
        band = _band(confidence, PROBABILITY_BANDS)
        bands[band][0] += 1
        bands[band][1] += int(truth == predicted)
    tp, fp, fn, tn = confusion["TT"], confusion["FT"], confusion["TF"], confusion["FF"]
    return {
        "scored_lines": tp + fp + fn + tn,
        "excluded_lines": excluded,
        "accuracy": _ratio(tp + tn, tp + fp + fn + tn),
        "precision": _ratio(tp, tp + fp),
        "recall": _ratio(tp, tp + fn),
        "confusion": dict(confusion),
        "calibration": {band: {"n": n, "correct": c} for band, (n, c) in sorted(bands.items())},
    }


def _slot_truth(line: list[str], gold_lines: list[tuple[list[str], bool]]) -> bool | None:
    best, best_gap = 0.0, None
    for toks, gap in gold_lines:
        score = 1.0 if _covers(line, toks) else _f1(line, toks)
        if score > best:
            best, best_gap = score, gap
    return best_gap if best >= 0.6 else None


def points_scores(match: GroupingMatch, answers: dict[str, dict[str, Any]]) -> dict[str, Any]:
    correct = total = 0
    wrong = []
    for item in match.reference.items:
        if item.points is None:
            continue
        qid = match.item_to_question[item.index]
        answer = answers.get(f"points_{qid}") if qid else None
        total += 1
        value = answer.get("choice") if answer else None
        if value is not None and value != "unknown" and float(value) == float(item.points):
            correct += 1
        else:
            wrong.append({"item": item.index, "gold": item.points, "pred": value})
    return {"n": total, "correct": correct, "accuracy": _ratio(correct, total), "wrong": wrong}


def facit_placement_scores(
    match: GroupingMatch, output: dict[str, Any], chunks: tuple[DocxChunk, ...]
) -> dict[str, Any]:
    keys = {a: item.index for item in match.reference.items for a in item.key}
    order = {chunk.anchor: index for index, chunk in enumerate(chunks)}
    starts = {
        q["id"]: min((order[a] for a in q["anchors"]), default=10**9) for q in match.questions
    }
    decided = positional = own = asked = 0
    assigned = {a: q["id"] for q in match.questions for a in q["key_anchors"]}
    for anchor, owner in keys.items():
        answer = output["answers"].get(f"facit_{anchor.replace('body:', '')}")
        if answer is None:
            continue
        asked += 1
        decided += int(match.question_to_item.get(answer.get("choice", "")) == owner)
        before = [qid for qid, start in starts.items() if start < order[anchor]]
        nearest = max(before, key=starts.__getitem__) if before else None
        positional += int(nearest is not None and match.question_to_item.get(nearest) == owner)
        own += int(match.question_to_item.get(assigned.get(anchor, "")) == owner)
    return {
        "ref_keys": len(keys),
        "asked": asked,
        "decisions_correct": decided,
        "positional_code_correct": positional,
        "grouping_own_correct": own,
    }


def converter_baseline(
    reference: Reference, gold: GoldExam, recording: dict[str, Any]
) -> dict[str, Any]:
    """Score today's whole-exam converter output (kind, points, keyed content) on the same items."""
    owner = reference.owner_of()
    by_item: dict[int, dict[str, Any]] = {}
    for converted in recording["items"]:
        votes = Counter(owner[a] for a in converted["source_anchors"] if a in owner)
        if votes:
            by_item.setdefault(votes.most_common(1)[0][0], converted)
    kind = points = keyed = keyed_n = 0
    confusion: Counter[str] = Counter()
    for item in reference.items:
        converted = by_item.get(item.index)
        source = gold.questions[item.index]
        predicted = converted["kind"] if converted else "missing"
        confusion[f"{item.kind}->{predicted}"] += 1
        kind += int(predicted == item.kind)
        if converted and item.points is not None and converted.get("points") is not None:
            points += int(float(converted["points"]) == float(item.points))
        if source.kind in {"single_choice", "multiple_response", "gap_fill"}:
            keyed_n += 1
            keyed += int(bool(converted) and _keyed_equal(source, converted))
    n = len(reference.items)
    return {
        "items": n,
        "kind_accuracy": _ratio(kind, n),
        "kind_confusion": dict(confusion),
        "points_accuracy": _ratio(points, sum(1 for i in reference.items if i.points is not None)),
        "keyed_accuracy": _ratio(keyed, keyed_n),
    }


def _norm(value: str) -> str:
    return " ".join(tokens(value))


def _keyed_equal(source: Any, converted: dict[str, Any]) -> bool:
    if source.kind in {"single_choice", "multiple_response"}:
        got = {
            _norm(choice["text"])
            for choice in converted.get("choices", [])
            if choice.get("correct")
        }
        return got == {_norm(value) for value in source.correct_choices}
    gaps = [
        {_norm(value) for value in segment.get("accepted_values", [])}
        for row in converted.get("body", [])
        for segment in row.get("segments", [])
        if segment.get("kind") == "gap"
    ]
    expected = [{_norm(value) for value in gap.accepted_values} for gap in source.gaps]
    return len(gaps) == len(expected) and all(g & e for g, e in zip(gaps, expected, strict=True))
