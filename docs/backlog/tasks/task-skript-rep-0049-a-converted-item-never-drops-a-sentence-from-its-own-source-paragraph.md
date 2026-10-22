---
type: task
id: TASK-SKRIPT-REP-0049
title: A converted item never drops a sentence from its own source paragraph
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-18'
status: ready
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

A teacher imports metodprov 1 (`tests/fixtures/exam_conversion/docx_corpus/metodprov_vetenskaplig_metod_med_facit.docx`). The item built from `body:0006` holds its whole own source paragraph, including "Gruppen har slumpat fram 120 tvåor från en fullständig elevlista.", and no rewording elsewhere is flagged. 39-04-15 is done, so its verdicts are the baseline. No performance concern is known.

## Validation

- Root cause named with evidence before any fix: where the sentence leaves the item between the recorded reply and the final item.
- A fail-first replay test over the recorded metodprov 1 conversion: the final item keeps the sentence. A guard test shows that a meaning-preserving rewording is still kept as the model wrote it and is not flagged.
- The existing 39-04-14 and 39-04-15 replay tests still pass.
- `pdm run lint`, `pdm run typecheck` and docs-validate.
- One independent review.
- A staging import of metodprov 1 by the Mac shows the sentence in its item.

## Stop Conditions

- The fix needs new paid model calls or re-recordings: the user decides.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                 |
| --- | ------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | metodprov 1 keeps "Gruppen har slumpat fram 120 tvåor från en fullständig elevlista." in the final item built from `body:0006`.        |
| D2  | The cause of the shortened own paragraph is named with evidence and fixed at that cause, never by a patch on the output.             |
| D3  | Meaning-preserving rewording stays as the model wrote it and is not flagged; 39-04-14 D7 marking and the 39-04-15 D4 rule stay as they are. |
| D4  | Proof replays the recorded conversion; new paid model calls or re-recordings need the user's decision.                               |
| D5  | Real task: one independent review, at most one rereview per finding; staging import by the Mac.                                     |

## Progress

### 2026-10-22 (Hemma orchestrator)

- Decided terms filled from the existing contract text, Core Vertical and Validation derived now that 39-04-15 is done, and status set to `ready` by the user's decision of 2026-10-22 (Mac AskUserQuestion, "39-10-02 + REP-0049"). A fresh lead session is assigned.
