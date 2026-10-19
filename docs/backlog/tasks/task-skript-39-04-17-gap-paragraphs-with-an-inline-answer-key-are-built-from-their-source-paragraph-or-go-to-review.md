---
type: task
id: TASK-SKRIPT-39-04-17
title: Gap paragraphs with an inline answer key are built from their source paragraph or go to review, so the question word is never lost
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-19'
status: proposed
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - A gap_fill body paragraph aligned to a source paragraph with an inline answer label and no blank run before it is built from that source paragraph or sends the item to review; the reply's wording never replaces the source wording
story: ST-SKRIPT-39-04
backlog_document_profile: contract-derived
---

## Implementation Contract

The TASK-SKRIPT-39-04-15 baseline read (2026-10-18) found that in
`svenska_2_grammatik_omprov_variant_1_med_facit` and `variant_2`, item_001
(Fråga 1, gap_fill, admitted `review_complete`) loses the word to be split and
shows the inline answer key's morpheme split instead: `a) sol[gap] + ros[gap] + or[gap] + na[gap] + s[gap]` (variant 2) and `a) snö + boll + ar + na + s[gap][gap][gap][gap][gap]` (variant 1).

Root cause (R1). The source paragraphs `body:0010`-`body:0012` are each
`a) <word> Svar: <split with (R)/(A)/(B)>`. They hold no underscore, dot or
ellipsis. The converter model's reply (recordings `docx_w2-05-01.json`,
variant 2, and `docx_w1-01.json`, variant 1) drops the word and writes the key
split as body text with one gap per class. The projection (formatting event
`aligned`) transfers marks only, so the body keeps the reply's text. The
TASK-SKRIPT-39-04-16 rebuild does not reach these paragraphs:
`source_gap_paragraphs._content_end` cuts the span at `Svar`
(`a) solrosornas `), `blank_runs` is empty, `_gap_unit` returns `None`, and its
D7 keeps the reply's rendering, so its D5 count check never runs. The
projection's loss signals look only at marked characters, and the dropped word
is unmarked.

This task gives such a paragraph a structural build rule, so its source text is
kept or the item goes to review.

## Contract Inputs

- Finding: TASK-SKRIPT-39-04-15 lead's baseline read, routed by the Mac parent
  2026-10-18; Hemma orchestrator brief 2026-10-19.
- Evidence (retained root `01a151da-eb66-7449-b7af-fb972ebb49f4`):
  `evidence/read/root-cause.md`, `evidence/probes/source_chunks.py`,
  `evidence/probes/gap_unit_probe.py` and `.out`.
- Seam: `source_gap_paragraphs.py` (`blank_runs`, `_content_end`,
  `_gap_unit`, `gap_paragraphs_from_source`), TASK-SKRIPT-39-04-16 D2-D8.
- Scope probe over the ten replay dumps at `389b1aee`
  (`~/logs/replays-39-04-gap-source/head2`): this item, in its two variants,
  is the only gap_fill whose source lines carry an inline answer label with no
  blank before it.

## Core Vertical And Performance

One more check inside the existing `_gap_unit` pass; no new data is stored and
the document and event formats are unchanged.

## Validation

- Adversarial unit tests with the two recorded reply shapes (gaps between the
  key's morphemes; gaps appended after the morpheme list): before the fix the
  built body lacks the source word; after it the source word is kept or the
  item goes to review. A paragraph with underscore blanks before an inline
  answer label keeps its 39-04-16 build; a paragraph with no answer label and
  no blank run keeps the reply's rendering.
- The ten recorded replays: only the two svenska_2 item_001 change; every
  other difference is a proven fix or goes to the parent before merge.
- On Hemma: the touched-domain suite
  `PYTHONHASHSEED=0 pdm run test-parallel tests/unit/application/curated_apps tests/unit/domain/curated_apps -q -p no:randomly`
  after the parent's go, `pdm run lint`, `pdm run typecheck`,
  `pdm run docs-validate`.

### Replay outcome (2026-10-19)

The ten recorded replays, dumped with documents and events (UUIDs masked) at
the base `830f13bc` and at `14862085`, differ in exactly one item in two
exams: `svenska_2_grammatik_omprov_variant_1_med_facit` and `variant_2`
item_001 (Fråga 1). Each moves from `review_complete` with the reply's
morpheme split (`a) snö + boll + ...[gap]x5`, `a) sol[gap] + ros[gap] ...`)
to `review_required` / `source_fallback` with reason "Frågan följer inte
provformatet: 5 luckor men 1 tom svarsrad." and its source text intact
(`a) snöbollarnas Svar: ...`, `a) solrosornas Svar: ...`). Its formatting
event `aligned` becomes the admission event `gap_count_mismatch` ("5 gaps for
1 blank runs"). No other item, document field or event changes
(`~/logs/replays-39-04-17/`, retained `evidence/read/replay.diff`).

### Resume here (2026-10-19)

- State: U1 integrated (`14862085`, docstring repair `0a93eaee`); `origin/main`
  at `a8195345` (TASK-SKRIPT-39-04-15) merged at `30e2c846` (only the
  generated `docs/repository-index.json` conflicted, taken from main and
  regenerated); the new test file now passes `foreign_chunks=()` (`c2d80fa3`).
- After the merge: the focused files pass (57 tests); lint, backend typecheck
  and docs-validate pass. Frontend is not touched (`vue-tsc` is not installed
  in this worktree). Replays at `a8195345` against `c2d80fa3`
  (`~/logs/replays-39-04-17-merged/`, retained
  `evidence/read/replay-merged.diff`) repeat the replay outcome above: only
  the two svenska_2 item_001 and their formatting event change.
- Domain suite at `2def276f`: 19 failed, 4230 passed, 59 skipped
  (`~/logs/suite-39-04-17.log`). The five failing files pass at `a8195345`.
  Eighteen are replay guards asserting no `gap_count_mismatch` or 15 gaps for
  this item. One, `test_unmarked_morpheme_alignment_keeps_model_wording_and_never_leaks_facit`
  (`a864a085`, 2026-10-15), pins the old body and that "Svar:" and the key
  never show in the body; the D4 review body is the whole source and shows the
  key.
- Blocked: G2 below, returned to the orchestrator 2026-10-19. No code change
  until it is decided.
- Open: G1 (review copy) with the user.
- Branch `codex/task-skript-39-04-17-remote`, worktree
  `/home/paunchygent/apps/skriptoteket-task-skript-39-04-17-remote`; never
  pushed.
- Retained root:
  `/home/paunchygent/apps/skriptoteket/.orchestration/context/sessions/01a151da-eb66-7449-b7af-fb972ebb49f4`.

## Stop Conditions

- A replay difference that is not a proven fix goes to the parent before merge.
- No wording comparison and no fallback: a paragraph that cannot be built from
  its source sends the item to review.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | The rule applies to gap_fill body paragraphs aligned (`SourceFormatting.output_anchors`) to a source paragraph whose 39-04-16 build span holds no blank run and that carries an inline answer label (`ANSWER_LABEL`). Decided by the implementation lead from the root cause.                                                                                                                                                                                                                              |
| D2  | No wording comparison and no fallback: the reply's wording never replaces the source wording in such a paragraph (39-04-16 D8, ST-SKRIPT-39-04).                                                                                                                                                                                                                                                                                                                                                           |
| D3  | Owning story is ST-SKRIPT-39-04; the task builds on main at `7bcc7f5b7`. Replay identity outside the two svenska_2 item_001 is the regression bar.                                                                                                                                                                                                                                                                                                                                                         |
| D4  | In a gap_fill item, a source paragraph with no blank run before an inline answer label (`ANSWER_LABEL`) has one blank run at the label's place. The paragraph is built from source up to the label (39-04-16 D2 span, the gap at the label's place: `a) solrosornas [gap]`). A reply gap count other than 1 raises `GapCountMismatchError`, and admission sends the item to review (39-04-16 D5). Orchestrator ruling 2026-10-19 (option A; a merged gap would change gap ids, which 39-04-16 D4 forbids). |
| D5  | Review with the source intact, instead of today's admitted item with the word lost, meets "never worse off than today". Orchestrator ruling 2026-10-19 on the TASK-SKRIPT-39-04-15 F2 re-review precedent (`898d311f`); no user gate.                                                                                                                                                                                                                                                                      |
| D6  | The change stays local to `_gap_unit`, `_unit_blank_runs` and `_content_end` in `source_gap_paragraphs.py`; `source_paragraph`, which TASK-SKRIPT-39-04-15 folds its builder onto, is not touched. 39-04-15 lands first; this branch then merges `origin/main` and reruns its tests and the replays. Orchestrator ruling 2026-10-19.                                                                                                                                                                       |
| G1  | Open user gate (copy), routed to the Mac parent 2026-10-19: the review reason for this mismatch. Until the user decides, the existing 39-04-16 D10 text built by `GapCountMismatchError.reason` is used, and the wording stays in that one place.                                                                                                                                                                                                                                                          |
| G2  | Open, orchestrator gate (2026-10-19): the D4 review body is the whole source, so it shows the inline answer key, against the 2026-10-15 "never leaks facit" test. Options: A cut each paragraph's inline key out of the review body on `gap_count_mismatch` (lead's recommendation; widens D6); B accept the key in the review_required body; C withdraw D4.                                                                                                                                               |
