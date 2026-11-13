---
type: task
id: TASK-SKRIPT-39-04-17
title: Gap paragraphs with an inline answer key are built from their source paragraph or go to review, so the question word is never lost
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-19'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-reviewer
  decided_at: '2026-10-19'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'Pi ruthless-reviewer 7ac4ca2f reviewed 5d70a359: no high findings, one medium (two test guards skipped every fallback item, so a review_complete item with a leaked label passed). Repaired at a8cd8181 (guards skip only review_required fallback-imported items, D9 amended, a test built on the reviewer probe failed before the fix) and admitted by the parent on focused proof without rereview: 120 focused tests, lint, typecheck and docs-validate pass; domain suite 4262 passed at 48852ace; replays change only svenska_2 item_001 in both variants, as decided in G1/G2 (user 2026-10-19). Merged to main at a8cd8181 on 2026-10-19.'
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
`a8195345` (main with TASK-SKRIPT-39-04-15) and at `4179f50c`, differ in
exactly one item in two exams: `svenska_2_grammatik_omprov_variant_1_med_facit`
and `variant_2` item_001 (Fråga 1). Each moves from `review_complete` with the
reply's morpheme split to `review_required` / `source_fallback` with reason
"Frågan följer inte provformatet: 5 luckor men 1 svarsplats." Its review body
shows the question as printed with each inline answer key cut (D7):
"a) snöbollarnas / b) skrivbarheten / c) fotbollsspelarnas" (variant 2:
"a) solrosornas / b) läsbarheten / c) handbollsspelarnas"), and no "Svar:"
and no "(R)", "(A)" or "(B)". Its formatting event `aligned` becomes the
admission event `gap_count_mismatch`. No other item, document field or event
changes (`~/logs/replays-39-04-17-final/`, retained
`evidence/read/replay-final.diff`).

### Resume here (2026-10-19)

- State: all units integrated. U1 `14862085` (D4), merge of `origin/main`
  `a8195345` at `30e2c846`, U2 `6c69fb20` (D7 review-body cut, D8 reason), U3
  `86a92fa4` (D9 replay guards; the 2026-10-15 morpheme test keeps its
  never-leaks assertions), U4 `4179f50c` (D9 source-review exemption).
- Focused proof: 117 tests across the twelve touched test files pass; lint,
  backend typecheck and docs-validate pass. Frontend is not touched (`vue-tsc`
  is not installed in this worktree).
- The first domain suite at `2def276f` (19 failed, 4230 passed, 59 skipped)
  found the guard and review-body gaps that D7-D9 settle.
- Domain suite at `48852ace`: 4262 passed, 59 skipped
  (`~/logs/suite-39-04-17-final.log`).
- Review `7ac4ca2f` (retained root `evidence/reviews/`): changes_requested,
  one medium finding F1 (the D9 exemption also skipped `review_complete`
  source-origin items). Repaired by U5 `dc94a988` (a test that fails before the
  fix, built on the reviewer's injection) and U6 `d561e701` (the shared helper
  moved into `recorded_build_events_support.py`); D9 amended at `ec123834`.
  Admitted on focused proof without rereview (orchestrator 2026-10-19).
- `origin/main` `0cb1df1a` merged at `561cd071` (only the generated index
  conflicted, regenerated). It adds the `defusedxml` dependency, so this
  worktree's environment was synced with `pdm sync`. The 120 focused tests,
  lint, backend typecheck and docs-validate pass. The replay difference
  (`0cb1df1a` against `561cd071`) is byte-identical to the reviewed one.
- Next: the orchestrator's integration into main.
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

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | The rule applies to gap_fill body paragraphs aligned (`SourceFormatting.output_anchors`) to a source paragraph whose 39-04-16 build span holds no blank run and that carries an inline answer label (`ANSWER_LABEL`). Decided by the implementation lead from the root cause.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| D2  | No wording comparison and no fallback: the reply's wording never replaces the source wording in such a paragraph (39-04-16 D8, ST-SKRIPT-39-04).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| D3  | Owning story is ST-SKRIPT-39-04; the task builds on main at `7bcc7f5b7`. Replay identity outside the two svenska_2 item_001 is the regression bar.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| D4  | In a gap_fill item, a source paragraph with no blank run before an inline answer label (`ANSWER_LABEL`) has one blank run at the label's place. The paragraph is built from source up to the label (39-04-16 D2 span, the gap at the label's place: `a) solrosornas [gap]`). A reply gap count other than 1 raises `GapCountMismatchError`, and admission sends the item to review (39-04-16 D5). Orchestrator ruling 2026-10-19 (option A; a merged gap would change gap ids, which 39-04-16 D4 forbids).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| D5  | Review with the source intact, instead of today's admitted item with the word lost, meets "never worse off than today". Orchestrator ruling 2026-10-19 on the TASK-SKRIPT-39-04-15 F2 re-review precedent (`898d311f`); no user gate.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| D6  | The change stays local to `_gap_unit`, `_unit_blank_runs` and `_content_end` in `source_gap_paragraphs.py`; `source_paragraph`, which TASK-SKRIPT-39-04-15 folds its builder onto, is not touched. 39-04-15 lands first; this branch then merges `origin/main` and reruns its tests and the replays. Orchestrator ruling 2026-10-19.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| D7  | When `gap_count_mismatch` sends an item to review, each review body paragraph is cut from its inline answer label onward (the cut 39-04-16 D2 applies to built paragraphs, with the wrapper `(` rule), and the trailing whitespace before the cut is trimmed. A picture after the cut stays, after the kept text. A paragraph the cut leaves empty is removed together with its aligned chunk entry. The word stays and the key stays out. The widening past D6's write boundary (admission and a shared label-cut helper) is accepted. User decision via the Mac parent 2026-10-19 (gate G2, option A).                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| D8  | The gap-count review reason is one wording for both blank kinds: "Frågan följer inte provformatet: 5 luckor men 1 svarsplats.", inflected by the item's own counts ("1 lucka" / "N luckor", "1 svarsplats" / "N svarsplatser"). It replaces the 39-04-16 D10 text. User decision via the Mac parent 2026-10-19 (gate G1); the plural "svarsplatser" confirmed by the Mac parent 2026-10-19.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| D9  | The replay guards that assert no build event outside the formatting stage allow exactly the svenska_2 omprov variant 1 and 2 Fråga 1 `gap_count_mismatch` (anchors `body:0008`-`body:0013`). The 2026-10-15 test `test_unmarked_morpheme_alignment_keeps_model_wording_and_never_leaks_facit` keeps its never-leaks assertions; only the assertions D4 makes obsolete (word absent, the reply's split, 15 gaps) are replaced. Orchestrator instruction 2026-10-19. Two guard invariants, "printed labels never enter student-visible text" and "points lines never reach an item", apply to admitted items. A pending source-review item (review state `review_required` and `parse_origin` `source_fallback`) shows the question as printed by design (`DocxBuildState.printed`, ruling 2026-10-18 c), so those two assertions skip it by its review state and origin, never by wording; a `review_complete` item stays checked whatever its origin (review 7ac4ca2f F1). Lead decision 2026-10-19, accepted by the Mac parent 2026-10-19. |
