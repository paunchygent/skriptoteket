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
    `in_progress`: titles drop answer-key wording. Approved `83501383`, merged
    `ece1b674`; staging walk 2026-10-11 passed (retained
    `evidence/task-skript-39-05-05/staging-walk-ece1b674/`). Next: user closure.
    Prior recorded eval's three item failures match baseline `6bf05757`.
  - [TASK-SKRIPT-39-05-04](docs/backlog/tasks/task-skript-39-05-04-label-items-with-a-decisions-classifier-and-convert-type-focused-batches-in-parallel.md)
    `done` (user closure 2026-10-12, staging walk `63de8094`, retained
    `evidence/staging-walk/walk-63de8094.md`). Next: plan story item 6: label-first
    review with per-question retry, picture in review items and marks, the D44
    low-27 miss and the D31 Exam.net rubric test import.

- [ST-SKRIPT-39-06](docs/backlog/stories/st-skript-39-06-teacher-authoring-of-every-exam-net-question-type-with-parent-and-child-questions.md)
  `proposed`, P1-P16: seven types, parents with children, and (P14-P16,
  2026-10-13) changing a question's type plus "Gör om till [type]". Next: user
  proposed->ready; after story 8.

- Owner Dobby (session `a0e6b5f5`, retained `01a13559-bf2e-760d-a690-3a3dea446cd5`):
  TASK-SKRIPT-39-05-08 planning: D1-D3 closed (shared gap/free-text
  definition, D15 plus alternative-sentences rule, import fixes folded in), O1-O3
  open; replay evidence `evidence/import-replay/`. Next: suggestion accuracy as a
  scored gold-corpus eval metric (user decision 2026-10-13; not scaffolded).

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

- EPIC-SKRIPT-39 decisions 2026-10-09 (E13-E15): story 8 converges the exporter
  on the native QTI 3.0 Exam.net contract after story 5, QTI 2.1 is the parity
  baseline until cutover. Open: sir-convert branch
  `claude/supersede-retired-exam-epics` (EPIC-SIRCON-07/08 supersession notes)
  awaits merge and governed terminal closure.

- TASK-SKRIPT-REP-0035 passive web liveness is deployed in production and staging.
  Owner: skill-repository parent 01a1036b; next: terminal closeout.
  Published c282c74b; exact image 0ae40a8a34a2; full startup healthy; /healthz 200.
  34 focused tests passed; next natural checks 25.005 ms prod / 24.596 ms staging.
  Proof: task-worktree .artifacts/native-health/passive-\*-rollout-proof.json (2026-10-06).

- [EPIC-SKRIPT-40](docs/backlog/epics/epic-skript-40-shared-design-system-convergence.md)
  and ST-SKRIPT-40-01 are `active`. TASK-SKRIPT-40-01-01 is `done`
  (user closure 2026-10-12; review `bda00b6a`; Hemma staging walk passed at
  `fc42b918`, Skriptoteket retained session
  `01a13061-ff38-7099-aa3d-e23f6e5bba43` evidence/staging-walk). Next:
  TASK-SKRIPT-40-01-03 (shared action buttons), which TASK-SKRIPT-39-04-05
  waits on. TASK-SKRIPT-40-02-01 waits on TASK-SKILL-REP-0187. Open defect
  from the walk: Klassrumskartan returns focus to the sidebar, not "Ny klass",
  after the modal closes.
- ST-SKRIPT-40-03 (`proposed`): every screen onto the shared visual direction
  (rules removal: all of .codex/rules moves into skills, user 2026-10-12;
  shadow and panel sweep, per-app token passes).
  Retained plan in session `01a13082-a8f9-7137-aa65-848f7e3c53c2`; S1-S7
  closed. Release first (user 2026-10-12): skill-repository
  `TASK-SKILL-REP-0279` and HuleEdu `TASK-HULE-REP-0142` are done
  (0.1.24 without offset shadows, in repository-governance 0.11.109; HuleEdu
  staging walk clean). Next: this story's first task (not yet scaffolded)
  syncs 0.1.24 and removes local uses in the same commit, before
  TASK-SKRIPT-40-01-02 and 40-01-03. TASK-SKRIPT-39-04-05
  (`proposed`, contract C1-C25 incl. autosave; plan D1-D67 closed in session
  `01a13061-ff38-7099-aa3d-e23f6e5bba43`): frontend-only editor with drawers;
  waits on 40-01-03, the 0.1.24 sync, 39-04-06 (scaffold),
  39-04-08 (scaffold: Mina filer exports, pruning) and 39-05-08 (see Dobby entry).
  ST-SKRIPT-39-08 (metadata) is scaffolded.
  EPIC-SKRIPT-39 E16 and ST-SKRIPT-39-07 (`proposed`): DigiExam conversion
  becomes a secondary input mode of the workspace.

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

- TASK-SKRIPT-39-04-09 `done` 2026-10-13 (ruthless-reviewer approved
  `d09bd286`, user closure): merged main `c018ae9e`, deployed to staging;
  all seven walk steps passed, incl. resume after reload, older job ignored
  after save, import blocked while unsaved, `docx_import` log label, q10
  Fungi/Bacteria (retained `01a13559…/evidence/staging-walk-c018ae9e/README.md`).
- TASK-SKRIPT-39-04-07 `done` 2026-10-13 (user closure; user waived review
  of final repair `ace0cc39`, earlier rounds `changes_requested`): merged
  main `838baea9`; T7 staging walk passed: suggestion on unsaved edits ->
  `machine_proposed` key -> reviewed -> saved -> kept on reopen (retained
  `01a133f5…/evidence/staging-walk-838baea9/README.md`).
- TASK-SKRIPT-39-05-07 `done` 2026-10-13 (user closure): export blocks only on
  missing values; review approved `58dabe3f`; staging walk on ebc2a9c7 passed
  (retained `01a13274…/evidence/staging-walk-ebc2a9c7/`).
- Historical docs selector reads `docs/_meta/historical-docs-contract.yaml`
  (renamed in `1bcd4a38`); `test_historical_docs_validator.py` 3 passed.

- 2026-10-10: sir-convert-a-lot `main` pushed (`3fb6f672`) with the
  EPIC-SIRCON-07/08 supersession notes; their terminal closure is blocked
  on migrating both epics to the contract-derived profile with open child
  stories (user decision pending; ST-SIRCON-07-01 still states the old QTI
  2.1 claim).

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
