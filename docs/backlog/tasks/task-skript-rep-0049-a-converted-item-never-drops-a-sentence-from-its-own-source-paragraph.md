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

| ID  | Decided contract term                                                                                                                                                                                                                                                        |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | metodprov 1 keeps "Gruppen har slumpat fram 120 tvåor från en fullständig elevlista." in the final item built from `body:0006`.                                                                                                                                              |
| D2  | The cause of the shortened own paragraph is named with evidence and fixed at that cause, never by a patch on the output.                                                                                                                                                     |
| D3  | Meaning-preserving rewording stays as the model wrote it and is not flagged; 39-04-14 D7 marking and the 39-04-15 D4 rule stay as they are.                                                                                                                                  |
| D4  | Proof replays the recorded conversion; new paid model calls or re-recordings need the user's decision.                                                                                                                                                                       |
| D5  | Real task: one independent review, at most one rereview per finding; staging import by the Mac.                                                                                                                                                                              |
| D6  | A converted item whose source text the facit repeats and the reply did not show becomes the printed review item; question text stays intact and no review_complete item carries facit (user decision "A: review item", via Mac 2026-10-22; D7 of 39-04-14 stays as written). |

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

### 2026-10-22 (lead): review repair round, widened scope

- Review `evidence/reviews/review-rep-0049.md` (ruthless-reviewer, changes_requested): F1 and F2 high, both in the new restore; F3 high, existing on main.
- Widened scope (orchestrator, Boy Scout rule, facit shown to students): F3 joins this branch as its own unit. It covers svenska_2 variant 2 Fråga 5 a-c, where the student body shows all three facit analyses. The italic key characters count as missing typography, and `rebuild_body`'s only key refusal is `ANSWER_LABEL`.
- Repair design. U2 (F3, F1): source text that the item's facit copies verbatim (the reply contract's `facit_text`), and that the reply body did not emit, becomes a recovered key carrier in `native_carrier_spans`. Like an answer label's tail, the carrier is excluded from the body source and counted as covered. No rebuild or restore can then emit it, and no wording list is involved. U3 (F2): the restore rebuilds each output paragraph's whole source extent, so a joined table row keeps every rendered cell.
- U2 (`f2ad253e6`): `native_carrier_spans(facit=…)` turns the longest runs of whole facit sentences into carriers. Each run must be found whitespace-folded on word boundaries inside one owner or body region and be wholly unemitted by the reply. The junior narrowed the order's "not all emitted" gate to "wholly unemitted": gap_fill facits restate the question with the answer, and the wider gate excluded the question text and broke five section-instruction tests. Fail-first: `test_source_facit_carriers.py`, `test_exam_workspace_docx_facit_carrier_replay.py` (Fråga 5) and the F1 admission case.
- U3 (F2): `sourced_fragments` reports each fragment's source end. `SourceFormatting.exact_extents` records each exact output's extent. The restore groups outputs by the source paragraphs they cover and rebuilds each group's whole span through `own_source_span`, the span form of the own builder. The facit-stretch check left the restore, because U2's carriers own that case. Fail-first: the F2 joined-row admission case.
- Replays after the repair (`evidence/replays/repair/`, `diff_base_repair.txt`): against base, exactly two items differ. Metodprov 1 item 1 holds the restored sentence. svenska_2 variant 2 Fråga 5 a-c ends each paragraph at "Analys:" and shows no analysis; its `facit_text` is unchanged. Curated-apps application and domain suites: 5214 passed, 59 skipped.

### 2026-10-22 (lead): rereview F4, decision A

- Rereview `evidence/reviews/review-rep-0049-rereview.md` approved F1, F2 and F3 and found F4 (high). U2's facit carriers also removed question context that the facit repeats, such as "A coin was tossed twice.", and gap instructions, such as "Read the passage.". Exact containment proves shared wording, not key ownership.
- Decision (orchestrator, option A): source text that the facit repeats, and that the reply did not emit, is never removed silently and never shown in a review_complete body. A source rebuild that would show it sends the item to the existing printed review item (the 39-04-15 F2 route). Option B, a sub-paragraph left-out mark, would change 39-04-14 D7 and waits for the user.
- U4: `native_carrier_spans` again holds only answer labels, points and score fields. U2's detection moved to `facit_shared_spans` and returns body spans that the body `SourceFormatting` holds as `facit_shared`. These spans are neither excluded nor covered. `SourceFormatting.refuse_facit_shared` raises `FormattingTransferError` beside each `ANSWER_LABEL` refusal: in `_rebuild`, `rebuild_body`, `own_source_span`, `gap_paragraphs_from_source` and the heading restore in `complete_source_formatting`.
- Changed outcome (decision A): the F1 case, case (c) and svenska_2 variant 2 Fråga 5 are now printed review items with their question text intact, where before they were review_complete with the facit text removed. The replay guards (`recorded_build_events_support.py`, the corpus formatting test, `_REVIEW_INLINE_POINTS`) admit exactly this one decided Fråga 5 event and review item.
- Fail-first: the reviewer's coin case and gap case, and the Fråga 5 replay, failed on `0f77f6aef` and pass now.
- Replays (`evidence/replays/f4/`):
  - Against base (`diff_base_f4.txt`), two items differ. Metodprov 1 item 1 keeps the restored sentence and is still review_complete. Fråga 5 becomes the printed review item; on main, its body showed the analyses.
  - Against the repair round (`diff_repair_f4.txt`), only Fråga 5 differs.

### 2026-10-22 (lead): pre-push failure on the merge, light route

- The pre-push suite on merge `d9193a821` failed `tests/unit/infrastructure/curated_apps/test_exam_workspace_docx_answer_line_main_builders.py::test_a_rebuilt_misplaced_paragraph_drops_the_printed_answer_line_on_both_paths`. With no printed label, the restore counted the source's "1." as missing and brought it back. Questions are named by Skriptoteket's list labels, never by the source's numbering.
- U5: `restore_shortened_paragraphs` counts missing text from `_restore_start`. A `QUESTION_HEADING_LABEL` match at the start of the body's first visible paragraph is skipped. `own_source_span` takes that start. Fail-first: the failing test. Three admission cases cover a number restored away, a whole paragraph left unchanged, and a later "2)" paragraph that keeps its number.
- Replays (`evidence/replays/u5/`, `diff_f4_u5.txt`): identical to the approved F4 run.
