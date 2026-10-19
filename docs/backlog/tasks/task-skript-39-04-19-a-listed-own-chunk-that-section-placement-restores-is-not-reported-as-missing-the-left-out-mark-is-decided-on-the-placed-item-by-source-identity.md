---
type: task
id: TASK-SKRIPT-39-04-19
title: A listed own chunk that section placement restores is not reported as missing; the left-out mark is decided on the placed item by source identity
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
  approval_evidence: 'Pi ruthless-reviewer c54c4ae4 (Hemma): no functional defects; medium M1 and M2 (file splits) repaired at 33ee7ad2 and admitted on focused proof (544 passed, lint and typecheck clean). Domain suite 5480 passed; its 15 test_spa_fallback failures match main (no built SPA in the worktree). Ten replays equal the base; the Del A probe ends review_complete with no reasons. origin/main 06985163 merged at 915be481; merged to main 2026-10-19. Validation names no staging walk.'
task_kind: story
acceptance_criteria:
  - A converted item whose listed own chunk section placement restores into its body or its parent shows no missing-text reason for that chunk; genuinely missing chunks and every unrelated review reason stay; the ten replays are identical
story: ST-SKRIPT-39-04
backlog_document_profile: contract-derived
---

## Implementation Contract

Defect: review 09d50acc M2 (medium), found in the TASK-SKRIPT-40-04-07 merge check
(`/home/paunchygent/apps/skriptoteket/.orchestration/context/sessions/01a14e6d-3ab6-7b8f-a363-3295c0f7fda6/evidence/reviews/09d50acc-f1f5-4ab1-9188-2c935dae7526-merge-check.md`).
A converted item lists its question's printed heading "Del A" and its body shows only
the stem. Admission marks the heading as missing source text. Section placement then
inserts the heading into the item's body from its source chunk. The delivered item shows
"Del A" and still reads `review_required` with "Källtext som saknas: Del A".

Root cause (R1). The two steps never share the chunk's identity:

- `with_left_out` (`exam_workspace_docx_build_left_out.py`) runs at admission. Its
  "section-placed instruction" exclusion (TASK-SKRIPT-39-04-15 D2) reads
  `state.instructions`, the reply's listed instructions. A printed heading is no reply
  instruction. Placement makes it a run of its own (`with_heading_runs`), so admission
  cannot know that placement will restore it.
- `with_left_out_mark` (`docx_own_instructions.py`) writes the mark as rendered Swedish
  reason text on `item.review` and sets `review_required`. No anchor survives the mark.
- `place_section_instructions` (`docx_section_instructions.py`, the `_inserted(... _unshown(...))` call near line 421) inserts the carried heading with its anchor into
  the aligned item (`aligned.shows("body:0001")` is then true). It never reads the
  review reasons, and it cannot tie the mark's text to the anchor it just placed.

Probe at `ffbfa953` (lead, `scratch/del_a_probe.py` in the retained root): admission shows
`('body:0002',)`, holds `('body:0001', 'body:0002')`, records `own_chunks_left_out` for
`('body:0001',)`; the final body is `'Del A\nFörklara.'`, and the final review is
`review_required` with `(LEFT_OUT_REASON, 'Del A')`. This reproduces the reviewer's
seam log (`09d50acc-merge-seams-final.log`, lines 40-41).

Fix. The left-out mark is decided once, on the placed item, by anchor. Admission and the
D42 return record which own chunks the item leaves out. Placement renders the mark for
those still not shown at the item's question. W10 (TASK-SKRIPT-40-04-07) and every other
review reason stay unchanged.

## Contract Inputs

- Review 09d50acc M2 (path above) and its seam log.
- TASK-SKRIPT-39-04-15 D1 and D2; D42 (the module docstring of `docx_own_instructions.py`:
  an instruction stands at its question in the body of an item holding the question's own
  chunks, or on a parent holding such an item).
- Assignment from the Hemma orchestrator `944b5a5a`, 2026-10-19 (retained root
  `01a15302-b287-7db2-91ec-8e9629121eb1`, `evidence/assignments/67fffd4d-6d52-4b31-8ee0-32681644f7fd/`).
- Replay scope at the 39-04-17 final dumps (`~/logs/replays-39-04-17-final/head`): no item
  in the ten replays carries `LEFT_OUT_REASON` and no `own_chunks_left_out` event exists.

## Core Vertical And Performance

One anchor set per item, checked once per placement pass against the item's aligned
chunks and its parent's source anchors.

## Validation

- Fail-first adversarial unit tests, through `admit_batch` and `state.result()` (real
  admission and assembly):
  - a listed heading that placement restores into the body: no left-out reason, the
    item is `review_complete` when it has no other reason, and the admission event
    `own_chunks_left_out` is still recorded;
  - a listed heading that forms a parent over two items: no left-out reason on either
    item;
  - a genuinely missing listed chunk (word bank): the reason lists it;
  - one item with a restored heading and a missing word bank: the reason lists only the
    word bank;
  - an item with an unrelated review reason and a restored heading: the unrelated reason
    stays, the left-out reason is absent, the item stays `review_required`;
  - a misplaced own chunk sent back by `return_misplaced_own_chunks` and not shown on the
    second placement pass: marked once, never twice;
  - the retry path (`exam_workspace_docx_retry`): a reconverted item that leaves out an
    own chunk is still marked.
- After the merge of TASK-SKRIPT-40-04-07: its real-heading admission control test in
  `test_exam_workspace_docx_answer_line_heading.py` (comment citing 09d50acc M2) asserts
  that the final item carries no `LEFT_OUT_REASON`.
- Existing admission tests that read `LEFT_OUT_REASON` from `state.accepted` read it from
  `state.result()` instead (D4).
- The ten recorded replays (the `dump_replays_39-04-14.py` dump, base `ffbfa953` against
  the head): no difference (D6).
- `pdm run lint`, `pdm run typecheck`, `pdm run docs-validate`; one domain suite on Hemma
  after the orchestrator's go: `PYTHONHASHSEED=0 pdm run test-parallel tests/unit/application/curated_apps tests/unit/domain/curated_apps tests/unit/web -q -p no:randomly`.

### Resume here (2026-10-19, lead 67fffd4d)

- Branch `codex/task-skript-39-04-left-out-remote`, worktree
  `/home/paunchygent/apps/skriptoteket-task-skript-39-04-left-out-remote`, from
  `origin/main` `ffbfa953`. Never pushed.
- Retained root `/home/paunchygent/apps/skriptoteket/.orchestration/context/sessions/01a15302-b287-7db2-91ec-8e9629121eb1`.
- State: review c54c4ae4 at `e3410b1e` changes_requested, two medium structural
  findings, both repaired as pure moves; waiting for the orchestrator's admission (no
  rereview required).
- Review c54c4ae4 M1 (junior `3c47a310`, `760dc1ff`): the printed-points admission tests
  moved from `test_exam_workspace_docx_left_out_admission.py` (344 lines) to
  `test_exam_workspace_docx_points_label_admission.py` (176 lines); `_stem_texts` moved
  into the shared test support module; 17 tests before and after.
- Review c54c4ae4 M2 (junior `5d4ca7b7`, `952da449`): `aligned_native_item` and its
  helpers moved from `docx_ai_build.py` (239 lines) to `docx_ai_item.py` (275 lines); every
  importer imports each symbol from its owner (`review_source_item` from
  `docx_source_review`); every function body unchanged.
- Proof after the repairs: 544 focused tests pass; lint and backend typecheck clean.
- Domain suite at `fbf9ed95` (application, domain, web and infrastructure curated_apps;
  `evidence/domain-suite-fbf9ed95.log`): 5480 passed, 59 skipped, 15 failed. All 15 are
  `tests/unit/web/test_spa_fallback.py` (HTTP 500). They fail the same way at
  `origin/main` `14f643c9` in this worktree: the fallback serves
  `src/skriptoteket/web/static/spa/index.html`, which exists only after a frontend
  build, and this worktree has none.
- U1 domain (junior `1e3a096f`, `5761395c`): `AlignedItem.left_out`,
  `with_placed_left_out_mark`, the placement call and the D42 return; order
  `evidence/orders/u1-domain-left-out-mark.md`.
- Merged `origin/main` `14f643c9` (TASK-SKRIPT-40-04-07) in `f217923c`; only conflict
  `docs/repository-index.json` (regenerated); `2a8996c1` adds `writing_lines` to the U1
  test builder for 40-04-07's free_text rule.
- U2 application (junior `bfbb5c87`, `0a33517b`; its run ended on a provider error after
  the commit): admission records the anchors, retry renders the mark (D7), the admission
  tests assert on `state.result()` (D4), the 40-04-07 Del A control test asserts the stale
  reason is gone. Fail-first: a, c, d failed on the stale mark before U2.
- Proof at `392cab8d`: 134 focused tests pass; lint clean; backend typecheck clean (the
  frontend phase cannot run here: no `node_modules`, frontend untouched); docs-validate
  clean. Ten replays (`~/logs/replays-39-04-19/`, base `14f643c9`) identical (D6). Del A
  probe (`scratch/del_a_probe.py`): final body `Del A\nFörklara.`, `review_complete`, no
  reasons, admission event `own_chunks_left_out` still recorded.

## Stop Conditions

- The domain suite runs only after this branch has merged `origin/main` with
  TASK-SKRIPT-40-04-07 on it, and after the orchestrator's go.
- Any replay difference goes to the orchestrator before merge.
- No `kind == "heading"` exclusion at admission or in W10, no reset of `review_required`,
  and no comparison of reason or body wording.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| D1  | `AlignedItem` carries `left_out: frozenset[str]`, the anchors of the own chunks the item leaves out (default empty). `with_left_out` keeps its examined set, its `left_out_chunks` call and its `own_chunks_left_out` admission event, and adds the missing anchors to `left_out`; it no longer calls `with_left_out_mark`. `return_misplaced_own_chunks` adds its missing anchors to `left_out` the same way and records its event as today.                                                          |
| D2  | A left-out anchor is shown when the placed item's body paragraph or entry is aligned to it (`left_out_chunks`), or when it is a source anchor of the instruction of a parent that holds the item (D42). Nothing else counts: no wording, no chunk kind, no other item.                                                                                                                                                                                                                                 |
| D3  | One domain function in `docx_own_instructions.py` renders the mark: from the item's `left_out` anchors, in source order, minus the shown ones (D2), it calls `with_left_out_mark` when any remain and returns the item unchanged otherwise. `place_section_instructions` calls it once per item at the end of its item loop, with that item's parent source anchors. The mark is computed from the anchor set on every pass and never written back into `accepted`, so the D42 loop cannot mark twice. |
| D4  | Tests that assert `LEFT_OUT_REASON` on `state.accepted` items assert it on `state.result()` items, plus the admission event; the admission-time item carries `left_out` and no left-out reason.                                                                                                                                                                                                                                                                                                        |
| D5  | `review_required` and its reasons change only through D3. Every other review reason, and every reason order outside the left-out reason, is unchanged.                                                                                                                                                                                                                                                                                                                                                 |
| D6  | The ten replays at the head equal the base `ffbfa953` dump: no replay item carries the left-out mark today.                                                                                                                                                                                                                                                                                                                                                                                            |
| D7  | The retry path renders the mark on its single admitted item with no parent anchors (D3), before `_with_owned_contexts` and `_review_reason` read it, because retry has no section placement.                                                                                                                                                                                                                                                                                                           |
| D8  | Owning story ST-SKRIPT-39-04; review 09d50acc M2 is the defect authority; 39-04-15 D1 and D2 stand as written, and this task implements D2's "an instruction that section placement places" at placement.                                                                                                                                                                                                                                                                                              |
| D9  | User answer 2026-10-19 (given in the Hemma session, relayed by the orchestrator `944b5a5a`): a listed chunk that placement restores keeps no review reason for the recovery. The stale "Källtext som saknas" mark disappears, the `own_chunks_left_out` admission event stays as the record, and unrelated reasons stay. No recovery note, so no new wording. The user accepted this design with that answer; status `ready` under `agent-planning:user-closure-gate`.                                 |
