---
type: story
id: ST-SKRIPT-08-06
title: Contributor help (Mina verktyg + Föreslå skript)
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
- Given contributor pages, when opening help, then it explains what each panel lets
  the user do (edit, submit suggestion, choose professions/categories)
- Given non-trivial text fields (title/description), when focusing them, then placeholder
  examples are shown and field help is available
retired_ids:
- ST-08-06
---

## Context

No separate context is stated in the source.

## Epic Contract Slice

No separate epic contract slice is stated in the source.

## ADR Coverage

No separate adr coverage is stated in the source.

## Contract Inputs

No separate contract inputs is stated in the source.

## Live Verification Plan

No separate live verification plan is stated in the source.

## Non-Goals

No separate non-goals is stated in the source.

## Notes

No separate notes is stated in the source.

### Source: Scope


Kontext-hjälp för contributors:

- `my_tools.html`
- `suggestions_new.html`

### Source: Tasks


- [ ] Skapa help topics för båda sidorna (kort, actions-fokuserat)
- [ ] Lägg till fält-hjälp + placeholder-exempel för:
  - [ ] titel (t.ex. “Omvandla klasslista till …”)
  - [ ] beskrivning (t.ex. 1–2 meningar om nytta och input)
  - [ ] yrken/kategorier (vad markeringarna används till)
- [ ] Förklara granskningsflödet på ett icke-tekniskt sätt (”ligger i granskningskön”)

### Source: Files


- `src/skriptoteket/web/templates/my_tools.html`
- `src/skriptoteket/web/templates/suggestions_new.html`
- `src/skriptoteket/web/templates/partials/` (help topics)

## Decision And Assumption Ledger

| source | semantic | carried_forward | Source material is retained in the sections above. | source |

## Plan Document Review

No review evidence is recorded in this migration candidate; the frontmatter gate remains authoritative.

## Story Closeout Review

No review evidence is recorded in this migration candidate; the frontmatter gate remains authoritative.
