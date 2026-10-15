"""Hunspell ``.dic``/``.aff`` word-form expansion for the misspelling data build.

Expands a hunspell dictionary into the standalone word forms its affix rules
produce, tracking continuation classes so results that hunspell treats as
forbidden, need-an-affix or only-in-compound are not emitted as standalone
words.  Only the affix subset used by ``sv_SE`` and ``en_US`` is implemented:
single prefix, single suffix, cross-product prefix+suffix, ``FLAG`` char/long/
num, ``NEEDAFFIX``, ``FORBIDDENWORD`` and ``ONLYINCOMPOUND``.

Compound words that hunspell assembles at lookup time are out of scope; the
build records that residual in ``ATTRIBUTION.md``.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

AffixRule = tuple[str, str, str, str]  # strip, add, condition, continuation flags


@dataclass(frozen=True, slots=True)
class AffixRules:
    flag_mode: str
    need_affix: str | None
    forbidden: str | None
    only_in_compound: str | None
    prefixes: dict[str, tuple[AffixRule, ...]]
    suffixes: dict[str, tuple[AffixRule, ...]]
    cross_product: dict[str, bool]

    def standalone_allowed(self, flags: frozenset[str]) -> bool:
        blocked = (self.need_affix, self.forbidden, self.only_in_compound)
        return not any(marker and marker in flags for marker in blocked)


@dataclass(slots=True)
class _MutableAffixRules:
    flag_mode: str = "char"
    need_affix: str | None = None
    forbidden: str | None = None
    only_in_compound: str | None = None
    prefixes: dict[str, list[AffixRule]] = field(default_factory=lambda: defaultdict(list))
    suffixes: dict[str, list[AffixRule]] = field(default_factory=lambda: defaultdict(list))
    cross_product: dict[str, bool] = field(default_factory=dict)


def _split_flags(value: str, flag_mode: str) -> frozenset[str]:
    if not value:
        return frozenset()
    if flag_mode in ("char", "utf-8"):
        return frozenset(value)
    if flag_mode == "long":
        return frozenset(value[index : index + 2] for index in range(0, len(value), 2))
    if flag_mode == "num":
        return frozenset(value.split(","))
    raise ValueError(f"unsupported Hunspell flag mode: {flag_mode}")


def parse_affix_file(path: Path) -> AffixRules:
    """Parse the affix directives the expansion and REP extraction need."""
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    parsed = _MutableAffixRules()
    index = 0
    while index < len(lines):
        line = lines[index]
        index += 1
        if not line or line.lstrip().startswith("#"):
            continue
        parts = line.split()
        head = parts[0]
        if head == "FLAG" and len(parts) > 1:
            parsed.flag_mode = parts[1].lower()
            continue
        if head == "NEEDAFFIX" and len(parts) > 1:
            parsed.need_affix = parts[1]
            continue
        if head == "FORBIDDENWORD" and len(parts) > 1:
            parsed.forbidden = parts[1]
            continue
        if head == "ONLYINCOMPOUND" and len(parts) > 1:
            parsed.only_in_compound = parts[1]
            continue
        if head in ("PFX", "SFX") and len(parts) == 4 and parts[3].isdigit():
            flag = parts[1]
            parsed.cross_product[flag] = parts[2] == "Y"
            table = parsed.prefixes if head == "PFX" else parsed.suffixes
            for _ in range(int(parts[3])):
                rule = lines[index]
                index += 1
                fields = rule.split(None, 4)
                strip = fields[2]
                add = fields[3]
                condition = fields[4].split()[0] if len(fields) > 4 else "."
                continuation = ""
                if "/" in add:
                    add, continuation = add.split("/", 1)
                table[flag].append((strip, add, condition, continuation))
    return AffixRules(
        flag_mode=parsed.flag_mode,
        need_affix=parsed.need_affix,
        forbidden=parsed.forbidden,
        only_in_compound=parsed.only_in_compound,
        prefixes={flag: tuple(rules) for flag, rules in parsed.prefixes.items()},
        suffixes={flag: tuple(rules) for flag, rules in parsed.suffixes.items()},
        cross_product=dict(parsed.cross_product),
    )


def read_dictionary(path: Path, flag_mode: str) -> tuple[tuple[str, frozenset[str]], ...]:
    """Read ``word/flags`` entries, skipping the count line and comments."""
    entries: list[tuple[str, frozenset[str]]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines()[1:]:
        if not line or line.startswith("#"):
            continue
        word, _, rest = line.partition("/")
        word = word.replace("\\/", "/").split("\t")[0]
        entries.append((word, _split_flags(rest.split("\t")[0], flag_mode)))
    return tuple(entries)


def parse_rep_rules(path: Path) -> tuple[tuple[str, str], ...]:
    """Return ``(wrong, right)`` REP pairs in affix-file order.

    Hunspell replaces the first field with the second while correcting, so the
    first field is the commonly misspelled pattern and the second is correct.
    """
    rules: list[tuple[str, str]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.startswith("REP "):
            continue
        parts = line.split()
        if len(parts) < 3 or parts[1].isdigit():
            continue
        rules.append((parts[1], parts[2]))
    return tuple(rules)


def _condition_pattern(condition: str) -> str:
    pattern: list[str] = []
    index = 0
    while index < len(condition):
        char = condition[index]
        if char == ".":
            pattern.append(".")
            index += 1
        elif char == "[":
            end = condition.index("]", index)
            pattern.append(condition[index : end + 1])
            index = end + 1
        else:
            pattern.append(re.escape(char))
            index += 1
    return "".join(pattern)


def _apply_suffix(word: str, rule: AffixRule, flag_mode: str) -> tuple[str, frozenset[str]] | None:
    strip, add, condition, continuation = rule
    if condition != "." and not re.search(_condition_pattern(condition) + "$", word):
        return None
    if strip != "0":
        if not word.endswith(strip):
            return None
        word = word[: -len(strip)]
    return word + ("" if add == "0" else add), _split_flags(continuation, flag_mode)


def _apply_prefix(word: str, rule: AffixRule, flag_mode: str) -> tuple[str, frozenset[str]] | None:
    strip, add, condition, continuation = rule
    if condition != "." and not re.match("^" + _condition_pattern(condition), word):
        return None
    if strip != "0":
        if not word.startswith(strip):
            return None
        word = word[len(strip) :]
    return ("" if add == "0" else add) + word, _split_flags(continuation, flag_mode)


def expand_word_forms(dictionary_path: Path, affix_path: Path) -> set[str]:
    """Return every standalone form the affix rules derive from the dictionary."""
    rules = parse_affix_file(affix_path)
    entries = read_dictionary(dictionary_path, rules.flag_mode)
    forms: set[str] = set()
    for word, flags in entries:
        if rules.standalone_allowed(flags):
            forms.add(word)
        for flag in flags:
            for suffix_rule in rules.suffixes.get(flag, ()):
                result = _apply_suffix(word, suffix_rule, rules.flag_mode)
                if result is None:
                    continue
                suffixed, continuation_flags = result
                if rules.standalone_allowed(continuation_flags):
                    forms.add(suffixed)
            for prefix_rule in rules.prefixes.get(flag, ()):
                result = _apply_prefix(word, prefix_rule, rules.flag_mode)
                if result is None:
                    continue
                prefixed, continuation_flags = result
                if rules.standalone_allowed(continuation_flags):
                    forms.add(prefixed)
                if not rules.cross_product.get(flag, False):
                    continue
                for suffix_flag in flags:
                    if not rules.cross_product.get(suffix_flag, False):
                        continue
                    for suffix_rule in rules.suffixes.get(suffix_flag, ()):
                        combined = _apply_suffix(prefixed, suffix_rule, rules.flag_mode)
                        if combined is None:
                            continue
                        combined_word, combined_flags = combined
                        if rules.standalone_allowed(combined_flags):
                            forms.add(combined_word)
    return forms
