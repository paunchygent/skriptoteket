---
type: story
id: ST-08-05
title: "Tool results + downloads help"
status: ready
owners: "agents"
created: 2025-12-17
epic: "EPIC-08"
acceptance_criteria:
  - "Given a result page, when opening help, then it explains status, result preview, and downloadable files"
  - "Given an error result, when opening help, then it explains what the user can do next (try again or contact maintainer/admin) without technical jargon"
---

## Scope

Kontext-hjälp för resultatyta och nedladdningar:

- `tools/result.html` + `tools/partials/run_result.html`
- `my_runs/detail.html` (visar samma run_result)

## Tasks

- [ ] Skapa help topic för resultatsidan (hur man tolkar status, resultat och filer)
- [ ] Skapa help topic för “Mina körningar”-detalj (om relevant)
- [ ] Säkerställ att hjälpen inte beskriver interna tekniska detaljer (stdout/stderr etc.)

## Files

- `src/skriptoteket/web/templates/tools/result.html`
- `src/skriptoteket/web/templates/tools/partials/run_result.html`
- `src/skriptoteket/web/templates/my_runs/detail.html`
- `src/skriptoteket/web/templates/partials/` (help topics)
