from __future__ import annotations

import html
from datetime import date

from skriptoteket.application.curated_apps.reagent_prep_chef import (
    ReagentPrepChefPrepSheet,
    ReagentPrepChefRiskAssessmentDraft,
)


def build_export_html(*, sheet: ReagentPrepChefPrepSheet) -> str:
    title = "Reagensberedning"
    if sheet.chemistry.formula_clean:
        title = f"Reagensberedning: {sheet.chemistry.formula_clean}"

    def esc(value: str) -> str:
        return html.escape(value, quote=True)

    warning_html = ""
    if sheet.warnings:
        warning_html = (
            "<section class='section warning'>"
            "<h2>Varningar</h2>"
            "<ul>" + "".join(f"<li>{esc(item)}</li>" for item in sheet.warnings) + "</ul>"
            "</section>"
        )

    safety = sheet.safety
    safety_disclaimer = (
        "<p>Den här appen ger endast råd för ämnen i listan. "
        "Om ämnet saknas: konsultera alltid SDS och lokala rutiner.</p>"
    )
    if safety.level == "unknown":
        safety_html = (
            "<section class='section safety'>"
            "<h2>Säkerhet</h2>"
            f"{safety_disclaimer}"
            f"<p class='warn'>{esc(safety.message or 'Konsultera SDS innan användning.')}</p>"
            "</section>"
        )
    else:
        safety_rows: list[tuple[str, str]] = []
        if safety.display_name:
            safety_rows.append(("Ämne", safety.display_name))
        if safety.ppe:
            safety_rows.append(("PPE", ", ".join(safety.ppe)))
        if safety.hazard_codes:
            safety_rows.append(("H-koder", ", ".join(safety.hazard_codes)))
        if safety.disposal:
            safety_rows.append(("Avfall", safety.disposal))

        safety_table = ""
        if safety_rows:
            safety_table = (
                "<table class='kv'>"
                + "".join(f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>" for k, v in safety_rows)
                + "</table>"
            )

        safety_notes = ""
        if safety.notes:
            safety_notes = "<ul>" + "".join(f"<li>{esc(n)}</li>" for n in safety.notes) + "</ul>"

        safety_html = (
            "<section class='section safety'>"
            "<h2>Säkerhet</h2>"
            f"{safety_disclaimer}"
            f"{safety_table}"
            f"{safety_notes}"
            "</section>"
        )

    instructions_html = (
        "<ol class='steps'>"
        + "".join(f"<li>{esc(step)}</li>" for step in sheet.instructions)
        + "</ol>"
    )

    summary_rows = [
        ("Grupper", str(sheet.logistics.total_groups)),
        ("Totalvolym", f"{sheet.logistics.total_volume_ml} ml"),
        ("Marginal", f"{sheet.logistics.safety_factor_pct}%"),
        ("Formel", sheet.chemistry.formula_clean),
        ("Molmassa", f"{sheet.chemistry.molar_mass_g_mol} g/mol"),
        ("Mängd substans", f"{sheet.chemistry.moles_required} mol"),
    ]
    if sheet.chemistry.mass_g:
        summary_rows.append(("Massa", f"{sheet.chemistry.mass_g} g"))
    if sheet.chemistry.stock_volume_ml and sheet.chemistry.diluent_volume_ml:
        summary_rows.append(("Stockvolym", f"{sheet.chemistry.stock_volume_ml} ml"))
        summary_rows.append(("Spädningsvatten", f"{sheet.chemistry.diluent_volume_ml} ml"))

    summary_table = (
        "<table class='kv'>"
        + "".join(f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>" for k, v in summary_rows)
        + "</table>"
    )

    return (
        "<!doctype html>"
        "<html lang='sv'>"
        "<head>"
        "<meta charset='utf-8'/>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'/>"
        "<style>"
        "body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;font-size:12px;}"
        "h1{font-size:20px;margin:0 0 12px 0;}"
        "h2{font-size:14px;margin:16px 0 8px 0;}"
        ".section{border:1px solid #111;padding:12px;margin:12px 0;}"
        ".kv{width:100%;border-collapse:collapse;}"
        ".kv th{width:35%;text-align:left;border-top:1px solid #111;padding:6px 8px;"
        "vertical-align:top;}"
        ".kv td{border-top:1px solid #111;padding:6px 8px;}"
        ".steps{margin:0;padding-left:18px;}"
        ".warning{border-color:#7a003c;}"
        ".warn{color:#7a003c;}"
        "</style>"
        "</head>"
        "<body>"
        f"<h1>{esc(title)}</h1>"
        "<section class='section'>"
        "<h2>Sammanfattning</h2>"
        f"{summary_table}"
        "</section>"
        "<section class='section'>"
        "<h2>Steg</h2>"
        f"{instructions_html}"
        "</section>"
        f"{warning_html}"
        f"{safety_html}"
        "</body>"
        "</html>"
    )


def build_risk_export_html(
    *,
    draft: ReagentPrepChefRiskAssessmentDraft,
    warnings: list[str],
) -> str:
    title = "Riskbedömning"
    if draft.sheet.chemistry.formula_clean:
        title = f"Riskbedömning: {draft.sheet.chemistry.formula_clean}"

    def esc(value: str) -> str:
        return html.escape(value, quote=True)

    def fmt_date(value: date | None) -> str:
        return value.isoformat() if value else "—"

    context = draft.context
    context_rows = [
        ("Omfattning", context.scope if context else None),
        ("Plats", context.location if context else None),
        ("Deltagare", context.participants if context else None),
        ("Ansvarig/Approver", context.approver if context else None),
        ("Datum", fmt_date(context.assessment_date) if context else "—"),
        ("Nästa översyn", fmt_date(context.next_review_date) if context else "—"),
        ("Lokala rutiner", context.local_routines if context else None),
    ]
    context_table = (
        "<table class='kv'>"
        + "".join(
            f"<tr><th>{esc(label)}</th><td>{esc(value or '—')}</td></tr>"
            for label, value in context_rows
        )
        + "</table>"
    )

    prep_rows = [
        ("Formel", draft.sheet.chemistry.formula_clean),
        ("Målmolaritet", f"{draft.sheet.chemistry.target_molarity} M"),
        ("Totalvolym", f"{draft.sheet.logistics.total_volume_ml} ml"),
        ("Grupper", str(draft.sheet.logistics.total_groups)),
    ]
    prep_table = (
        "<table class='kv'>"
        + "".join(f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>" for k, v in prep_rows)
        + "</table>"
    )

    clp = draft.clp
    clp_rows = [
        ("H-koder", ", ".join(clp.hazard_codes) if clp.hazard_codes else "—"),
        ("Piktogram", ", ".join(clp.pictograms) if clp.pictograms else "—"),
        ("Signalord", clp.signal_word or "—"),
        ("Noteringar", ", ".join(clp.notes) if clp.notes else "—"),
    ]
    clp_table = (
        "<table class='kv'>"
        + "".join(f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>" for k, v in clp_rows)
        + "</table>"
    )

    heuristics = draft.heuristics
    heuristics_rows = [
        ("Inkompatibilitet", ", ".join(heuristics.incompatibilities) or "—"),
        ("Exotermitet", heuristics.exothermicity or "—"),
        ("Reaktionsnoteringar", ", ".join(heuristics.reaction_notes) or "—"),
    ]
    heuristics_table = (
        "<table class='kv'>"
        + "".join(f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>" for k, v in heuristics_rows)
        + "</table>"
    )

    warnings_html = ""
    if warnings:
        warnings_html = (
            "<section class='section warning'>"
            "<h2>Varningar</h2>"
            "<ul>" + "".join(f"<li>{esc(item)}</li>" for item in warnings) + "</ul>"
            "</section>"
        )

    risks_rows = ""
    for risk in draft.risks:
        measures_html = "<ul>" + "".join(f"<li>{esc(m)}</li>" for m in risk.measures) + "</ul>"
        risks_rows += (
            "<tr>"
            f"<td>{esc(risk.title)}</td>"
            f"<td>{risk.final.severity}</td>"
            f"<td>{risk.final.likelihood}</td>"
            f"<td>{risk.final.score}</td>"
            f"<td>{esc(risk.final.level)}</td>"
            f"<td>{'Ja' if risk.confirmed else 'Nej'}</td>"
            f"<td>{measures_html}</td>"
            "</tr>"
        )

    risks_table = (
        "<table class='kv risks'>"
        "<tr>"
        "<th>Risk</th><th>Allvar</th><th>Sannolikhet</th>"
        "<th>Poäng</th><th>Nivå</th><th>Bekräftad</th><th>Åtgärder</th>"
        "</tr>"
        f"{risks_rows}"
        "</table>"
    )

    return (
        "<!doctype html>"
        "<html lang='sv'>"
        "<head>"
        "<meta charset='utf-8'/>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'/>"
        "<style>"
        "body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;font-size:12px;}"
        "h1{font-size:20px;margin:0 0 12px 0;}"
        "h2{font-size:14px;margin:16px 0 8px 0;}"
        ".section{border:1px solid #111;padding:12px;margin:12px 0;}"
        ".kv{width:100%;border-collapse:collapse;}"
        ".kv th{width:25%;text-align:left;border-top:1px solid #111;padding:6px 8px;"
        "vertical-align:top;}"
        ".kv td{border-top:1px solid #111;padding:6px 8px;}"
        ".risks th{width:auto;}"
        ".warning{border-color:#7a003c;}"
        "</style>"
        "</head>"
        "<body>"
        f"<h1>{esc(title)}</h1>"
        "<section class='section'>"
        "<h2>Kontext</h2>"
        f"{context_table}"
        "</section>"
        "<section class='section'>"
        "<h2>Förutsättningar</h2>"
        f"{prep_table}"
        "</section>"
        "<section class='section'>"
        "<h2>CLP-klassning</h2>"
        f"{clp_table}"
        "</section>"
        "<section class='section'>"
        "<h2>Kemiska heuristiker</h2>"
        f"{heuristics_table}"
        "</section>"
        f"{warnings_html}"
        "<section class='section'>"
        "<h2>Risker och åtgärder</h2>"
        f"{risks_table}"
        "</section>"
        "</body>"
        "</html>"
    )
