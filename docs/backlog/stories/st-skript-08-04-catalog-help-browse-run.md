---
type: story
id: ST-SKRIPT-08-04
title: Catalog help (browse + run)
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
- Given browse pages, when opening help, then it explains how to navigate yrke → kategori
  → verktyg
- Given a tool run page, when opening help, then it explains how to upload a file
  and run the tool
- Given the file upload control, when opening field help, then it explains what kind
  of file is expected in plain Swedish
retired_ids:
- ST-08-04
---

## Context

The source does not provide a separate context section; no additional context is recorded.

## Epic Contract Slice

### Source: Scope

Kontext-hjälp för katalogflödet:

- `browse_professions.html`
- `browse_categories.html`
- `browse_tools.html`
- `tools/run.html`

## ADR Coverage

The source does not provide a separate adr coverage section; no additional adr coverage is recorded.

## Contract Inputs

### Source: Files

- `src/skriptoteket/web/templates/browse_professions.html`
- `src/skriptoteket/web/templates/browse_categories.html`
- `src/skriptoteket/web/templates/browse_tools.html`
- `src/skriptoteket/web/templates/tools/run.html`
- `src/skriptoteket/web/templates/partials/` (help topics)

## Live Verification Plan

The source does not provide a separate live verification plan section; no additional live verification plan is recorded.

## Non-Goals

The source does not provide a separate non-goals section; no additional non-goals is recorded.

## Notes

The source does not provide a separate notes section; no additional notes is recorded.

### Source: Tasks

- [ ] Skapa help topics för varje sida (kort, stegvis, actions-fokuserat)
- [ ] Lägg till fält-hjälp vid filuppladdning på `tools/run.html`
- [ ] Säkerställ “Till hjälpindex” fungerar från alla dessa sidor

## Decision And Assumption Ledger

The source does not provide a separate decision and assumption ledger section; no additional decision and assumption ledger is recorded.

## Plan Document Review

The source does not provide a separate plan document review section; no additional plan document review is recorded.

## Story Closeout Review

The source does not provide a separate story closeout review section; no additional story closeout review is recorded.
