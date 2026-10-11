"""Yrkesgenerator tool entrypoint: reads the name, selects a fate and builds the outputs."""

from __future__ import annotations

from pathlib import Path

from pdf_helper import save_as_pdf
from skriptoteket_toolkit import get_action_parts, read_inputs

from .diploma import build_diploma_html
from .selection import build_metrics, get_profile_details, hash_to_int, normalize_name

REROLL_SALT = 982_451_653


def _coerce_int(value: object, *, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return default
    return default


def _safe_filename(value: str) -> str:
    cleaned = []
    for ch in value.strip():
        if ch.isalnum() or ch in {"-", "_"}:
            cleaned.append(ch)
        elif ch.isspace():
            cleaned.append("_")
    result = "".join(cleaned).strip("_")
    return result or "diplom"


def run_tool(input_dir: str, output_dir: str) -> dict[str, object]:
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    del input_dir

    inputs = read_inputs()
    action_id, action_input, action_state = get_action_parts()

    full_name = ""
    if isinstance(inputs, dict):
        full_name = str(inputs.get("full_name", "")).strip()
    if not full_name and isinstance(action_input, dict):
        full_name = str(action_input.get("full_name", "")).strip()
    if not full_name and isinstance(action_state, dict):
        full_name = str(action_state.get("full_name", "")).strip()

    if not full_name:
        return {
            "outputs": [
                {"kind": "notice", "level": "warning", "message": "Du glömde skriva ditt namn!"},
                {
                    "kind": "markdown",
                    "markdown": (
                        "## 🤔 Vem är du?\nSkriv in ditt namn i fältet ovan för att få din dom."
                    ),
                },
            ]
        }

    normalized = normalize_name(full_name)
    base_seed = hash_to_int(normalized)
    reroll_count = _coerce_int(action_state.get("reroll_count"), default=0)
    if action_id == "reroll":
        reroll_count += 1
    if action_id == "reset":
        reroll_count = 0

    seed_val = base_seed + reroll_count * REROLL_SALT
    profile, career_details = get_profile_details(seed_val=seed_val)
    metrics = build_metrics(seed_val)

    # Snyggare formatering med emojis och blockquotes
    intro_text = profile["intro"]
    if not intro_text.endswith((".", "!", "?")):
        intro_text += "..."

    md = f"""
## 🔮 Din framtid är avgjord

{intro_text}

# 🧑‍💼 **{profile["career"].title()}**

---

### Profilanalys
* 💸 **Förväntad lön:** {profile["salary"]}
* 🗣️ **Ditt motto:** *"{profile["motto"]}"*
* 🧷 **Side hustle:** {profile["side_hustle"]}
* 🧨 **Svaghet:** {profile["weakness"]}
* 🧲 **Aura:** {profile["aura"]}
* 🧩 **Perk:** {profile["perk"]}

> *Algoritmen har talat. Detta beslut kan ej överklagas.*
"""

    outputs: list[dict[str, object]] = [{"kind": "markdown", "markdown": md}]

    outputs.append(
        {
            "kind": "table",
            "title": "Ödesmätare",
            "columns": [
                {"key": "meter", "label": "Mätare"},
                {"key": "value", "label": "Nivå (0–100)"},
            ],
            "rows": metrics,
        }
    )

    if action_id == "detail":
        outputs.append(
            {
                "kind": "json",
                "title": "Ödesdetaljer",
                "value": {
                    "seed": seed_val,
                    "reroll_count": reroll_count,
                    "career_slot": career_details,
                },
            }
        )

    if action_id == "pdf":
        diploma_html = build_diploma_html(full_name, profile, reroll_count)
        filename = f"yrkesdiplom_{_safe_filename(full_name)}.pdf"
        save_as_pdf(diploma_html, output_dir, filename)
        outputs.insert(
            0,
            {
                "kind": "notice",
                "level": "info",
                "message": f"PDF-diplom skapat: {filename}",
            },
        )

    next_actions = [
        {"action_id": "reroll", "label": "🎲 Ny ödesrunda", "kind": "form", "fields": []},
        {"action_id": "detail", "label": "🔍 Visa detaljer", "kind": "form", "fields": []},
        {"action_id": "pdf", "label": "📄 Skapa diplom (PDF)", "kind": "form", "fields": []},
        {"action_id": "reset", "label": "♻️ Återställ öde", "kind": "form", "fields": []},
    ]

    state = {
        "full_name": full_name,
        "reroll_count": reroll_count,
        "career": profile["career"],
        "seed_base": base_seed,
    }

    return {"outputs": outputs, "next_actions": next_actions, "state": state}
