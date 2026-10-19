---
type: task
id: TASK-SKRIPT-39-04-18
title: An inline answer key cut from a review question is carried into its facit exactly as printed and marked as taken from the source
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-19'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - When the 39-04-17 D7 cut removes an inline answer key from a review item's body, the item's facit holds that key text exactly as printed, its answer key is marked as taken from the source, the key never appears in the student-visible body, and the item stays review_required
story: ST-SKRIPT-39-04
backlog_document_profile: contract-derived
---

## Implementation Contract

After TASK-SKRIPT-39-04-17, `svenska_2_grammatik_omprov_variant_1_med_facit`
and `variant_2` item_001 (Fråga 1, "Dela upp orden i morfem") go to review as
a free_text item that shows the source words ("a) snöbollarnas",
"b) skrivbarheten", "c) fotbollsspelarnas"), but its `facit_text` and
`import_record.original_wording.answer_key_text` are null. The source printed
the key on each line: "Svar: snö (R) + boll (R) + ar (B) + na (B) + s (B)".

Root cause (R1). The 39-04-17 D7 cut throws the key away.
`review_answer_key_cut._cut_paragraph` keeps the text before
`answer_label_cut` and drops the rest; `without_inline_answer_keys` returns
only the cut body. The review item comes from `review_source_item`
(`docx_source_review.py:57`), which never sets `facit_text`, and
`with_docx_import_records` copies `item.facit_text` (null) into
`answer_key_text`. Before 39-04-17 the converter model's reply carried the key
in `facit_text`; the source review item has no reply, so the key now has no
holder.

This task keeps the cut key and puts it in the item's facit, exactly as
printed. The student-visible body keeps the 39-04-17 cut, and the item stays
`review_required` for the teacher to confirm.

Units:

- U1 (backend, junior): the carry in `review_answer_key_cut.py` (D1-D3),
  with adversarial tests in `test_review_answer_key_cut.py`, and the
  item_001 assertions in `test_exam_workspace_docx_gap_count_admission.py`
  and `test_exam_workspace_docx_inline_answer_key_replay.py` (`facit_text` and
  `answer_key_text` hold the printed key lines; the body holds no label and no
  key). Each key line keeps the paragraph's leading list label (Q3).
  The origin stays `not_applicable` (Q1).
- U2 (frontend, junior): `ExamWorkspaceQuestionEditor.vue` shows the existing
  facit line for an unbuilt item that has `facit_text` (Q2), with a Vitest
  spec beside it that fails before the change.
- Lead: integration, the ten replays, focused checks, and the domain suite
  after the orchestrator's go.

Non-goals: the retry path (`source_review_item`), other `state.printed`
callers, and the 39-04-17 cut itself, which stays as decided.

## Contract Inputs

- User decisions U-A to U-D, 2026-10-19, relayed by the Mac parent (Hemma
  orchestrator brief).
- TASK-SKRIPT-39-04-17 (done) D7 and its replay outcome; retained root
  `01a151da-eb66-7449-b7af-fb972ebb49f4`, `evidence/read/replay-final.diff`
  and `root-cause.md`.
- Code map (retained root `01a152e0-e3d9-79cd-b575-f90bfb3109f7`,
  explorers q1-q11): the cut (`review_answer_key_cut.py`), its one caller
  (`exam_workspace_docx_build_admission.py:167-172`), the origin vocabulary
  (`native_exam_vocabulary.py:54-63`), the free_text origin invariant
  (`native_exam_item.py:173-177`) and its frontend mirror
  (`examWorkspaceAnswerKeyRules.ts:84-92`), the import-record copy
  (`docx_import_records.py:74-78`), the editor facit line
  (`ExamWorkspaceQuestionEditor.vue:146-156`, `:329-339`) and the import box
  (`ExamWorkspaceImportBox.vue:93-99`).

## Core Vertical And Performance

One string join inside the existing cut pass; no new stored field, no
document or event format change, no migration.

## Validation

- U1: adversarial unit tests in `test_review_answer_key_cut.py`: one key line
  per cut paragraph in body order, verbatim from the label (and from the
  wrapper "(" in the "(Svar: …)" form); a picture after the cut stays in the
  body and out of the key; a printed answer line "Svar: \_\_\_\_\_\_" is not
  carried and leaves `facit_text` null; a paragraph without a label adds no
  line; each line keeps the paragraph's leading list label ("a) Svar: …")
  and a paragraph without one starts at the label; the body never holds the
  label or the key. Before the change the
  item's `facit_text` is null.
- U1: `test_exam_workspace_docx_gap_count_admission.py` and
  `test_exam_workspace_docx_inline_answer_key_replay.py` assert the item_001
  `facit_text` and `answer_key_text` equal the source key lines and that the
  item stays `review_required` / `source_fallback`.
- U2: the Vitest spec beside `ExamWorkspaceQuestionEditor.vue`.
- The ten recorded replays, dumped with documents and events (UUIDs masked)
  by `~/logs/dump_replays_39-04-14.py` from a `git archive` of `ffbfa953` and
  of the head: only items the D7 cut changes may differ, and each difference
  is the carried key.
- On Hemma, after the orchestrator's go: the touched-domain suite
  `PYTHONHASHSEED=0 pdm run test-parallel tests/unit/application/curated_apps tests/unit/domain/curated_apps -q -p no:randomly`,
  `pdm run lint`, `pdm run typecheck`, `pdm run docs-validate`; for U2 the
  frontend checks from `integrated-frontend-stack`.

### Resume here (2026-10-19)

- State: in_progress. The user answered Q1 (b), Q2 (yes) and Q3 (keep the
  part prefix) and accepted the plan on 2026-10-19; ledger closed. U1
  (backend carry, `3c49c605`) and U2 (editor facit line, `cfe1f25c`) are
  committed with focused proof (33 pytest, 4 Vitest). `origin/main`
  `14f643c9` (TASK-SKRIPT-40-04-07) is merged at `8d7d812b`.
- Replays (retained root `evidence/replays/TASK-SKRIPT-39-04-18/`):
  `14f643c9` -> `cfe1f25c` differs only in the two svenska_2 omprov item_001,
  in `facit_text` and `answer_key_text`, which hold the carried key lines. No
  key line holds answer-line text that W10 strips. `ffbfa953` ->
  `14f643c9` is the effect of 40-04-07 alone.
- Branch `codex/task-skript-39-04-facit-carry-remote`, worktree
  `/home/paunchygent/apps/skriptoteket-task-skript-39-04-facit-carry-remote`,
  from `origin/main` `ffbfa953`; never pushed.
- Retained root:
  `/home/paunchygent/apps/skriptoteket/.orchestration/context/sessions/01a152e0-e3d9-79cd-b575-f90bfb3109f7`
  (plan `evidence/planning/TASK-SKRIPT-39-04-18/plan.md`).
- Domain suite at `96930417`: 4620 passed, 59 skipped. Review `9f931df3`
  (changes_requested, F1 high): an unlabelled leading word such as
  "question text" became a huge Roman-numeral ordinal. Repaired in
  `8affda4b` (delimiter first, grammar shared through
  `_delimited_label_end`) and `7fbc6bc9` (decimal label checked without
  `int()`, which refused tokens over 4300 digits). Replays at `7fbc6bc9` are
  identical to `cfe1f25c`.
- Next: rereview of F1 by `9f931df3`, routed by the orchestrator.

## Stop Conditions

- A replay difference outside the items the D7 cut changes, or one that is
  not the carried key, goes to the parent before merge.
- The key never enters the student-visible body; no wording comparison and no
  fallback.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| U-A | When the 39-04-17 D7 cut removes an inline answer key from an item's body, that key text is carried into the item's facit, copied exactly as in the source with nothing rewritten, so the teacher sees it while reviewing. It never appears in the student-visible body. User 2026-10-19 via the Mac parent.                                                                                                                                                                                                                                                                   |
| U-B | The facit is marked as taken from the source, so the teacher can see where it came from. User 2026-10-19 via the Mac parent.                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| U-C | The rule applies to every item that the D7 cut changes, not only svenska_2. User 2026-10-19 via the Mac parent.                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| U-D | The item stays `review_required`; the teacher confirms the result. User 2026-10-19 via the Mac parent.                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| D1  | The carry has one owner, `review_answer_key_cut.py` (`without_inline_answer_keys`), reached only from the `GapCountMismatchError` branch of `_built` (`exam_workspace_docx_build_admission.py:167-172`), the only D7 caller; so it covers every item the D7 cut changes (U-C). No other `state.printed` caller changes. Lead decision 2026-10-19.                                                                                                                                                                                                                              |
| D2  | Each cut paragraph gives one key line: the paragraph's leading list label when it has one (Q3), then its source text from the cut point that `answer_label_cut` returns (the label, or the wrapper "(" before it) to the paragraph's text end, verbatim, trailing whitespace trimmed. `facit_text` is the key lines joined by a newline in body order. A picture or gap after the cut stays in the body (39-04-17 D7) and is not part of the key line. Lead decision 2026-10-19 under U-A, amended by Q3.                                                                      |
| D3  | A cut tail that holds nothing after its label but whitespace and blank runs (a printed answer line such as "Svar: \_\_\_\_\_\_") is not a key and is not carried; the test is structural (the existing blank-run recognition), never by wording. With no key line, `facit_text` stays null. Lead decision 2026-10-19 under U-A.                                                                                                                                                                                                                                                |
| D4  | `import_record.original_wording.answer_key_text` gets no second write: `with_docx_import_records` copies `item.facit_text` after admission on the publication path. Lead decision 2026-10-19 from the code map.                                                                                                                                                                                                                                                                                                                                                                |
| D5  | Owning story ST-SKRIPT-39-04; the task builds on main at `ffbfa953`. Regression bar: the ten replays differ only in items the D7 cut changes (today the two svenska_2 omprov item_001), and each difference is the carried key. Lead decision 2026-10-19.                                                                                                                                                                                                                                                                                                                      |
| Q1  | Carry `facit_text` only; `answer_key.origin` stays `not_applicable`. The existing "Facit ur provfilen:" (editor facit line) and "Facit i provfilen" (import box) labels show the key's source. No origin-rule change. User 2026-10-19, given directly in the Hemma orchestrator session.                                                                                                                                                                                                                                                                                       |
| Q2  | The question editor shows the existing facit line on an unbuilt (`review_required` + `source_fallback`) item that has `facit_text` (unit U2). User 2026-10-19, given directly in the Hemma orchestrator session.                                                                                                                                                                                                                                                                                                                                                               |
| Q3  | Each key line keeps its part prefix, so it reads "a) Svar: snö (R) + boll (R) + …". The prefix is the source paragraph's own leading list label, an ordinal token with its delimiter at the paragraph start as `entry_label_end` (`source_format_coverage.py`) recognizes it, taken structurally and never by wording, without its trailing whitespace and followed by one space. A paragraph with no such label gives a line that starts at the cut point. User 2026-10-19, given directly in the Hemma orchestrator session; overrides the planning lead's prefix-free line. |
| D6  | The user accepted the plan on 2026-10-19; status `ready` then `in_progress` under `agent-planning:user-closure-gate`.                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
