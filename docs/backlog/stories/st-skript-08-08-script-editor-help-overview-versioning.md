---
type: story
id: ST-SKRIPT-08-08
title: Script editor help (overview + versioning)
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
- Given the script editor page, when opening help, then it explains saving, drafts/versions,
  and the review/publish flow in plain Swedish
- Given role restrictions, when opening help, then it clarifies which actions are
  available for the current role
retired_ids:
- ST-08-08
---

## Context

The source does not provide a separate context section.

## Epic Contract Slice

### Source: Scope

Översiktshjälp för script editorn (utan testytan, som hanteras i ST-SKRIPT-08-09).

## ADR Coverage

The source does not record separate ADR coverage.

## Contract Inputs

The source does not record separate contract inputs.

## Live Verification Plan

### Source: Tasks

- [ ] Skapa help topic för `admin/script_editor.html` (översikt)
- [ ] Förklara panelerna: redigering, process (skicka för granskning/publicera/begär ändringar), historik (versioner)
- [ ] Lägg till micro-help för fält som är otydliga:
  - [ ] “Startfunktion” (vad ska stå där)
  - [ ] “Ändringssammanfattning” (kort exempel)

## Non-Goals

The source does not record separate non-goals.

## Notes

### Source: Files

- `src/skriptoteket/web/templates/admin/script_editor.html`
- `src/skriptoteket/web/templates/partials/` (help topics)

## Decision And Assumption Ledger

The source does not record a separate decision and assumption ledger.

## Plan Document Review

The source does not include a plan document review record.

## Story Closeout Review

The source does not include a story closeout review record.
