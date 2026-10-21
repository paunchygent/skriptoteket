---
type: task
id: TASK-SKRIPT-39-10-03
title: A PDF without readable text stops with a message, and skipped pages are named
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-21'
status: proposed
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - A PDF without text, or whose text layer is mostly unreadable, imports nothing and shows a stop message telling the teacher to save the exam as Word or as a PDF from the original
  - When only some pages lack readable text, the readable pages import and a note names the skipped pages
story: ST-SKRIPT-39-10
backlog_document_profile: contract-derived
---

## Implementation Contract

Scaffolded from the ST-SKRIPT-39-10 story terms (P2, P3, P7 and P8). The orchestrator writes the full contract from those terms when a lead slot opens after TASK-SKRIPT-39-10-01; status stays `proposed` until then.

## Contract Inputs

## Core Vertical And Performance

## Validation

## Stop Conditions

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
