from __future__ import annotations

import hashlib
import json
import os
import random
from pathlib import Path
from typing import Any, Dict, List

from pdf_helper import save_as_pdf

# ──────────────────────────────────────────────────────────────────────────────
# SKRIPTOTEKET_INPUTS
# ──────────────────────────────────────────────────────────────────────────────
SKRIPTOTEKET_INPUTS = [
    {
        "name": "full_name",
        "label": "Skriv in ditt för- och efternamn",
        "kind": "string",
    }
]
SKRIPTOTEKET_INPUT_SCHEMA = SKRIPTOTEKET_INPUTS

# ──────────────────────────────────────────────────────────────────────────────
# DATA: Yrken, Platser, Löner, Motton
# ──────────────────────────────────────────────────────────────────────────────

INTRO_PHRASES = [
    "Du kan se fram emot en karriär som",
    "Din framtid pekar mot att bli",
    "Det verkar som att du passar som",
    "Spåkulan säger att du blir",
    "Dina föräldrar kommer 'älska' att du blir",
    "Grattis? Det ser ut som att du ska bli",
    "Ditt bidrag till samhället blir som",
    "Det kunde varit värre, men du blir",
    "Efter diverse snedsteg landar du som",
    "Det står skrivet i stjärnorna (tyvärr): du blir",
    "Algoritmen har, utan nåd, valt att du blir",
    "Ditt sanna, mörka kall är att vara",
    "Universum vill att du blir",
    "Din karma har kommunicerat: du blir",
    "Verkligheten försökte varna dig, men du blir",
    "Sanningen gör ont: du blir",
    "Ryktena stämmer, du blir",
]

CAREERS: List[Dict[str, Any]] = [
    {"title": "lärare"},
    {"title": "ingenjör"},
    {"title": "programmerare"},
    {"title": "journalist"},
    {"title": "sjuksköterska"},
    {"title": "läkare"},
    {"title": "jurist"},
    {"title": "arkitekt"},
    {"title": "kock"},
    {"title": "psykolog"},
    {"title": "polis"},
    {"title": "forskare"},
    {"title": "bibliotekarie"},
    {"title": "projektledare"},
    {"title": "grafisk designer"},
    {"title": "elektriker"},
    {"title": "fysioterapeut"},
    {"title": "pilot"},
    {"title": "musiker"},
    {"title": "entreprenör"},
    {"title": "pokerspelare"},
    {"title": "gamer"},
    {"title": "influencer"},
    {"title": "drömtydare"},
    {"title": "becknare"},
    {"title": "målvakt (ekonomisk brottslighet)"},
    {"title": "svarttaxichaufför"},
    {"title": "cykeltjuv"},
    {"title": "hälare"},
    {"title": "penningtvättare"},
    {"title": "kryptobror"},
    {"title": "livscoach"},
    {"title": "LinkedIn-inspiratör"},
    {"title": "poet"},
    {"title": "reality-såpadeltagare"},
    {"title": "OnlyFans-manager"},
    {"title": "poddare"},
    {"title": "flashback-detektiv"},
    {"title": "discord-moderator"},
    {"title": "telefonförsäljare"},
    {"title": "parkeringsvakt"},
    {"title": "biljettkontrollant"},
    {"title": "ex-realitystjärna"},
    {"title": "statist"},
    {"title": "karaokevärd"},
    {"title": "coverbandsbasist"},
    {"title": "lokalkändis"},
    {"title": "inkassohandläggare"},
    {"title": "begravningsentreprenör"},
    {"title": "skadedjursbekämpare"},
    {"title": "tatuerare"},
    {"title": "lastbilschaufför"},
    {"title": "bartender"},
    {"title": "arbetsförmedlare"},
    {"title": "väktare"},
    {"title": "sotare"},
    {"title": "Foodora-bud"},
    {"title": "slaktare"},
    {"title": "aktuarie"},
    {"title": "fritidspolitiker"},
    {"title": "personlig assistent"},
    {"title": "låssmed"},
    {"title": "sommelier"},
    {"title": "badvakt"},
    {"title": "ordningsvakt"},
    {"title": "kyrkogårdsvaktmästare"},
    {"title": "hundfrisör"},
    {"title": "osteopat"},
    {"title": "agil coach utan team"},
    {"title": "powerpoint-krigare"},
    {"title": "mellanchef (utan personalansvar)"},
    {"title": "professionell mötesdeltagare"},
    {"title": "wellness-konsult"},
    {"title": "konstnärlig ledare för en tom lokal"},
    {"title": "mikro-influencer (12 följare)"},
    {"title": "troll i kommentarsfält"},
    {"title": "dropshipping-guru"},
    {"title": "osignad Soundcloud-rappare"},
    {"title": "svartklubbsarrangör"},
    {"title": "professionell rättshaverist"},
    {"title": "pantentreprenör"},
    {"title": "mänsklig försökskanin"},
    {"title": "gubbe i keps"},
]

SALARIES = [
    "En varm handslag",
    "3 miljoner (i monopolpengar)",
    "Dåligt samvete",
    "Exponering",
    "Provision på sålda strumpor",
    "Gratis kaffe (ibland)",
    "En halv bitcoin (från 2011)",
    "Rikskuponger",
    "Skuldsanering",
    "En klapp på axeln",
    "Det du hittar i fickorna",
    "En växande CSN-skuld som aldrig försvinner",
    "Pantkvitton och gamla trisslotter",
    "Bara SMS-lån",
    "En påse gifflar och ett 'bra jobbat'",
    "Fria bananer (men bara de bruna)",
    "Betalt i 'erfarenhet' (som ingen vill ha)",
    "En faktura från Klarna",
    "Tre dagars karensavdrag",
    "Sveda och värk",
    "Aktieoptioner som (kanske) blir värda något 2035",
    "Du får behålla dricksen (om chefen inte ser)",
    "Förmånen att få jobba med 'världens bästa team'",
    "Dina föräldrars pensionssparpengar",
    "Endast representationsluncher på företagskortet",
    "Svartbetalning via Swish",
    "Du betalar faktiskt för att få jobba här",
    "En hög lön, om man bortser från att du jobbar 90 timmar i veckan",
    "Allt du lyckas stjäla från kontorsförrådet",
]

MOTTOS = [
    "Det löser sig.",
    "Skyll på praktikanten.",
    "Fake it til you make it.",
    "Det var bättre förr.",
    "Minsta möjliga motstånd.",
    "Cash is king.",
    "Lev, skratta, gråt.",
    "Det är inte mitt fel.",
    "Snart är det helg.",
    "Våga vägra jobba.",
    "Allt är en social konstruktion.",
    "Det var inte jag.",
    "Vi tar det på måndag (aldrig).",
    "Gör om, gör fel.",
    "Det är tanken som räknas (tyvärr).",
    "Det kunde varit värre, jag kunde varit nykter.",
    "Bara döda fiskar flyter med strömmen.",
    "Bit ihop och lida.",
    "Det finns inga problem, bara dyra lösningar.",
    "Vet du inte vem jag är?",
    "Alla andra är bara NPCs i mitt liv.",
    "Regler är till för de fattiga.",
    "Jag är inte arrogant, jag är bara bättre.",
    "Förlåt att jag finns.",
    "Vi sätter en lapp i tvättstugan.",
    "Jag håller med den som pratade sist.",
    "Den som spar han har (andras pengar).",
    "Varför betala när man kan springa?",
    "Det är bara olagligt om man åker fast.",
    "Vänner är till för att utnyttjas.",
    "Det var inte mitt fel, det var systemet.",
]

DEFAULT_TOTAL_SLOTS = 10_000
REROLL_SALT = 982_451_653

# ──────────────────────────────────────────────────────────────────────────────
# LOGIK
# ──────────────────────────────────────────────────────────────────────────────


def _normalize_name(name: str) -> str:
    return " ".join(name.strip().split()).casefold()


def _hash_to_int(text: str) -> int:
    """Stabil hash → heltal."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return int.from_bytes(digest, "big")


def _build_weighted_intervals(
    options: List[Dict[str, Any]], total_slots: int
) -> List[Dict[str, Any]]:
    """Bygger intervall för yrkesvalet."""
    if total_slots <= 0:
        raise ValueError("total_slots > 0")

    # Filtrera och extrahera
    valid_opts = [o for o in options if str(o.get("title", "")).strip()]
    if not valid_opts:
        raise ValueError("Inga giltiga yrken.")

    titles = [str(o["title"]).strip() for o in valid_opts]
    weights = [int(o.get("weight", 1)) for o in valid_opts]

    total_weight = sum(weights)
    base_sizes = [(w * total_slots) // total_weight for w in weights]
    remainders = [(w * total_slots) % total_weight for w in weights]

    # Fördela rester
    leftover = total_slots - sum(base_sizes)
    if leftover > 0:
        order = sorted(range(len(base_sizes)), key=lambda i: (-remainders[i], i))
        for i in order[:leftover]:
            base_sizes[i] += 1

    intervals = []
    start = 0
    for title, size in zip(titles, base_sizes):
        intervals.append({"title": title, "start": start, "end": start + size})
        start += size

    return intervals


EXTRA_PERKS = [
    "Kan snacka sig ur nästan vad som helst (tyvärr)",
    "Läser rummet fel, men äger det",
    "Har ett alibi som nästan håller",
    "Skapar drama utan att ens försöka",
    "Har en plan som inte ens du förstår",
    "Gör dåliga idéer oförskämt övertygande",
    "Hittar gratis fika som om det vore ett kall",
    "Lyckas alltid landa mjukt trots fallskärmförbud",
    "Skapar en myt om sig själv i realtid",
]

WEAKNESSES = [
    'Dålig impulskontroll när någon säger "gör det bara"',
    "Allergisk mot deadlines men beroende av panik",
    "Försvinner när det blir ansvar",
    "Överskattar sin egen charm (alltid)",
    "Har alltid fel kalendervecka",
    "Känner sig personligt attackerad av logik",
    "Svaghet för dåliga idéer som låter smarta",
    "Blir kränkt av konsekvenser",
]

SIDE_HUSTLES = [
    "Driver en podd ingen bett om",
    "Skapar memes som bara du gillar",
    "Säljer drömmar på Blocket",
    "Gör listor över listor över listor",
    "Organiserar hemliga Spotify-listor för dramatik",
    "Deltidskonstnär i kreativ panik",
    "Instagram-analytiker åt sig själv",
]

AURAS = [
    "fuktig karisma",
    "vild oklarhet",
    "stökig trygghet",
    "obehaglig pondus",
    "lugnt kaos",
    "oskyldigt hot",
    "professionell nihilism",
    "kaos med kalender",
    "starkt tvivel",
    "snäll tyranni",
]

CAREER_PREFIXES = [
    "självutnämnd",
    "certifierad",
    "obekväm",
    "överarbetad",
    "halvtids",
    "mytisk",
    "oetablerad",
    "tveksamt",
    "oönskad",
    "bortglömd",
]


def _read_json_env(name: str, *, default: object) -> object:
    raw = os.environ.get(name, "")
    if not raw.strip():
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default


def _read_action_payload(input_dir: Path) -> dict[str, Any] | None:
    manifest = _read_json_env("SKRIPTOTEKET_INPUT_MANIFEST", default={"files": []})
    if isinstance(manifest, dict):
        files = manifest.get("files", [])
        if isinstance(files, list):
            for item in files:
                if not isinstance(item, dict):
                    continue
                if item.get("name") != "action.json":
                    continue
                raw_path = item.get("path")
                if not isinstance(raw_path, str):
                    continue
                path = Path(raw_path)
                if path.exists():
                    try:
                        return json.loads(path.read_text(encoding="utf-8"))
                    except json.JSONDecodeError:
                        return None

    action_path = input_dir / "action.json"
    if action_path.exists():
        try:
            return json.loads(action_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
    return None


def _normalize_action_payload(payload: dict[str, Any] | None) -> tuple[str | None, dict, dict]:
    if not payload:
        return None, {}, {}
    action_id = payload.get("action_id")
    if isinstance(action_id, str):
        action_id = action_id.strip() or None
    else:
        action_id = None
    action_input = payload.get("input") if isinstance(payload.get("input"), dict) else {}
    action_state = payload.get("state") if isinstance(payload.get("state"), dict) else {}
    return action_id, action_input, action_state


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


def _get_profile_details(*, seed_val: int) -> tuple[Dict[str, str], dict[str, int]]:
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


def _build_metrics(seed_val: int) -> list[dict[str, object]]:
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


def _build_diploma_html(full_name: str, profile: dict[str, str], reroll_count: int) -> str:
    career_title = profile["career"].title()
    return f"""
<!doctype html>
<html lang="sv">
<head>
  <meta charset="utf-8">
  <style>
    @page {{
      size: A4;
      margin: 0;
    }}
    * {{
      box-sizing: border-box;
    }}
    body {{
      font-family: "Noto Serif", "DejaVu Serif", serif;
      background: #fffaf2;
      color: #111;
      margin: 0;
    }}
    .page {{
      width: 210mm;
      height: 297mm;
      padding: 18mm;
      background: #f0ebe2;
    }}
    .sheet {{
      width: 100%;
      height: 100%;
      background: #fffaf2;
      border: 6px double #111;
      padding: 20mm 18mm 16mm 18mm;
    }}
    .top {{
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 18px;
    }}
    .seal-cell {{
      width: 110px;
      vertical-align: top;
    }}
    .seal {{
      width: 96px;
      height: 96px;
      border-radius: 999px;
      border: 3px solid #111;
      text-align: center;
      margin-right: 12px;
    }}
    .seal-title {{
      margin-top: 22px;
      font-size: 16px;
      font-weight: 700;
      letter-spacing: 2px;
    }}
    .seal-sub {{
      font-size: 10px;
      letter-spacing: 1px;
      text-transform: uppercase;
    }}
    .meta {{
      font-family: "Noto Sans", "DejaVu Sans", sans-serif;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 1.2px;
      color: #333;
    }}
    .title {{
      font-size: 34px;
      margin: 8px 0 4px 0;
    }}
    .name {{
      font-size: 26px;
      font-weight: 700;
      margin: 0 0 6px 0;
    }}
    .career {{
      font-size: 20px;
      margin: 0 0 18px 0;
    }}
    .rule {{
      height: 2px;
      background: #111;
      margin: 14px 0 18px 0;
    }}
    .details {{
      width: 100%;
      border-collapse: collapse;
      font-family: "Noto Sans", "DejaVu Sans", sans-serif;
      font-size: 12px;
    }}
    .details td {{
      padding: 6px 8px;
      border-bottom: 1px solid #ddd;
    }}
    .details td.label {{
      width: 32%;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      font-size: 10px;
      color: #333;
    }}
    .footer {{
      margin-top: 18px;
      font-size: 11px;
      color: #333;
      text-transform: uppercase;
      letter-spacing: 1px;
    }}
  </style>
</head>
<body>
  <div class="page">
    <div class="sheet">
    <table class="top">
      <tr>
        <td class="seal-cell">
          <div class="seal">
            <div class="seal-title">YR</div>
            <div class="seal-sub">DIPLOM</div>
          </div>
        </td>
        <td>
          <div class="meta">Officiellt ödesintyg</div>
          <div class="title">Yrkesdiplom</div>
          <div class="name">{full_name}</div>
          <div class="career">{career_title}</div>
        </td>
      </tr>
    </table>

    <div class="rule"></div>
    <table class="details">
      <tr><td class="label">Förväntad lön</td><td>{profile["salary"]}</td></tr>
      <tr><td class="label">Motto</td><td>{profile["motto"]}</td></tr>
      <tr><td class="label">Side hustle</td><td>{profile["side_hustle"]}</td></tr>
      <tr><td class="label">Aura</td><td>{profile["aura"]}</td></tr>
      <tr><td class="label">Svaghet</td><td>{profile["weakness"]}</td></tr>
      <tr><td class="label">Perk</td><td>{profile["perk"]}</td></tr>
    </table>

    <div class="footer">Ödesrunda #{reroll_count + 1} • Detta beslut kan ej överklagas</div>
    </div>
  </div>
</body>
</html>
"""


def run_tool(input_dir: str, output_dir: str) -> dict:
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    inputs = _read_json_env("SKRIPTOTEKET_INPUTS", default={})
    action_payload = _read_action_payload(Path(input_dir))
    action_id, action_input, action_state = _normalize_action_payload(action_payload)

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

    normalized = _normalize_name(full_name)
    base_seed = _hash_to_int(normalized)
    reroll_count = _coerce_int(action_state.get("reroll_count"), default=0)
    if action_id == "reroll":
        reroll_count += 1
    if action_id == "reset":
        reroll_count = 0

    seed_val = base_seed + reroll_count * REROLL_SALT
    profile, career_details = _get_profile_details(seed_val=seed_val)
    metrics = _build_metrics(seed_val)

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
        diploma_html = _build_diploma_html(full_name, profile, reroll_count)
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
