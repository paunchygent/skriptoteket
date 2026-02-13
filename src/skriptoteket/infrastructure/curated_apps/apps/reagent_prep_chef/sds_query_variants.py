from __future__ import annotations

import re


def looks_like_formula(value: str) -> bool:
    """Return True when the string looks like a chemical formula."""
    if not value:
        return False
    if not re.fullmatch(r"[A-Za-z0-9().·]+", value):
        return False
    return bool(re.search(r"[A-Z]", value))


def normalize_formula_variants(value: str) -> list[str]:
    """Generate normalized formula variants to improve PubChem matching."""
    sanitized = value.strip().replace(" ", "")
    if not sanitized:
        return []
    parsed = _parse_formula_counts(sanitized)
    if not parsed:
        fallback = re.sub(r"[^A-Za-z0-9]", "", sanitized)
        return [fallback] if fallback else []
    counts, order = parsed
    raw_order = _format_formula(counts, order)
    hill_order = _format_formula(counts, _hill_order(order))
    variants = [sanitized, raw_order, hill_order]
    return dedupe_preserve_order([variant for variant in variants if variant])


def extract_autocomplete_terms(value: str) -> list[str]:
    """Split autocomplete terms into name + formula candidates."""
    cleaned = value.strip()
    if not cleaned:
        return []
    terms = [cleaned]
    match = re.search(r"\(([^)]+)\)", cleaned)
    if match:
        formula = match.group(1).strip()
        if formula:
            terms.append(formula)
        without = cleaned.replace(match.group(0), "").strip()
        if without:
            terms.append(without)
    return dedupe_preserve_order([term for term in terms if term])


def dedupe_preserve_order(values: list[str]) -> list[str]:
    """Remove duplicates while preserving original order."""
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def _parse_formula_counts(value: str) -> tuple[dict[str, int], list[str]] | None:
    formula = value.replace("·", ".")
    segments = [segment for segment in formula.split(".") if segment]
    total: dict[str, int] = {}
    order: list[str] = []
    for segment in segments:
        result = _parse_segment(segment)
        if result is None:
            return None
        counts, segment_order = result
        for element in segment_order:
            if element not in order:
                order.append(element)
        for element, count in counts.items():
            total[element] = total.get(element, 0) + count
    return (total, order)


def _parse_segment(segment: str) -> tuple[dict[str, int], list[str]] | None:
    stack: list[dict[str, int]] = []
    stack_order: list[list[str]] = []
    counts: dict[str, int] = {}
    order: list[str] = []
    index = 0
    leading_multiplier = 1
    if segment and segment[0].isdigit():
        multiplier, index = _parse_number(segment, index)
        if multiplier is None:
            multiplier = 1
        leading_multiplier = multiplier
    length = len(segment)
    while index < length:
        char = segment[index]
        if char == "(":
            stack.append(counts)
            stack_order.append(order)
            counts = {}
            order = []
            index += 1
            continue
        if char == ")":
            index += 1
            multiplier, index = _parse_number(segment, index)
            if multiplier is None:
                multiplier = 1
            counts = {element: count * multiplier for element, count in counts.items()}
            prev_counts = stack.pop() if stack else {}
            prev_order = stack_order.pop() if stack_order else []
            for element in order:
                if element not in prev_order:
                    prev_order.append(element)
            for element, count in counts.items():
                prev_counts[element] = prev_counts.get(element, 0) + count
            counts = prev_counts
            order = prev_order
            continue
        if char.isupper():
            symbol = char
            index += 1
            if index < length and segment[index].islower():
                symbol += segment[index]
                index += 1
            multiplier, index = _parse_number(segment, index)
            if multiplier is None:
                multiplier = 1
            counts[symbol] = counts.get(symbol, 0) + multiplier
            if symbol not in order:
                order.append(symbol)
            continue
        if char.isdigit():
            index += 1
            continue
        index += 1
    if stack:
        return None
    if leading_multiplier != 1:
        counts = {element: count * leading_multiplier for element, count in counts.items()}
    return (counts, order)


def _parse_number(value: str, index: int) -> tuple[int | None, int]:
    start = index
    length = len(value)
    while index < length and value[index].isdigit():
        index += 1
    if index == start:
        return (None, index)
    return (int(value[start:index]), index)


def _format_formula(counts: dict[str, int], order: list[str]) -> str:
    parts: list[str] = []
    for element in order:
        count = counts.get(element)
        if not count:
            continue
        suffix = "" if count == 1 else str(count)
        parts.append(f"{element}{suffix}")
    return "".join(parts)


def _hill_order(order: list[str]) -> list[str]:
    if "C" in order:
        remaining = [element for element in order if element not in {"C", "H"}]
        return ["C", "H", *sorted(remaining)]
    return sorted(order)
