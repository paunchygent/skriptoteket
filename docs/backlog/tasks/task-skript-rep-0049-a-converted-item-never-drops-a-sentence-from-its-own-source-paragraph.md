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

| ID  | Decided contract term                                                                                                                       |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | metodprov 1 keeps "Gruppen har slumpat fram 120 tvåor från en fullständig elevlista." in the final item built from `body:0006`.             |
| D2  | The cause of the shortened own paragraph is named with evidence and fixed at that cause, never by a patch on the output.                    |
| D3  | Meaning-preserving rewording stays as the model wrote it and is not flagged; 39-04-14 D7 marking and the 39-04-15 D4 rule stay as they are. |
| D4  | Proof replays the recorded conversion; new paid model calls or re-recordings need the user's decision.                                      |
| D5  | Real task: one independent review, at most one rereview per finding; staging import by the Mac.                                             |

## Progress

### 2026-10-22 (Hemma orchestrator)

- Decided terms filled from the existing contract text, Core Vertical and Validation derived now that 39-04-15 is done, and status set to `ready` by the user's decision of 2026-10-22 (Mac AskUserQuestion, "39-10-02 + REP-0049"). A fresh lead session is assigned.

### 2026-10-22 (lead): root cause

Evidence: retained root `01a160cd-e60f-7a6f-8166-26210b7bf1db`, `evidence/probes/`.

- The build request `docx_w1-01` carries `body:0006` whole, with both sentences (`body0006_probe.py`).
- The recorded reply's item 1 body paragraph holds only the first sentence. The sentence leaves at the reply: the model shortened its own paragraph, although the prompt asks for every word in order.
- `SourceFormatting._paragraph` accepts that text on the `exact` path, because it is a span of the source. The coverage gate `source_format_coverage.complete_source_formatting` then counts as missing only characters with a source mark, plus unprojected heading paragraphs. The unmarked second sentence is never counted, so the item keeps the short paragraph, and the sentence survives only in the import record. This gate is the cause the code can fix without a new model call (D4).
- Gate probe over the eight recorded exams (`gate_probe.py`, `gate_base.tsv`): metodprov 1 `body:0006` is the only text-only `exact` paragraph that leaves out visible own text no surface shows. Gap paragraphs, which Task 1 rebuilds, and reworded `aligned` paragraphs (D3) fall outside the rule. In svenska_2 variant 2 Fråga 5 a-c, the left-out "Analys: …" text is the item's facit, and it stays out of the body.
- Fix: after the gate, a text-only `exact` body paragraph whose own source paragraph holds visible text that no surface shows (the body, entries, label, excluded intervals, blank runs, or an exact span of the item's facit) shows its whole own source paragraph. The rule uses 39-04-15's own-paragraph builder.

### 2026-10-22 (lead): implementation and proof

- Code: `source_shortened_paragraph.restore_shortened_paragraphs`, called in `docx_ai_item` right after `complete_source_formatting`. `SourceFormatting` records exact and other-path origins. `source_format_coverage.accounted_characters` holds the gate's accounted set, which both steps read. `own_source_paragraph` is the renamed 39-04-15 builder.
- Fail-first: `test_exam_workspace_docx_shortened_paragraph_replay.py` (metodprov 1 item 1 shows both sentences of `body:0006`, the sentence exactly once) and admission case (a) fail with the restore bypassed and pass with it. The admission file also holds cases (b) to (h). Case (b) is the D3 guard: a reworded reply that also leaves out a sentence keeps the model's wording and gets no left-out mark.
- Replays: all eight recorded exams, snapshotted before and after (`evidence/replays/`, `diff_base_post.txt`), differ in exactly one item: metodprov 1 item 1 now holds "Gruppen har slumpat fram 120 tvåor från en fullständig elevlista.".
- Found, not fixed (outside scope): on main, svenska_2 variant 2 Fråga 5 a-c shows its italic answer analysis ("Analys: Klassen (S) läste (P) …") in the item body. `rebuild_body` restores the marked analysis because "Analys:" is not an `ANSWER_LABEL`. Reported to the orchestrator.
