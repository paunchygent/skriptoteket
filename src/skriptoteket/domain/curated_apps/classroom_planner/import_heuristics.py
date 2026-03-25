"""Heuristic class-list parsing for Klassrumskartan imports.

Purpose:
  Infer a class name and likely student roster rows from noisy text or tabular
  roster inputs while keeping the parsing logic framework-free.

Relationships:
  - Implements `ClassListHeuristicParserProtocol`.
  - Consumes normalized text/rows from the infrastructure extractor.
  - Produces `ClassListImportPreview` contracts for the application/web layer.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from collections import defaultdict
from typing import Iterable, Optional

from skriptoteket.application.curated_apps.classroom_planner.import_contracts import (
    ClassListImportPreview,
    ParsedStudentRow,
)
from skriptoteket.protocols.classroom_planner_imports import ClassListHeuristicParserProtocol

# Constants from prototype
HEADER_WORDS = {
    "klasslista",
    "klass",
    "class",
    "classlist",
    "efternamn",
    "familjenamn",
    "firstname",
    "forename",
    "förnamn",
    "givenname",
    "lastname",
    "student",
    "students",
    "elev",
    "elevlista",
    "lista",
    "namn",
    "nr",
    "no",
    "number",
    "sida",
    "page",
    "pages",
    "surname",
}

MONTH_WORDS = {
    "jan",
    "feb",
    "mar",
    "apr",
    "may",
    "jun",
    "jul",
    "aug",
    "sep",
    "oct",
    "nov",
    "dec",
    "januari",
    "februari",
    "mars",
    "april",
    "maj",
    "juni",
    "juli",
    "augusti",
    "september",
    "oktober",
    "november",
    "december",
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
}

CLASS_STOP_PREFIXES = {
    "av",
    "den",
    "id",
    "no",
    "nr",
    "of",
    "page",
    "pages",
    "row",
    "sida",
    "the",
}

NAME_ALLOWED_CHARS = re.compile(r"^[\wÀ-ÖØ-öø-ÿ'’.,\- ]+$", re.UNICODE)
BULLET_PREFIX = re.compile(r"^[\-\u2022•]+\s*")
CLASS_CODE_RE = re.compile(r"^([A-ZÅÄÖ]{1,6})(\d{1,4})([A-ZÅÄÖ]{0,2})$", re.I)
CLASS_CODE_TOKEN_RE = re.compile(
    r"(?<![A-ZÅÄÖ0-9])([A-ZÅÄÖ]{1,6}(?:[\s._/-]*\d{1,4})(?:[\s._/-]*[A-ZÅÄÖ]{0,2})?)(?![A-ZÅÄÖ0-9])",
    re.I,
)
INDEX_RE = re.compile(r"^\s*(\d{1,4})[.\s]+(.+?)\s*$")
WHOLE_TEXT_RECORD_RE = re.compile(
    r"(?:^|\b)(\d{1,4})(?:\s+|[\t;|]+)"
    r"([A-Za-zÀ-ÖØ-öø-ÿ'’.\- ]+?,\s*[A-Za-zÀ-ÖØ-öø-ÿ'’.\- ]+?)"
    r"(?=(?:\s+\d{1,4}(?:\s+|[\t;|]+))|$)",
    re.MULTILINE,
)
FAMILY_NAME_SUFFIXES = (
    "berg",
    "blad",
    "borg",
    "felt",
    "gren",
    "holm",
    "kvist",
    "lund",
    "man",
    "mark",
    "qvist",
    "quist",
    "sen",
    "skog",
    "son",
    "sson",
    "stedt",
    "strand",
    "strom",
    "ström",
    "vall",
    "wall",
)
ROW_NAME_ORDER_FAMILY_GIVEN = "family_given"
ROW_NAME_ORDER_GIVEN_FAMILY = "given_family"


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    replacements = {
        "\u00a0": " ",
        "\u200b": "",
        "\u200c": "",
        "\u200d": "",
        "\u00ad": "",
        "\ufeff": "",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text


def collapse_ws(text: str) -> str:
    return re.sub(r"\s+", " ", normalize_text(text)).strip()


def strip_outer_quotes(text: str) -> str:
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        return text[1:-1].strip()
    return text


def canonical_name_key(name: str) -> str:
    text = unicodedata.normalize("NFKD", name)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold()
    text = re.sub(r"[^0-9a-z]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_class_code(text: str) -> Optional[str]:
    candidate = collapse_ws(strip_outer_quotes(text))
    if not candidate:
        return None

    compact = re.sub(r"[\s._/-]+", "", candidate).upper()
    match = CLASS_CODE_RE.fullmatch(compact)
    if not match:
        return None

    prefix = match.group(1).casefold()
    if prefix in HEADER_WORDS or prefix in MONTH_WORDS or prefix in CLASS_STOP_PREFIXES:
        return None

    return compact


def canonical_class_key(class_name: Optional[str]) -> Optional[str]:
    if not class_name:
        return None

    normalized = normalize_class_code(class_name)
    if normalized is not None:
        return normalized

    text = unicodedata.normalize("NFKD", class_name)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold()
    text = re.sub(r"[^0-9a-z]+", "", text)
    return text or None


def has_letters(text: str) -> bool:
    return any(ch.isalpha() for ch in text)


def looks_like_metadata(text: str) -> bool:
    candidate = collapse_ws(strip_outer_quotes(text))
    lowered = candidate.casefold()
    if not lowered:
        return True

    words = [word for word in re.split(r"[\s,;|]+", lowered) if word]
    if lowered in HEADER_WORDS or "".join(words) in HEADER_WORDS:
        return True
    if words and set(words) <= HEADER_WORDS:
        return True
    if normalize_class_code(candidate) is not None:
        return True
    if re.search(r"\b(sida|page|pages)\b", lowered):
        return True
    if re.search(r"\bklasslista\b", lowered) or re.search(r"\bclass\s*list\b", lowered):
        return True
    if any(word in MONTH_WORDS for word in words) and re.search(r"\b\d{4}\b", lowered):
        return True
    return False


def is_probable_name_text(text: str) -> bool:
    candidate = collapse_ws(strip_outer_quotes(text)).strip(" ,;|")
    if not candidate or looks_like_metadata(candidate):
        return False
    if any(ch.isdigit() for ch in candidate):
        return False
    if not has_letters(candidate):
        return False
    if not NAME_ALLOWED_CHARS.fullmatch(candidate):
        return False

    if "," in candidate:
        parts = [part.strip() for part in candidate.split(",") if part.strip()]
        if len(parts) < 2:
            return False
        if any(looks_like_metadata(part) for part in parts):
            return False
        return True

    tokens = candidate.split()
    if len(tokens) < 2:
        return False
    if set(token.casefold() for token in tokens) <= HEADER_WORDS:
        return False
    return True


def family_name_likelihood(token: str) -> int:
    candidate = collapse_ws(strip_outer_quotes(token)).strip(" ,;|")
    if not candidate or not has_letters(candidate):
        return 0

    lowered = candidate.casefold()
    score = 0
    if " " in candidate:
        score += 2
    if len(candidate) >= 7:
        score += 1
    if any(lowered.endswith(suffix) for suffix in FAMILY_NAME_SUFFIXES):
        score += 3
    return score


class InternalStudentRecord:
    def __init__(
        self,
        full_name: str,
        given_name: Optional[str],
        family_name: Optional[str],
        raw_name: str,
        row_number: Optional[int],
        source: str,
        class_name: Optional[str] = None,
        order_hint: int = 0,
    ) -> None:
        self.full_name = full_name
        self.given_name = given_name
        self.family_name = family_name
        self.raw_name = raw_name
        self.row_number = row_number
        self.source = source
        self.class_name = class_name
        self.order_hint = order_hint

    @property
    def canonical_name(self) -> str:
        return canonical_name_key(self.full_name)

    @property
    def canonical_class_name(self) -> Optional[str]:
        return canonical_class_key(self.class_name)

    @property
    def merge_priority(self) -> tuple[int, int, int, int, int]:
        has_class = int(bool(self.canonical_class_name))
        has_row = int(self.row_number is not None)
        structured = int(bool(self.given_name and self.family_name))
        has_non_ascii = int(any(ord(ch) > 127 for ch in self.full_name))
        return (has_class, has_row, structured, has_non_ascii, len(self.full_name))


class StudentAccumulator:
    def __init__(self) -> None:
        self.records: list[InternalStudentRecord] = []
        self._counter = 0

    def add(self, record: InternalStudentRecord) -> None:
        compatible_indices = [
            index
            for index, existing in enumerate(self.records)
            if self._records_are_compatible(existing, record)
        ]

        if not compatible_indices:
            record.order_hint = self._next_counter()
            self.records.append(record)
            return

        merged = self._merge_student_records(
            [self.records[index] for index in compatible_indices] + [record]
        )
        merged.order_hint = min(self.records[index].order_hint for index in compatible_indices)

        first_index = compatible_indices[0]
        self.records[first_index] = merged
        for index in reversed(compatible_indices[1:]):
            del self.records[index]

    def _next_counter(self) -> int:
        value = self._counter
        self._counter += 1
        return value

    def _records_are_compatible(
        self, left: InternalStudentRecord, right: InternalStudentRecord
    ) -> bool:
        if left.canonical_name != right.canonical_name:
            return False
        if (
            left.row_number is not None
            and right.row_number is not None
            and left.row_number != right.row_number
        ):
            return False
        left_class = left.canonical_class_name
        right_class = right.canonical_class_name
        if left_class is not None and right_class is not None and left_class != right_class:
            return False
        return True

    def _merge_student_records(self, records: list[InternalStudentRecord]) -> InternalStudentRecord:
        best = max(records, key=lambda rec: rec.merge_priority)
        row_number = best.row_number
        if row_number is None:
            row_number = next(
                (rec.row_number for rec in records if rec.row_number is not None), None
            )
        class_name = best.class_name
        if not class_name:
            class_name = next((rec.class_name for rec in records if rec.class_name), None)
        name_record = best
        if not (name_record.given_name and name_record.family_name):
            structured_candidates = [rec for rec in records if rec.given_name and rec.family_name]
            if structured_candidates:
                name_record = max(structured_candidates, key=lambda rec: rec.merge_priority)
        source_record = best
        if (
            source_record.source != name_record.source
            and name_record.merge_priority > source_record.merge_priority
        ):
            source_record = name_record
        return InternalStudentRecord(
            full_name=name_record.full_name,
            given_name=name_record.given_name,
            family_name=name_record.family_name,
            raw_name=name_record.raw_name,
            row_number=row_number,
            source=source_record.source,
            class_name=class_name,
        )

    def ordered(self) -> list[InternalStudentRecord]:
        return sorted(
            self.records,
            key=lambda rec: (
                rec.canonical_class_name is None,
                rec.canonical_class_name or "",
                rec.row_number is None,
                rec.row_number if rec.row_number is not None else 10**9,
                rec.order_hint,
            ),
        )


class ClassListHeuristicParser(ClassListHeuristicParserProtocol):
    def parse(
        self,
        *,
        file_name: str,
        text: str | None,
        rows: list[list[str]] | None,
    ) -> ClassListImportPreview:
        inferred_class_name = self._detect_class_name(file_name, text, rows)
        row_delimiter = self._row_delimiter_for_file_name(file_name)

        accumulator = StudentAccumulator()

        if rows:
            for record in self._parse_rows(
                rows,
                "rows",
                inferred_class_name,
                delimiter=row_delimiter,
            ):
                accumulator.add(record)

        if text:
            for record in self._parse_text(text, "text", inferred_class_name):
                accumulator.add(record)

        parsed_students = [
            ParsedStudentRow(
                full_name=rec.full_name,
                given_name=rec.given_name,
                family_name=rec.family_name,
                row_number=rec.row_number,
            )
            for rec in accumulator.ordered()
        ]

        # For this prototype, we don't have a sophisticated "ambiguous row" detection
        # yet beyond what is_probable_name_text filters out.
        # Future PR can add more logic here.
        return ClassListImportPreview(
            file_name=file_name,
            suggested_class_name=inferred_class_name,
            parsed_students=parsed_students,
            ambiguous_rows=[],
        )

    def _row_delimiter_for_file_name(self, file_name: str) -> str:
        lowered = file_name.casefold()
        if lowered.endswith(".csv"):
            return ","
        if lowered.endswith(".tsv"):
            return "\t"
        return "\t"

    def _detect_class_name(
        self, file_name: str, text: str | None, rows: list[list[str]] | None
    ) -> str | None:
        content_scores: dict[str, int] = defaultdict(int)
        if text:
            self._merge_score_maps(content_scores, self._score_class_candidates_from_text(text))
        if rows:
            self._merge_score_maps(content_scores, self._score_class_candidates_from_rows(rows))

        path_scores = self._score_class_candidates_from_path(file_name)

        class_name = self._select_best_class_candidate(content_scores, minimum_score=50)
        if class_name is None:
            class_name = self._select_best_class_candidate(path_scores, minimum_score=1)
        if class_name is None:
            class_name = self._select_best_class_candidate(content_scores, minimum_score=1)
        return class_name

    def _merge_score_maps(self, target: dict[str, int], incoming: dict[str, int]) -> None:
        for candidate, score in incoming.items():
            target[candidate] += score

    def _score_class_candidates_from_text(self, text: str) -> dict[str, int]:
        normalized = normalize_text(text)
        lines = [line for line in normalized.splitlines() if collapse_ws(line)]
        anchors = self._find_header_anchors(lines)
        scores: dict[str, int] = defaultdict(int)
        for index, line in enumerate(lines):
            self._merge_score_maps(
                scores, self._score_class_candidates_in_line(line, index, anchors)
            )
        return scores

    def _score_class_candidates_from_rows(self, rows: Iterable[list[str]]) -> dict[str, int]:
        materialized_rows = list(rows)
        row_texts = [
            " ".join(collapse_ws(cell) for cell in row if collapse_ws(cell))
            for row in materialized_rows
        ]
        anchors = self._find_header_anchors(row_texts)
        scores: dict[str, int] = defaultdict(int)
        for row_index, row in enumerate(materialized_rows):
            cleaned_cells = [
                collapse_ws(strip_outer_quotes(cell))
                for cell in row
                if collapse_ws(strip_outer_quotes(cell))
            ]
            if not cleaned_cells:
                continue
            row_bonus = self._positional_bonus(row_index, anchors)
            row_context_bonus = self._class_context_bonus(" ".join(cleaned_cells))
            for cell in cleaned_cells:
                candidate = normalize_class_code(cell)
                if candidate is not None:
                    scores[candidate] += 130 + row_bonus + row_context_bonus
                self._merge_score_maps(
                    scores, self._score_class_candidates_in_line(cell, row_index, anchors)
                )
            row_text = " ".join(cleaned_cells)
            row_line_scores = self._score_class_candidates_in_line(row_text, row_index, anchors)
            for candidate, score in row_line_scores.items():
                scores[candidate] += max(10, score // 2)
        return scores

    def _score_class_candidates_from_path(self, file_name: str) -> dict[str, int]:
        scores: dict[str, int] = defaultdict(int)
        stem = file_name.split(".")[0]
        for match in CLASS_CODE_TOKEN_RE.finditer(stem):
            candidate = normalize_class_code(match.group(1))
            if candidate is not None:
                scores[candidate] += 5
        return scores

    def _select_best_class_candidate(
        self, scores: dict[str, int], minimum_score: int = 1
    ) -> str | None:
        eligible = [
            (candidate, score) for candidate, score in scores.items() if score >= minimum_score
        ]
        if not eligible:
            return None
        eligible.sort(key=lambda item: (-item[1], item[0]))
        return eligible[0][0]

    def _class_context_bonus(self, text: str) -> int:
        lowered = collapse_ws(text).casefold()
        bonus = 0
        if re.search(r"\b(klass|class|grupp|group)\b", lowered):
            bonus += 25
        if re.search(r"\bklasslista\b", lowered) or re.search(r"\bclass\s*list\b", lowered):
            bonus += 35
        if re.search(r"\b(nr|namn|student|students|elev)\b", lowered):
            bonus += 10
        return bonus

    def _find_header_anchors(self, lines: list[str]) -> list[int]:
        anchors: list[int] = []
        for index, line in enumerate(lines[:60]):
            lowered = collapse_ws(line).casefold()
            if not lowered:
                continue
            if re.search(r"\bklasslista\b", lowered) or re.search(r"\bclass\s*list\b", lowered):
                anchors.append(index)
                continue
            if re.search(r"\b(nr|namn|student|students|elev)\b", lowered):
                anchors.append(index)
        return anchors

    def _positional_bonus(self, index: int, anchors: list[int]) -> int:
        bonus = 0
        if index < 5:
            bonus += 45
        elif index < 12:
            bonus += 25
        elif index < 25:
            bonus += 10
        if anchors:
            distance = min(abs(index - anchor) for anchor in anchors)
            if distance <= 2:
                bonus += 40
            elif distance <= 5:
                bonus += 20
        return bonus

    def _score_class_candidates_in_line(
        self, line: str, line_index: int, anchors: list[int]
    ) -> dict[str, int]:
        scores: dict[str, int] = defaultdict(int)
        cleaned = collapse_ws(strip_outer_quotes(line))
        if not cleaned:
            return scores
        bonus = self._positional_bonus(line_index, anchors)
        context_bonus = self._class_context_bonus(cleaned)
        whole_line_candidate = normalize_class_code(cleaned)
        if whole_line_candidate is not None:
            scores[whole_line_candidate] += 140 + bonus + context_bonus
        for delimiter in ("\t", ";", "|", ","):
            if delimiter not in cleaned:
                continue
            try:
                tokens = next(csv.reader([cleaned], delimiter=delimiter, skipinitialspace=True))
            except Exception:
                tokens = cleaned.split(delimiter)
            for token in tokens:
                candidate = normalize_class_code(token)
                if candidate is not None:
                    scores[candidate] += 100 + bonus + context_bonus
        for match in CLASS_CODE_TOKEN_RE.finditer(cleaned):
            candidate = normalize_class_code(match.group(1))
            if candidate is None:
                continue
            token_score = 20 + context_bonus + (bonus // 2)
            if cleaned == collapse_ws(match.group(1)):
                token_score += 60
            scores[candidate] += token_score
        return scores

    def _parse_text(
        self, text: str, source_label: str, class_name: str | None = None
    ) -> list[InternalStudentRecord]:
        records: list[InternalStudentRecord] = []
        for line in self._logical_lines(text):
            parsed = self._extract_candidate_from_text_line(line)
            if parsed is None:
                continue
            row_number, candidate = parsed
            record = self._parse_candidate_name(
                candidate, source=source_label, row_number=row_number, class_name=class_name
            )
            if record is not None:
                records.append(record)
        for match in WHOLE_TEXT_RECORD_RE.finditer(normalize_text(text)):
            row_number = int(match.group(1))
            candidate = match.group(2)
            record = self._parse_candidate_name(
                candidate,
                source=f"{source_label}::whole-text",
                row_number=row_number,
                class_name=class_name,
            )
            if record is not None:
                records.append(record)
        return records

    def _parse_rows(
        self,
        rows: Iterable[list[str]],
        source_label: str,
        class_name: str | None = None,
        *,
        delimiter: str,
    ) -> list[InternalStudentRecord]:
        records: list[InternalStudentRecord] = []
        materialized_rows = list(rows)
        row_name_order = self._infer_two_column_row_name_order(materialized_rows)
        for row in materialized_rows:
            parsed = self._extract_candidate_from_row_like_tokens(
                row,
                delimiter=delimiter,
                row_name_order=row_name_order,
            )
            if parsed is None:
                continue
            row_number, candidate = parsed
            record = self._parse_candidate_name(
                candidate, source=source_label, row_number=row_number, class_name=class_name
            )
            if record is not None:
                records.append(record)
        return records

    def _logical_lines(self, text: str) -> list[str]:
        raw_lines = [normalize_text(line).strip() for line in text.splitlines()]
        raw_lines = [line for line in raw_lines if line]
        merged: list[str] = []
        current: Optional[str] = None
        for line in raw_lines:
            starts_new_record = bool(INDEX_RE.match(line)) or bool(
                re.match(r"^\s*\d{1,4}[,\t;|]", line)
            )
            if starts_new_record:
                if current:
                    merged.append(current)
                current = line
                continue
            if current and not looks_like_metadata(line):
                current = f"{current} {line}"
                continue
            if current:
                merged.append(current)
                current = None
            merged.append(line)
        if current:
            merged.append(current)
        return merged

    def _extract_candidate_from_text_line(self, line: str) -> Optional[tuple[Optional[int], str]]:
        raw = normalize_text(line).strip()
        if not raw:
            return None
        direct = INDEX_RE.match(raw)
        if direct:
            row_number = int(direct.group(1))
            candidate = direct.group(2)
            if self._parse_candidate_name(candidate, source="", row_number=row_number) is not None:
                return row_number, candidate
        for delimiter, tokens in self._split_delimited_line(raw):
            parsed = self._extract_candidate_from_row_like_tokens(tokens, delimiter)
            if parsed is not None:
                return parsed
        if is_probable_name_text(raw):
            return None, raw
        return None

    def _split_delimited_line(self, line: str) -> list[tuple[str, list[str]]]:
        variants: list[tuple[str, list[str]]] = []
        for delimiter in ("\t", ";", "|", ","):
            if delimiter not in line:
                continue
            try:
                tokens = next(csv.reader([line], delimiter=delimiter, skipinitialspace=True))
            except Exception:
                continue
            variants.append((delimiter, tokens))
        return variants

    def _infer_two_column_row_name_order(self, rows: Iterable[list[str]]) -> str | None:
        family_given_votes = 0
        given_family_votes = 0

        for row in rows:
            cleaned = [
                strip_outer_quotes(collapse_ws(token)) for token in row if collapse_ws(token)
            ]
            if self._find_first_numeric_index(cleaned) is not None:
                continue
            textish = [
                token for token in cleaned if has_letters(token) and not looks_like_metadata(token)
            ]
            if len(textish) != 2:
                continue

            first_score = family_name_likelihood(textish[0])
            second_score = family_name_likelihood(textish[1])
            if first_score >= second_score + 2:
                family_given_votes += 1
            elif second_score >= first_score + 2:
                given_family_votes += 1

        if family_given_votes > given_family_votes:
            return ROW_NAME_ORDER_FAMILY_GIVEN
        if given_family_votes > family_given_votes:
            return ROW_NAME_ORDER_GIVEN_FAMILY
        return None

    def _compose_split_name_candidate(
        self,
        textish: list[str],
        delimiter: str,
        row_name_order: str | None,
    ) -> str | None:
        if len(textish) < 2:
            return None

        family_first = row_name_order == ROW_NAME_ORDER_FAMILY_GIVEN or (
            row_name_order is None
            and family_name_likelihood(textish[0]) >= family_name_likelihood(textish[1]) + 2
        )
        if delimiter == "," and family_first:
            family_given = f"{textish[0]}, {textish[1]}"
            if is_probable_name_text(family_given):
                return family_given

        if family_first:
            reversed_full_name = f"{textish[1]} {textish[0]}"
            if is_probable_name_text(reversed_full_name):
                return reversed_full_name

        given_family = f"{textish[0]} {textish[1]}"
        if is_probable_name_text(given_family):
            return given_family
        return None

    def _extract_candidate_from_row_like_tokens(
        self,
        tokens: list[str],
        delimiter: str,
        *,
        row_name_order: str | None = None,
    ) -> Optional[tuple[Optional[int], str]]:
        cleaned = [strip_outer_quotes(collapse_ws(token)) for token in tokens]
        index_position = self._find_first_numeric_index(cleaned)
        if index_position is None:
            return self._extract_candidate_without_numeric_index(
                cleaned,
                delimiter,
                row_name_order=row_name_order,
            )
        row_number_str = cleaned[index_position]
        if not row_number_str.isdigit():
            return None
        row_number = int(row_number_str)
        tail = [token for token in cleaned[index_position + 1 :] if token]
        if not tail:
            return None
        for token in tail:
            if "," in token and is_probable_name_text(token):
                return row_number, token
        textish = [token for token in tail if has_letters(token) and not looks_like_metadata(token)]
        split_candidate = self._compose_split_name_candidate(textish, delimiter, row_name_order)
        if split_candidate is not None:
            return row_number, split_candidate
        for token in textish:
            if is_probable_name_text(token):
                return row_number, token
        if len(textish) >= 2:
            joined = " ".join(textish[:2])
            if is_probable_name_text(joined):
                return row_number, joined
        return None

    def _extract_candidate_without_numeric_index(
        self,
        tokens: list[str],
        delimiter: str,
        *,
        row_name_order: str | None = None,
    ) -> Optional[tuple[Optional[int], str]]:
        cleaned = [token for token in tokens if token]
        if not cleaned:
            return None

        for token in cleaned:
            if "," in token and is_probable_name_text(token):
                return None, token

        textish = [
            token for token in cleaned if has_letters(token) and not looks_like_metadata(token)
        ]
        split_candidate = self._compose_split_name_candidate(textish, delimiter, row_name_order)
        if split_candidate is not None:
            return None, split_candidate

        for token in textish:
            if is_probable_name_text(token):
                return None, token

        if len(textish) >= 2:
            joined = " ".join(textish[:2])
            if is_probable_name_text(joined):
                return None, joined
        return None

    def _find_first_numeric_index(self, tokens: list[str]) -> Optional[int]:
        for index, token in enumerate(tokens):
            if re.fullmatch(r"\d{1,4}", collapse_ws(token)):
                return index
        return None

    def _parse_candidate_name(
        self,
        raw_candidate: str,
        source: str,
        row_number: Optional[int],
        class_name: Optional[str] = None,
    ) -> Optional[InternalStudentRecord]:
        candidate = normalize_text(raw_candidate)
        candidate = strip_outer_quotes(candidate)
        candidate = collapse_ws(candidate)
        candidate = BULLET_PREFIX.sub("", candidate).strip(" ,;|")
        if not is_probable_name_text(candidate):
            return None
        if "," in candidate:
            parts = [collapse_ws(part) for part in candidate.split(",") if collapse_ws(part)]
            if len(parts) >= 2:
                family_name = parts[0]
                given_name = " ".join(parts[1:])
                full_name = collapse_ws(f"{given_name} {family_name}")
                return InternalStudentRecord(
                    full_name=full_name,
                    given_name=given_name,
                    family_name=family_name,
                    raw_name=candidate,
                    row_number=row_number,
                    source=source,
                    class_name=class_name,
                )
        return InternalStudentRecord(
            full_name=candidate,
            given_name=None,
            family_name=None,
            raw_name=candidate,
            row_number=row_number,
            source=source,
            class_name=class_name,
        )
