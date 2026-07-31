---
type: story
id: ST-SKRIPT-08-05
title: Tool results + downloads help
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-08
acceptance_criteria:
- Given a result page, when opening help, then it explains status, result preview,
  and downloadable files
- Given an error result, when opening help, then it explains what the user can do
  next (try again or contact maintainer/admin) without technical jargon
retired_ids:
- ST-08-05
---

## Context

Kontext-hjälp för resultatyta och nedladdningar:

- `tools/result.html` + `tools/partials/run_result.html`
- `my_runs/detail.html` (visar samma run_result)

## Epic Contract Slice

Kontext-hjälp för resultatyta och nedladdningar:

- `tools/result.html` + `tools/partials/run_result.html`
- `my_runs/detail.html` (visar samma run_result)

## ADR Coverage

No separate material is recorded in the source snapshot.

## Contract Inputs

- `src/skriptoteket/web/templates/tools/result.html`
- `src/skriptoteket/web/templates/tools/partials/run_result.html`
- `src/skriptoteket/web/templates/my_runs/detail.html`
- `src/skriptoteket/web/templates/partials/` (help topics)

## Live Verification Plan

- [ ] Skapa help topic för resultatsidan (hur man tolkar status, resultat och filer)
- [ ] Skapa help topic för “Mina körningar”-detalj (om relevant)
- [ ] Säkerställ att hjälpen inte beskriver interna tekniska detaljer (stdout/stderr etc.)

## Non-Goals

No separate material is recorded in the source snapshot.

## Notes

### Scope

Kontext-hjälp för resultatyta och nedladdningar:

- `tools/result.html` + `tools/partials/run_result.html`
- `my_runs/detail.html` (visar samma run_result)

### Tasks

- [ ] Skapa help topic för resultatsidan (hur man tolkar status, resultat och filer)
- [ ] Skapa help topic för “Mina körningar”-detalj (om relevant)
- [ ] Säkerställ att hjälpen inte beskriver interna tekniska detaljer (stdout/stderr etc.)

### Files

- `src/skriptoteket/web/templates/tools/result.html`
- `src/skriptoteket/web/templates/tools/partials/run_result.html`
- `src/skriptoteket/web/templates/my_runs/detail.html`
- `src/skriptoteket/web/templates/partials/` (help topics)

## Decision And Assumption Ledger

The source snapshot is the governing record for the decisions and assumptions stated above.

## Plan Document Review

No separate material is recorded in the source snapshot.

## Story Closeout Review

No separate material is recorded in the source snapshot.
