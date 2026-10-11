"""Deterministic career, profile and metric selection for the yrkesgenerator."""

from __future__ import annotations

import hashlib
import random

from .careers import (
    AURAS,
    CAREER_PREFIXES,
    CAREERS,
    EXTRA_PERKS,
    INTRO_PHRASES,
    MOTTOS,
    SALARIES,
    SIDE_HUSTLES,
    WEAKNESSES,
    Career,
    WeightedInterval,
)

DEFAULT_TOTAL_SLOTS = 10_000


def normalize_name(name: str) -> str:
    return " ".join(name.strip().split()).casefold()


def hash_to_int(text: str) -> int:
    """Stabil hash → heltal."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return int.from_bytes(digest, "big")


def _build_weighted_intervals(options: list[Career], total_slots: int) -> list[WeightedInterval]:
    """Bygger intervall för yrkesvalet."""
    if total_slots <= 0:
        raise ValueError("total_slots > 0")

    # Filtrera och extrahera
    valid_opts = [o for o in options if o["title"].strip()]
    if not valid_opts:
        raise ValueError("Inga giltiga yrken.")

    titles = [o["title"].strip() for o in valid_opts]
    weights = [o.get("weight", 1) for o in valid_opts]

    total_weight = sum(weights)
    base_sizes = [(w * total_slots) // total_weight for w in weights]
    remainders = [(w * total_slots) % total_weight for w in weights]

    # Fördela rester
    leftover = total_slots - sum(base_sizes)
    if leftover > 0:
        order = sorted(range(len(base_sizes)), key=lambda i: (-remainders[i], i))
        for i in order[:leftover]:
            base_sizes[i] += 1

    intervals: list[WeightedInterval] = []
    start = 0
    for title, size in zip(titles, base_sizes):
        intervals.append({"title": title, "start": start, "end": start + size})
        start += size

    return intervals


def _select_career(seed_val: int) -> tuple[str, dict[str, int]]:
    total_slots = max(DEFAULT_TOTAL_SLOTS, len(CAREERS))
    intervals = _build_weighted_intervals(CAREERS, total_slots)
    slot = seed_val % intervals[-1]["end"]

    for idx, iv in enumerate(intervals):
        if iv["start"] <= slot < iv["end"]:
            details = {
                "slot": slot,
                "start": iv["start"],
                "end": iv["end"],
                "index": idx,
                "total_slots": intervals[-1]["end"],
            }
            return iv["title"], details

    details = {
        "slot": slot,
        "start": intervals[-1]["start"],
        "end": intervals[-1]["end"],
        "index": len(intervals) - 1,
        "total_slots": intervals[-1]["end"],
    }
    return intervals[-1]["title"], details


def _decorate_career(career: str, rng: random.Random) -> str:
    title = career
    if rng.random() < 0.6:
        prefix = rng.choice(CAREER_PREFIXES)
        title = f"{prefix} {title}"
    return title


def get_profile_details(*, seed_val: int) -> tuple[dict[str, str], dict[str, int]]:
    """Genererar en fullständig profil baserat på seed."""

    rng = random.Random(seed_val)
    career_raw, career_details = _select_career(seed_val)
    career = _decorate_career(career_raw, rng)

    # 2. Hämta Flavor-text (Deterministiskt slumpat via seed)
    # Vi använder modulo med olika primtal eller bit-shifts för att undvika
    # att samma yrke alltid får samma plats.
    salary = rng.choice(SALARIES)
    motto = rng.choice(MOTTOS)
    intro = rng.choice(INTRO_PHRASES)
    perk = rng.choice(EXTRA_PERKS)
    weakness = rng.choice(WEAKNESSES)
    side_hustle = rng.choice(SIDE_HUSTLES)
    aura = rng.choice(AURAS)

    return {
        "career": career,
        "salary": salary,
        "motto": motto,
        "intro": intro,
        "perk": perk,
        "weakness": weakness,
        "side_hustle": side_hustle,
        "aura": aura,
    }, career_details


def build_metrics(seed_val: int) -> list[dict[str, object]]:
    chaos = (seed_val // 97) % 101
    karma = (seed_val // 131) % 101
    charm = (seed_val // 173) % 101
    stamina = (seed_val // 199) % 101
    return [
        {"meter": "Kaos", "value": chaos},
        {"meter": "Karma", "value": karma},
        {"meter": "Karisma", "value": charm},
        {"meter": "Uthållighet", "value": stamina},
    ]
