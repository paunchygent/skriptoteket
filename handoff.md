## Current

- [ST-SKRIPT-39-05](docs/backlog/stories/st-skript-39-05-ai-first-docx-exam-conversion-with-a-gold-corpus-eval-loop.md)
  is `ready` (A1-A12). Owner: Claude parent session; implementers are Opus 5.5
  assignments and reviewers Pi Sol 6.1 high (role routes). Retained session
  `01a12706-566c-7480-acc3-427145283942`.

  - TASK-SKRIPT-39-05-01, -02 and -03 `done` (user closure 2026-10-11 after the
    staging walk on `1db37835`: 166/166 items on all eight principles, matching
    edit, QTI export; retained root
    `evidence/task-skript-39-05-03/staging-walk-1db37835/summary.md`).
  - [TASK-SKRIPT-39-05-05](docs/backlog/tasks/task-skript-39-05-05-remove-answer-key-wording-from-converted-exam-titles.md)
    `in_progress`: titles drop answer-key wording. Rereview approved `83501383`,
    merged `ece1b674`, pushed; staging walk 2026-10-11 on `ece1b674`: sa24 editor
    and QTI title "Test Unit 3 Discuss and Argue" (retained root
    `evidence/task-skript-39-05-05/staging-walk-ece1b674/`). Next: user closure.
    Prior recorded eval's three item failures match baseline `6bf05757`.
  - [TASK-SKRIPT-39-05-04](docs/backlog/tasks/task-skript-39-05-04-label-items-with-a-decisions-classifier-and-convert-type-focused-batches-in-parallel.md)
    `in_progress`, Claude parent (session `01a12706`), branch
    `codex/task-skript-39-05-04` in worktree `Skriptoteket-task-skript-39-05-04`.
    D23 revised, D40 and D41 (2026-10-12) built by P7-P9 (`de0c816e`,
    `1c9093fa`, `810610c6`). Live runs low-17..24: 302-309/314. Sol rereview
    at `e1471e2c` (retained `evidence/reviews/TASK-SKRIPT-39-05-04/rereview-e1471e2c.md`):
    F4/F5/F7/F9/F10 fixed; changes_requested for F11 (own chunk listed only as
    metadata skips the D41 mark) and F12 (test pins prompt prose).
    Now: P10 repairs F11/F12. Next: rereview of P10, browser walk (incl. D31
    Exam.net rubric check), merge. Follow-up task in ST-39-05: label-first
    review with per-question model retry, picture in review items and marks.

- [ST-SKRIPT-39-06](docs/backlog/stories/st-skript-39-06-teacher-authoring-of-every-exam-net-question-type-with-parent-and-child-questions.md)
  is `proposed` with a closed contract (P1-P13): teachers create the seven
  Exam.net types standalone or as parent with children (Deluppgift).
  All-types Exam.net import 2026-10-10 passed (exam 5310254, 13 tasks, 28p).
  Retained plan `01a127b9-9597-7303-b076-e5b24e5954d2`. Next: user
  proposed->ready; sequenced after story 8.

- [TASK-SKRIPT-REP-0037](docs/backlog/tasks/task-skript-rep-0037-multi-file-script-bank-tool-bundles-and-the-split-of-four-over-long-tools.md)
  `in_progress`, owner Codex (handed over by the Claude exam parent 2026-10-11).
  D6 (editor and version views show and save every bundle file) rereview approved
  `578d4a4d`, merged `4b68bcde` and pushed; staging `skriptoteket-dev` rebuilt and
  healthy on it. Gruppgenerator run on staging done. Production: `hemma-deploy`
  and `seed-script-bank --sync-code` were run there by mistake; gruppgeneratorn
  depublished, the other seeded tools stay unpublished. Staging grants
  `skriptoteket-proof-user` the contributor role and gruppgeneratorn maintainership.
  Next: finish the staging editor walk (sibling `grouping.py` shown; edit a sibling
  file, sandbox run, save), record the proof, close docs. UX note: a saved class
  list looks selected in step 2 but is not until the class name is filled.

- [TASK-SKRIPT-REP-0036](docs/backlog/tasks/task-skript-rep-0036-resolve-mina-filer-app-export-labels-from-the-app-id-prefix.md)
  is `ready` (user decision 2026-10-11); label behaviour user-witnessed. Review
  F1 (synthetic tests) and F2 (repeated listing queries) repaired, Sol rereview
  approved `0f17cc78`, merged `61cce3ac`. Next: user closure. Follow-up: Mina filer keeps every workspace version
  visible by user choice; head-only listing is a later task.

- 2026-10-09 planning session (Claude): user decisions recorded in
  EPIC-SKRIPT-39 — new story 8 converges the product exporter on the proven
  native QTI 3.0 Exam.net contract (HuleEduOS `examnet-qti-import` skill,
  probe rounds V1-V44) after story 5 and before story 7, with the QTI 2.1
  writer as the parity baseline until cutover (terms E13-E14); story-5
  breadth candidates add accepted-spelling variants, case-insensitive maps,
  letter hints, and the proven ordering type. ADR-SKRIPT-0066 gained an
  ADR-0090 amendment pointer. Verified on current sir-convert-a-lot main:
  the stale pre-beta QTI contract reference and the whole Sir exam domain
  are already removed (TASK-SIRCON-07-04-01); the residual hazard was
  EPIC-SIRCON-07/08 still `proposed`, which now carry supersession notes
  on sir-convert branch `claude/supersede-retired-exam-epics` pending
  merge and governed terminal closure. The HuleEduOS producer stays a
  deliberately separate hand-tool for now (E15). ADR-SKRIPT-0091 and
  ST-SKRIPT-39-04 were accepted by user decision 2026-10-09 (user-closure
  gate): ADR-0091 is `accepted` and the story is `ready`.

- TASK-SKRIPT-REP-0035 passive web liveness is deployed in production and staging.
  Owner: skill-repository parent 01a1036b; next: terminal closeout.
  Published c282c74b; exact image 0ae40a8a34a2; full startup healthy; /healthz 200.
  34 focused tests passed; next natural checks 25.005 ms prod / 24.596 ms staging.
  Proof: task-worktree .artifacts/native-health/passive-\*-rollout-proof.json (2026-10-06).

- [EPIC-SKRIPT-40](docs/backlog/epics/epic-skript-40-shared-design-system-convergence.md)
  is `ready`. TASK-SKRIPT-40-01-01 has an approved implementation review
  (`bda00b6a`) and adopts design-system metadata 0.1.23 through package
  sync. Current main was merged before integration.
  The adopted CSS and logo bytes did not change in this refresh. The task
  remains `in_progress`: this integration does not establish its required
  Hemma staging screen walk. Integration and cleanup evidence:
  HuleEdu retained session `01a0eef4-0059-7e04-a805-0991592709a1`.
  TASK-SKRIPT-40-02-01 waits on TASK-SKILL-REP-0187. Planning session:
  `01a0e4a4-436a-70d9-a907-702d84f2a091`.

- 2026-09-05 reconciliation (docs/planning only, no code): the user-approved
  native editable exam workspace is recorded in
  [EPIC-SKRIPT-39](docs/backlog/epics/epic-skript-39-skriptoteket-owned-exam-conversion.md)
  (terms E8-E12) plus `proposed`
  [ADR-SKRIPT-0091](docs/decisions/adr-skript-0091-native-editable-exam-workspace-narrows-the-adr-0090-authoring-ui-non-decision.md),
  [ST-SKRIPT-39-04](docs/backlog/stories/st-skript-39-04-native-editable-exam-workspace-with-docx-first-walking-skeleton.md),
  and
  [TASK-SKRIPT-39-04-01](docs/backlog/tasks/task-skript-39-04-01-docx-walking-skeleton-import-native-edit-and-create-save-and-reopen-export.md).
  Direction: DOCX upload first, digital PDF second, OCR deferred;
  deterministic extraction plus LLM parse/enrich/repair behind teacher
  review; versioned native documents with assets and editing state in Mina
  filer; PDF/DOCX/QTI are on-demand exports only. Cleanup first (02-03 done):
  03-03 and 03-04 are done; DOCX implementation waits for ADR-0091/story
  review. Verbose prior history archived to
  `.codex/long-term-memory/entries/session-2026-09-05-epic-39-handoff-compaction.md`.

- [TASK-SKRIPT-39-03-03](docs/backlog/tasks/task-skript-39-03-03-retire-the-sir-convert-exam-specific-integration.md)
  and [TASK-SKRIPT-39-03-04](docs/backlog/tasks/task-skript-39-03-04-retire-the-hemma-qwen-answer-key-sidecar.md)
  are `done` (2026-09-30, independent reviews approved). Linked Sir
  TASK-SIRCON-07-04-01/REP-0030 and Hule TASK-HULE-01-04-13/REP-0130 are done.
  Sir Convert production and STT stay offline by user decision; the
  Skriptoteket answer-key env keys (Luna/GLM) stay.

- [TASK-SKRIPT-39-02-03](docs/backlog/tasks/task-skript-39-02-03-repair-partial-digiexam-answer-key-enrichment-and-prove-the-real-integrated-vertical.md)
  is `done` (Pi closeout rereview approved `e877170d`): the item-local admission repair is already on `main` via
  `52ccc0a2` (real-DXE plan `ELIGIBLE` for 5 supported items, asset-bearing
  item-003 kept for manual review); the real-DXE fixture is byte-identical to
  its source (`ab39bbee`). Two unit tests pin D1. D5 was amended 2026-09-30
  by user decision to a real-browser click-through on Hemma's rootless Docker
  staging (`skriptoteket-dev`) after merge to `main`; staging now enables the
  answer-key lane from its untracked `.env` with the production provider keys.
  The D5 walk passed on 2026-09-30 at `e3ae9527`: questions 1, 2, 4, 5, 6 got
  provider proposals, asset-bearing question 3 stayed for manual review until
  a teacher key was saved, and the Exam.net PDF and QTI zip became
  downloadable; the enrichment and conversion jobs `succeeded`. The real-DXE
  PostgreSQL integration test passes (`1 passed`); three vacuous replay cases
  in `ExamConverterAuthenticatedFilesActionSlice.spec.ts` were removed (D3).
  Evidence: Skriptoteket session
  `01a0f227-63b9-7435-8013-5f556eaf4905`. It is a required predecessor for
  the DOCX skeleton.

- [TASK-SKRIPT-39-01-03](docs/backlog/tasks/task-skript-39-01-03-degrade-unknown-digiexam-question-types-to-reviewable-free-text.md)
  stays canceled (`d48233e9`); Exam.net acceptance stays user-owned and
  proven import acceptance is not reopened. Live-proven anchors: Sir
  `TASK-SIRCON-REP-0029`, Skript `TASK-SKRIPT-39-01-01` byte parity
  (`f36a4ae3…`).

- [ST-SKRIPT-39-02](docs/backlog/stories/st-skript-39-02-port-the-remote-answer-key-completion-line-with-a-daily-token-lease.md)
  is `done` and independently `VERIFIED` (record
  `.orchestration/context/sessions/01a04d62-…/evidence/reviews/ST-SKRIPT-39-02/terminal-spec-verification.md`).

- [EPIC-SKRIPT-39](docs/backlog/epics/epic-skript-39-skriptoteket-owned-exam-conversion.md)
  and [ADR-SKRIPT-0090](docs/decisions/adr-skript-0090-skriptoteket-owned-exam-conversion-boundary-with-sir-convert-generic-extraction.md)
  stay approved; ADR-0091 (`proposed`) narrows only the authoring-UI
  non-decision. Story 4 is the scaffolded DOCX workspace; story 5 adds
  DOCX breadth, story 6 digital-PDF intake, and story 7 QTI import.
  Stories 5-7 await their own detailed contracts.

- REP lane: 0032 and 0026 verified/done; 0030/0031 canceled; ST-38-01 and
  EPIC-SKRIPT-38 done; REP-0006/0003/0004/0005 done. Detail in the archived
  entry above.

## Recent

- Historical docs selector reads `docs/_meta/historical-docs-contract.yaml`
  (renamed in `1bcd4a38`); `test_historical_docs_validator.py` 3 passed.
- TASK-SKRIPT-39-04-04 `done` 2026-10-11 (user closure): pending proposals
  carried across saves; staging walk 2026-10-10 at `929e847a`, Sol `231a2190`,
  merge `e0746f2a`.

- 2026-10-10: TASK-SKRIPT-39-04-02 `done` by user acceptance of the
  four-viewport staging walk (`agent-planning:user-closure-gate`); `main`
  `acca1ee7` on staging; evidence in the task's Closeout Evidence.

- 2026-10-10: TASK-SKRIPT-39-04-01 `done` by user D5 approval
  (`agent-planning:user-closure-gate`); walk, proposal step, gap-key fix,
  missing-key export block (DOCX included, user decision) and small items
  on `main` through `77ea389f`; evidence in the task's Closeout Evidence.

- 2026-10-10: sir-convert-a-lot `main` pushed (`3fb6f672`) with the
  EPIC-SIRCON-07/08 supersession notes; their terminal closure is blocked
  on migrating both epics to the contract-derived profile with open child
  stories (user decision pending; ST-SIRCON-07-01 still states the old QTI
  2.1 claim).

- 2026-09-05: reconciled EPIC-39/ADR-0090 with the approved workspace scope
  via scaffolder-created ADR-0091, ST-39-04, and TASK-39-04-01 (all
  `proposed`); `pdm run docs-validate` green; `git diff --check` clean.

- 2026-08-30/31: public (03-02) and authenticated (03-01) cutovers done;
  both lanes run Skriptoteket-owned with zero Sir exam calls.

## Facts

- Session Date: 2026-10-10
- Last Refreshed: 2026-10-10
- Current docs validate with `pdm run docs-validate`.
- Historical terminal docs audit separately with `pdm run python -m scripts.historical_docs.validate_historical_docs`.
- The 2026-09-30 slices add TASK-SKRIPT-39-02-03 unit tests and a test-support
  module, amend its D5 gate, add the staging answer-key lane configuration, and
  remove three vacuous frontend replay tests; they change no production code.
- Full typecheck on 2026-10-10 reports 12 errors in untouched files: three
  `src/skriptoteket/script_bank/scripts/` demos and
  `tests/unit/web/test_observability_routes.py`. TASK-SKRIPT-39-05-02's
  changed-file type proof passes; retained capture `0098` in its session.
- Open product questions (undecided, not silently resolved): native doc
  format internals (new versioned doc type vs file-plus-sidecar state);
  deferred scanned-PDF behavior (hard-fail with guidance vs generic
  extraction queue); digital-PDF slice detail follows ST-39-04 review.
- Next: eval triage, item-type and parent/child authoring planning.
