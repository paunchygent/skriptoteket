---
type: task
id: TASK-SKRIPT-REP-0049
title: A converted item never drops a sentence from its own source paragraph
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-18'
status: proposed
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
  - metodprov 1 keeps the sentence 'Gruppen har slumpat fram 120 tvåor från en fullständig elevlista.' in its final item
  - The cause of the shortened own paragraph is named and fixed at that cause, without flagging meaning-preserving rewording
backlog_document_profile: contract-derived
---

## Implementation Contract

The 39-04-15 interpretive read (2026-10-18) found metodprov 1 worse after conversion. Body paragraph `body:0006` keeps only the first sentence of its own source paragraph; "Gruppen har slumpat fram 120 tvåor från en fullständig elevlista." appears only in the import record. The reply's paragraph is an exact span of the item's own source, so the misplaced-only rule (39-04-15 D4) correctly leaves it, and 39-04-14 D7 keeps the drop unflagged. The user gate still applies: an item is never worse off after conversion than before.

This task traces why the reply shortens its own paragraph and fixes that cause, so a dropped sentence from an item's own source returns to the item. Meaning-preserving rewording stays as the model wrote it.

Non-goals: flagging rewording, changing 39-04-14 D7 marking, the svenska_2 Fråga 1 gap drops (39-04-17).

## Contract Inputs

- 39-04-15 task doc Validation (branch head 6d58822f on Hemma) and its `base_verdicts.json` / `post_verdicts.json`.
- 39-04-14 D7; memory rule: conversion quality means systematic drops, fixed at the root.

## Core Vertical And Performance

To be derived in planning after 39-04-15 merges. No performance concern known.

## Validation

To be derived in planning.

## Stop Conditions

- The fix needs new paid model calls or re-recordings: the user decides.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
