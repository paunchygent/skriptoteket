"""Raw-source download, parsing and extraction for the misspelling data build.

Every remote artifact is pinned by URL and SHA-256 so the build either
reproduces the committed data or fails loudly.  Parsers here only turn a
downloaded artifact into candidate ``(correct, miss)`` pairs; ranking,
real-word filtering and serialization belong to
``scripts/build_answer_misspellings.py``.
"""

from __future__ import annotations

import hashlib
import itertools
import re
import urllib.request
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

LANGUAGE_SWEDISH = "sv"
LANGUAGE_ENGLISH = "en"

# Rank scale: every learner-attested source outranks every editor source, and
# observed editor errors outrank derived bot rules.  Rank breaks ties inside a
# word's misspelling list before frequency and lexical order.
DALAJ_RANK_O = 5
DALAJ_RANK_MIXED_O = 4
BIRKBECK_RANK = 5
LOVS_RANK = 2
WIKIPEDIA_RANK = 2
AWB_RANK = 1

WORD_LETTERS = re.compile(r"^[A-Za-zÅÄÖåäöÉéÜüÈèÀà]+$")

USER_AGENT = "skriptoteket-answer-misspellings-build/1.0 (repository data build)"

KEYBOARD_LAYOUTS: dict[str, tuple[str, ...]] = {
    LANGUAGE_SWEDISH: ("qwertyuiopå", "asdfghjklöä", "zxcvbnm"),
    LANGUAGE_ENGLISH: ("qwertyuiop", "asdfghjkl", "zxcvbnm"),
}


@dataclass(frozen=True, slots=True)
class RawSource:
    name: str
    url: str
    sha256: str


@dataclass(frozen=True, slots=True)
class AttestedPair:
    correct: str
    miss: str
    rank: int


SOURCES: tuple[RawSource, ...] = (
    RawSource(
        name="dalaj-ged-superlim.zip",
        url=(
            "https://svn.spraakdata.gu.se/sb-arkiv/pub/dalaj/"
            "dalaj-ged-superlim/dalaj-ged-superlim.zip"
        ),
        sha256="7f40e1ea3ac11bb33263d1b81f4158ff9b438d3263006362247072acf95f0146",
    ),
    RawSource(
        name="sv_SE.dic",
        url=(
            "https://raw.githubusercontent.com/LibreOffice/dictionaries/"
            "67032ee957631908098a72edf48dc81cac27e369/sv_SE/dictionaries/sv_SE.dic"
        ),
        sha256="384a2126eff333f5f6f9790ae892554546f53948d2988c600397cb5ad6ce66e8",
    ),
    RawSource(
        name="sv_SE.aff",
        url=(
            "https://raw.githubusercontent.com/LibreOffice/dictionaries/"
            "67032ee957631908098a72edf48dc81cac27e369/sv_SE/dictionaries/sv_SE.aff"
        ),
        sha256="b721c9d44bee912feb182b601a1bc2ae3e7dffef660f4130cf2751867488a9dd",
    ),
    RawSource(
        name="en_US.dic",
        url=(
            "https://raw.githubusercontent.com/LibreOffice/dictionaries/"
            "67032ee957631908098a72edf48dc81cac27e369/en/en_US.dic"
        ),
        sha256="f0b1a234bd178bdd01875b2a392a9647f888b8fe879f79c52aae62c2759b3647",
    ),
    RawSource(
        name="en_US.aff",
        url=(
            "https://raw.githubusercontent.com/LibreOffice/dictionaries/"
            "67032ee957631908098a72edf48dc81cac27e369/en/en_US.aff"
        ),
        sha256="e746c882dd6f303c2c46e7452804b9201115a6942cfeb15f18f8edf774d2e24e",
    ),
    RawSource(
        name="lovs-stavfel.wikitext",
        url=(
            "https://sv.wikipedia.org/w/index.php"
            "?title=Wikipedia:Lista_%C3%B6ver_vanliga_spr%C3%A5kfel"
            "&oldid=59163295&action=raw"
        ),
        sha256="7f7d43da0fcd657a588cfb0cb3c332e78e177935da74546a843e9c386cdb406b",
    ),
    RawSource(
        name="awb-typos.wikitext",
        url=(
            "https://sv.wikipedia.org/w/index.php"
            "?title=Wikipedia:AutoWikiBrowser/Typos&oldid=59749383&action=raw"
        ),
        sha256="6a193c970ab1e3ab364156b0dd75abca802da106c79588c60220280466ddb9ce",
    ),
    RawSource(
        name="for-machines.wikitext",
        url=(
            "https://en.wikipedia.org/w/index.php"
            "?title=Wikipedia:Lists_of_common_misspellings/For_machines"
            "&oldid=1199637275&action=raw"
        ),
        sha256="3b6a9290e5aaad968da7ec769a5174adb45247688ef7ae097fd2dd80237a3050",
    ),
    RawSource(
        name="birkbeck-missp.dat",
        url="https://titan.dcs.bbk.ac.uk/~ROGER/missp.dat",
        sha256="ed7d8c91961a1201632351943571e77af2011cdf45d24304c4d7cad6cf77ea15",
    ),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_raw_sources(
    raw_dir: Path, *, refresh: bool = False, log: Callable[[str], object] = print
) -> dict[str, Path]:
    """Download every pinned source into ``raw_dir`` and verify its checksum."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    resolved: dict[str, Path] = {}
    for source in SOURCES:
        target = raw_dir / source.name
        if refresh or not target.exists() or sha256_file(target) != source.sha256:
            request = urllib.request.Request(source.url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=120) as response:
                target.write_bytes(response.read())
            actual = sha256_file(target)
            if actual != source.sha256:
                raise RuntimeError(
                    f"{source.name}: expected sha256 {source.sha256}, downloaded {actual}"
                )
            log(f"downloaded {source.name} ({target.stat().st_size} bytes)")
        resolved[source.name] = target
    return resolved


def parse_dalaj_pairs(zip_path: Path) -> list[AttestedPair]:
    """Extract single-token DaLAJ-GED-Superlim 2.0 O and mixed-O pairs."""
    import json

    pairs: list[AttestedPair] = []
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.namelist():
            if not member.endswith(".jsonl"):
                continue
            for raw_line in archive.read(member).decode("utf-8").splitlines():
                if not raw_line.strip():
                    continue
                row = json.loads(raw_line)
                if row.get("label") != "incorrect":
                    continue
                label = str(row.get("meta", {}).get("error_label") or "")
                labels = [part.strip() for part in label.split(",")]
                if "O" not in labels:
                    continue
                rank = DALAJ_RANK_O if label == "O" else DALAJ_RANK_MIXED_O
                confusion = row.get("meta", {}).get("confusion_pair") or {}
                miss = str(confusion.get("incorrect_span") or "").strip()
                correct = str(confusion.get("correction") or "").strip()
                if not _single_token_pair(correct, miss):
                    continue
                pairs.append(AttestedPair(correct=correct, miss=miss, rank=rank))
    return pairs


def _clean_wiki_cell(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value)
    value = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", value)
    value = re.sub(r"\[\[([^\]]*)\]\]", r"\1", value)
    return value.replace("'''", "").replace("''", "").strip()


def _explicit_miss_variants(raw_miss: str) -> list[str]:
    """Keep written forms, not guessed expansions of inflection shorthand.

    For example ``aborre, -n -ar`` does not attest ``aborrear`` as a spelling
    of ``abborre``. Inflected pairs come from the learner corpus instead.
    """
    return [part.strip() for part in raw_miss.split(",") if WORD_LETTERS.fullmatch(part.strip())]


def parse_lovs_pairs(wikitext: str) -> list[AttestedPair]:
    """Parse the sv.wikipedia LÖVS misspelling tables in the stavfel sections."""
    pairs: list[AttestedPair] = []
    sections = re.split(r"^==\s*(.*?)\s*==\s*$", wikitext, flags=re.M)
    heading: str | None = None
    row_pattern = re.compile(r"^\|-\s*\n((?:^\|[^\-\}].*\n?)+)", flags=re.M)
    for index, chunk in enumerate(sections):
        if index % 2 == 1:
            heading = chunk.strip()
            continue
        if heading is None or "stavfel" not in heading.lower():
            continue
        for match in row_pattern.finditer(chunk):
            cells = [cell.strip() for cell in match.group(1).strip().split("||")]
            if len(cells) < 2:
                continue
            miss_raw = _clean_wiki_cell(cells[0].lstrip("| "))
            correct_raw = _clean_wiki_cell(cells[1])
            if not miss_raw or not correct_raw or miss_raw.lower().startswith("felaktig"):
                continue
            miss_variants = _explicit_miss_variants(miss_raw)
            correct_variants = [
                part.strip() for part in re.split(r"[,/]", correct_raw) if part.strip()
            ]
            for miss in miss_variants:
                for correct in correct_variants:
                    if _single_token_pair(correct, miss):
                        pairs.append(AttestedPair(correct=correct, miss=miss, rank=LOVS_RANK))
    return pairs


AWB_RULE = re.compile(r'<Typo word="(.*?)" find="(.*?)" replace="(.*?)"\s*/>')
AWB_GROUP = re.compile(r"\(([^()]*)\)(\?)?")
AWB_MAX_EXPANSION = 60


def parse_awb_pairs(wikitext: str) -> list[AttestedPair]:
    """Expand the strictly attested single-group AutoWikiBrowser typo rules."""
    pairs: list[AttestedPair] = []
    for _word, find, replace in AWB_RULE.findall(wikitext):
        pattern = re.sub(r"^\\b", "", find.strip())
        pattern = re.sub(r"\\b$", "", pattern)
        if "(?" in pattern or "\\w" in pattern or "\\d" in pattern or "[" in pattern:
            continue
        matches = list(AWB_GROUP.finditer(pattern))
        if len(matches) > 1:
            continue
        if not matches:
            if _single_token_pair(replace, pattern):
                pairs.append(AttestedPair(correct=replace, miss=pattern, rank=AWB_RANK))
            continue
        alternatives: list[list[str]] = []
        for match in matches:
            values = match.group(1).split("|")
            if match.group(2):
                values = values + [""]
            alternatives.append(values)
        total = 1
        for values in alternatives:
            total *= len(values)
        if total > AWB_MAX_EXPANSION:
            continue
        literals: list[str] = []
        last = 0
        for match in matches:
            literals.append(pattern[last : match.start()])
            last = match.end()
        literals.append(pattern[last:])
        literals = [literal.replace("\\b", "") for literal in literals]
        for combination in itertools.product(*alternatives):
            miss = "".join(
                literal + value for literal, value in zip(literals, combination + ("",))
            ).replace("\\", "")
            correct = replace
            for position, value in enumerate(combination, start=1):
                correct = correct.replace(f"${position}", value)
            correct = correct.replace("\\", "").strip()
            if "$" in correct or not _single_token_pair(correct, miss):
                continue
            pairs.append(AttestedPair(correct=correct, miss=miss, rank=AWB_RANK))
    return pairs


def parse_birkbeck_pairs(text: str) -> list[AttestedPair]:
    """Parse Birkbeck ``missp.dat``: ``$correct`` headers then misspellings."""
    pairs: list[AttestedPair] = []
    correct: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("$"):
            correct = line[1:].strip()
            continue
        if correct is not None and _single_token_pair(correct, line):
            pairs.append(AttestedPair(correct=correct, miss=line, rank=BIRKBECK_RANK))
    return pairs


def parse_for_machines_pairs(text: str) -> list[AttestedPair]:
    """Parse the Wikipedia For machines list: ``misspelling->correction``."""
    pairs: list[AttestedPair] = []
    for line in text.splitlines():
        if "->" not in line:
            continue
        miss, _, rest = line.partition("->")
        correct = rest.strip()
        if "," in correct:
            continue
        if _single_token_pair(correct, miss.strip()):
            pairs.append(AttestedPair(correct=correct, miss=miss.strip(), rank=WIKIPEDIA_RANK))
    return pairs


def _single_token_pair(correct: str, miss: str) -> bool:
    if not correct or not miss:
        return False
    if not WORD_LETTERS.match(correct) or not WORD_LETTERS.match(miss):
        return False
    return correct.casefold() != miss.casefold()


def filter_rep_rules(
    rules: tuple[tuple[str, str], ...],
) -> tuple[tuple[str, str], ...]:
    """Drop whitespace, underscore and dot rules; keep anchors in aff order."""
    kept: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for wrong, right in rules:
        if not wrong or not right:
            continue
        if any(character in " \t_." for character in wrong + right):
            continue
        if (wrong, right) in seen:
            continue
        seen.add((wrong, right))
        kept.append((wrong, right))
    return tuple(kept)


def keyboard_neighbours(rows: tuple[str, ...]) -> dict[str, tuple[str, ...]]:
    """Symmetric QWERTY neighbours from staggered layout rows."""
    positions: dict[str, tuple[float, float]] = {}
    for row_index, row in enumerate(rows):
        offset = row_index * 0.5
        for column, character in enumerate(row):
            positions[character] = (float(row_index), column + offset)
    neighbours: dict[str, set[str]] = {character: set() for character in positions}
    for character, (y, x) in positions.items():
        for other, (other_y, other_x) in positions.items():
            if character == other or abs(y - other_y) > 1:
                continue
            distance = 1.0 if y == other_y else 0.75
            if abs(x - other_x) <= distance:
                neighbours[character].add(other)
    return {character: tuple(sorted(values)) for character, values in sorted(neighbours.items())}
