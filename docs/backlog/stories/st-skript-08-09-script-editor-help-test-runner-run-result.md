---
type: story
id: ST-SKRIPT-08-09
title: Script editor help (test runner + run result)
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-07-31'
status: ready
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-08
acceptance_criteria:
  - Given the script editor test area, when opening help, then it explains how to choose a file, run a test, and read the result
  - Given run errors, when opening help, then it explains next steps (fix code, try again) without technical jargon
retired_ids:
  - ST-08-09
backlog_document_profile: contract-derived
---

## Slice Contract

Deferred by the user on 2026-10-28 (TASK-SKRIPT-REP-0055 D3). No work is scheduled and the status is unchanged; the contract below stays as written.

## Context

### Scope

Hjälp för testytan i editorn:

- Filuppladdning + “Testkör”
- Resultatytan (status, resultat/iframe, filer)

### Tasks

- [ ] Skapa help topic för testytan i `admin/script_editor.html`
- [ ] Lägg till fält-hjälp vid filval (vad som händer och vad som används som input)
- [ ] Förklara resultaten kort och action-fokuserat (t.ex. “om du ser fel: justera koden och testkör igen”)

### Files

- `src/skriptoteket/web/templates/admin/script_editor.html`
- `src/skriptoteket/web/templates/admin/partials/run_result.html`
- `src/skriptoteket/web/templates/partials/` (help topics)

## Epic Contract Slice

The source material below remains authoritative for this section.

## Contract Inputs

The source material below remains authoritative for this section.

## Tasks

The source record did not define a separate section for this package heading.

## Verification

The source record did not define a separate section for this package heading.

## Decided Contract Terms

| ID  | Decided contract term                                                                                           |
| --- | --------------------------------------------------------------------------------------------------------------- |
| D1  | Deferred by the user on 2026-10-28 (TASK-SKRIPT-REP-0055 D3): no work is scheduled and the status is unchanged. |

## Live Verification Plan

Verification expectations remain in the retained source material below.

## Non-Goals

The source boundaries and recovery limits remain preserved below.

## Notes

The source material below remains authoritative for this section.

## Decision And Assumption Ledger

The source material below remains authoritative for this section.

## Plan Document Review

The source material below remains authoritative for this section.

## Story Closeout Review

The source material below remains authoritative for this section.
