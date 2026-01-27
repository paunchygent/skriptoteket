from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import cast

from pydantic import JsonValue

from skriptoteket.domain.scripting.ui.contract_v2 import (
    UiJsonOutput,
    UiMarkdownOutput,
    UiNoticeLevel,
    UiNoticeOutput,
    UiTableColumn,
    UiTableOutput,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.calculator import (
    PrepNumbers,
    calculate_numbers,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.formatting import (
    format_decimal,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.models import PrepRequest
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.safety import (
    SafetyResult,
    lookup_safety,
)


@dataclass(frozen=True, slots=True)
class PrepSheet:
    state: dict[str, JsonValue]
    outputs: list[UiNoticeOutput | UiMarkdownOutput | UiTableOutput | UiJsonOutput]


def build_prep_sheet(*, request: PrepRequest) -> PrepSheet:
    numbers = calculate_numbers(request=request)
    warnings = _collect_warnings(numbers=numbers)
    instructions = _build_instructions(numbers=numbers)
    safety = lookup_safety(formula_clean=numbers.formula_clean)

    result_payload = _build_result_payload(
        numbers=numbers,
        instructions=instructions,
        warnings=warnings,
        safety=safety,
        safety_factor=request.safety_factor,
        target_molarity=request.target_molarity,
        stock_molarity=request.stock_molarity,
    )
    markdown = _build_markdown(
        numbers=numbers,
        instructions=instructions,
        warnings=warnings,
        safety_factor=request.safety_factor,
        target_molarity=request.target_molarity,
        stock_molarity=request.stock_molarity,
        solute_purity=request.solute_purity,
    )
    export_html = _build_export_html(markdown=markdown)

    state: dict[str, JsonValue] = {
        "inputs": cast(JsonValue, request.model_dump(mode="json")),
        "result": cast(JsonValue, result_payload),
        "export_html": export_html,
    }
    outputs = _build_outputs(result=result_payload, markdown=markdown, safety=safety)
    return PrepSheet(state=state, outputs=outputs)


def _collect_warnings(*, numbers: PrepNumbers) -> list[str]:
    warnings: list[str] = []
    if numbers.mass_g is not None and numbers.mass_g < Decimal("0.01"):
        warnings.append(
            "Beräknad massa är < 0,01 g. Gör en stocklösning först för bättre precision."
        )
    return warnings


def _build_instructions(*, numbers: PrepNumbers) -> list[str]:
    if numbers.source_type == "solid":
        if numbers.mass_g is None:
            return []
        mass_g = format_decimal(numbers.mass_g, places=2)
        approx_dissolve_ml = format_decimal(numbers.total_volume_ml * Decimal("0.7"), places=0)
        total_volume_ml = format_decimal(numbers.total_volume_ml, places=1)
        return [
            f"Väg upp {mass_g} g av {numbers.formula_clean}.",
            f"Lös i ca {approx_dissolve_ml} mL destillerat vatten.",
            f"Späd till {total_volume_ml} mL totalt.",
        ]
    if numbers.stock_volume_ml is None or numbers.diluent_volume_ml is None:
        return []
    return [
        f"Mät upp {format_decimal(numbers.stock_volume_ml, places=1)} mL av stocklösningen.",
        f"Tillsätt {format_decimal(numbers.diluent_volume_ml, places=1)} mL vatten.",
        "Blanda väl.",
    ]


def _build_result_payload(
    *,
    numbers: PrepNumbers,
    instructions: list[str],
    warnings: list[str],
    safety: SafetyResult,
    safety_factor: Decimal,
    target_molarity: Decimal,
    stock_molarity: Decimal | None,
) -> dict[str, JsonValue]:
    result: dict[str, JsonValue] = {
        "formula_clean": numbers.formula_clean,
        "molar_mass_g_mol": format_decimal(numbers.molar_mass_g_mol, places=3),
        "total_groups": numbers.total_groups,
        "total_volume_ml": format_decimal(numbers.total_volume_ml, places=1),
        "moles_required": format_decimal(numbers.moles_required, places=4),
        "source_type": numbers.source_type,
        "instructions": list(instructions),
        "warnings": list(warnings),
        "safety_factor": format_decimal(safety_factor * Decimal("100"), places=0),
        "target_molarity": format_decimal(target_molarity, places=4),
    }

    if numbers.mass_g is not None:
        result["mass_g"] = format_decimal(numbers.mass_g, places=2)
    if numbers.stock_volume_ml is not None and numbers.diluent_volume_ml is not None:
        result["stock_molarity"] = format_decimal(stock_molarity or Decimal("0"), places=4)
        result["stock_volume_ml"] = format_decimal(numbers.stock_volume_ml, places=1)
        result["diluent_volume_ml"] = format_decimal(numbers.diluent_volume_ml, places=1)

    result["safety"] = _build_safety_payload(safety=safety)
    return result


def _build_safety_payload(*, safety: SafetyResult) -> dict[str, JsonValue]:
    if safety.entry is None:
        return {
            "level": safety.level,
        }
    return {
        "level": safety.level,
        "display_name": safety.entry.display_name,
        "ppe": list(safety.entry.ppe),
        "hazard_codes": list(safety.entry.hazard_codes),
        "disposal": safety.entry.disposal,
        "notes": list(safety.entry.notes),
    }


def _build_markdown(
    *,
    numbers: PrepNumbers,
    instructions: list[str],
    warnings: list[str],
    safety_factor: Decimal,
    target_molarity: Decimal,
    stock_molarity: Decimal | None,
    solute_purity: Decimal,
) -> str:
    header = (
        "# Reagensberedning" if numbers.source_type == "solid" else "# Reagensberedning (spädning)"
    )
    safety_pct = format_decimal(safety_factor * Decimal("100"), places=0)
    total_volume_ml = format_decimal(numbers.total_volume_ml, places=1)

    lines = [
        header,
        "",
        f"- Grupper: **{numbers.total_groups}**",
        f"- Totalvolym: **{total_volume_ml} mL** (inkl. {safety_pct}% marginal)",
    ]

    if numbers.source_type == "solid":
        lines.extend(
            [
                f"- Ämne: **{numbers.formula_clean}**",
                f"- Molar massa: **{format_decimal(numbers.molar_mass_g_mol, places=3)} g/mol**",
                f"- Mängd substans: **{format_decimal(numbers.moles_required, places=4)} mol**",
            ]
        )
        if numbers.mass_g is not None:
            purity_pct = format_decimal(solute_purity * Decimal("100"), places=0)
            mass_g = format_decimal(numbers.mass_g, places=2)
            lines.append(f"- Massa (justerat för renhet {purity_pct}%): **{mass_g} g**")
    else:
        stock_molarity_display = format_decimal(stock_molarity or Decimal("0"), places=4)
        lines.extend(
            [
                f"- Målmolaritet: **{format_decimal(target_molarity, places=4)} M**",
                f"- Stockmolaritet: **{stock_molarity_display} M**",
            ]
        )

    lines.extend(["", "## Steg"])
    for idx, instruction in enumerate(instructions, start=1):
        lines.append(f"{idx}. {instruction}")

    if warnings:
        lines.extend(["", "## Varningar", *[f"- {w}" for w in warnings]])

    return "\n".join(lines).rstrip() + "\n"


def _build_export_html(*, markdown: str) -> str:
    safe_lines: list[str] = []
    for line in markdown.splitlines():
        safe_lines.append(line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    body = "<br/>".join(safe_lines)
    return (
        "<!doctype html><html><head><meta charset='utf-8'/>"
        "<style>body{font-family:system-ui, -apple-system, Segoe UI, Roboto, sans-serif;}"
        "h1,h2{margin:0 0 8px 0;} .box{border:1px solid #111;padding:16px;}</style>"
        "</head><body><div class='box'>"
        f"{body}"
        "</div></body></html>"
    )


def _build_outputs(
    *,
    result: dict[str, JsonValue],
    markdown: str,
    safety: SafetyResult,
) -> list[UiNoticeOutput | UiMarkdownOutput | UiTableOutput | UiJsonOutput]:
    outputs: list[UiNoticeOutput | UiMarkdownOutput | UiTableOutput | UiJsonOutput] = []
    outputs.extend(_build_safety_notices(safety=safety))
    outputs.append(UiMarkdownOutput(markdown=markdown))
    outputs.append(_build_summary_table(result=result))
    safety_table = _build_safety_table(safety=safety)
    if safety_table is not None:
        outputs.append(safety_table)
    outputs.append(UiJsonOutput(title="Prep-resultat (JSON)", value=cast(JsonValue, result)))
    return outputs


def _build_safety_notices(*, safety: SafetyResult) -> list[UiNoticeOutput]:
    notices: list[UiNoticeOutput] = []
    if safety.level == "unknown":
        notices.append(
            UiNoticeOutput(
                level=UiNoticeLevel.WARNING,
                message="Säkerhet: okänt ämne. Konsultera SDS innan användning.",
            )
        )
    notices.append(
        UiNoticeOutput(
            level=UiNoticeLevel.INFO,
            message="Kom ihåg: kontrollera SDS och lokala rutiner innan beredning.",
        )
    )
    return notices


def _build_summary_table(*, result: dict[str, JsonValue]) -> UiTableOutput:
    columns = [
        UiTableColumn(key="key", label="Nyckel"),
        UiTableColumn(key="value", label="Värde"),
    ]
    rows: list[dict[str, str]] = [
        {"key": "Grupper", "value": str(result.get("total_groups", ""))},
        {"key": "Totalvolym", "value": f"{result.get('total_volume_ml', '')} mL"},
        {"key": "Formel", "value": str(result.get("formula_clean", ""))},
        {"key": "Molar massa", "value": f"{result.get('molar_mass_g_mol', '')} g/mol"},
    ]
    if "mass_g" in result:
        rows.append({"key": "Massa", "value": f"{result.get('mass_g', '')} g"})
    if "stock_volume_ml" in result:
        rows.append({"key": "Stockvolym", "value": f"{result.get('stock_volume_ml', '')} mL"})
        rows.append(
            {"key": "Spädningsvatten", "value": f"{result.get('diluent_volume_ml', '')} mL"}
        )
    return UiTableOutput(title="Sammanfattning", columns=columns, rows=rows)


def _build_safety_table(*, safety: SafetyResult) -> UiTableOutput | None:
    if safety.entry is None:
        return None

    columns = [
        UiTableColumn(key="key", label="Nyckel"),
        UiTableColumn(key="value", label="Värde"),
    ]
    rows: list[dict[str, str]] = [{"key": "Ämne", "value": safety.entry.display_name}]
    if safety.entry.ppe:
        rows.append({"key": "PPE", "value": ", ".join(safety.entry.ppe)})
    if safety.entry.hazard_codes:
        rows.append({"key": "H-koder", "value": ", ".join(safety.entry.hazard_codes)})
    if safety.entry.disposal:
        rows.append({"key": "Avfall", "value": safety.entry.disposal})
    return UiTableOutput(title="Säkerhet (kuraterad)", columns=columns, rows=rows)
