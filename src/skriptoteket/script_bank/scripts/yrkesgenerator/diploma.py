"""Renders the diploma HTML from the diploma.html template."""

from __future__ import annotations

from pathlib import Path
from string import Template

_DIPLOMA_TEMPLATE = Template(Path(__file__).with_name("diploma.html").read_text(encoding="utf-8"))


def build_diploma_html(full_name: str, profile: dict[str, str], reroll_count: int) -> str:
    return _DIPLOMA_TEMPLATE.substitute(
        full_name=full_name,
        career_title=profile["career"].title(),
        salary=profile["salary"],
        motto=profile["motto"],
        side_hustle=profile["side_hustle"],
        aura=profile["aura"],
        weakness=profile["weakness"],
        perk=profile["perk"],
        round_number=reroll_count + 1,
    )
