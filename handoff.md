## Current

- [TASK-SKRIPT-REP-0038](docs/backlog/tasks/task-skript-rep-0038-retire-repository-rules-and-route-staging-walks-to-staging-walk.md)
  `ready`, owner delegated Codex lead on `codex/task-skript-rep-0038`.
  D1-D2 live routing edits pass focused gates (2026-10-11; retained session
  `01a12706-566c-7480-acc3-427145283942`, captures 0426-0430).
  Rule deletion is blocked: migration hook demands replacements, contrary to D1.
  Next: parent resolves hook, delete rules, rerun gates, commit for review.

- [TASK-SKRIPT-REP-0040](docs/backlog/tasks/task-skript-rep-0040-retire-sir-convert-public-host-defaults-and-align-private-conversion-lanes.md)
  `in_progress`; owner Claude parent. `fix/retire-convert-references` at
  `d97caf5b` merged to main after the original reviewer approved the F1/F2
  repair (`evidence/reviews/TASK-SKRIPT-REP-0040/rereview-d97caf5b.md` in
  retained `01a13f9f-d6dd-7067-b581-efc395226538`). Next: closeout after the
  Hemma hold, with the staging env check. No SSH, deployment or live proof yet.
  Namecheap CNAME deletion stays with the user.

- [ST-SKRIPT-08-36](docs/backlog/stories/st-skript-08-36-klassrumskartan-tutorial-clips-in-hj%C3%A4lp-with-a-first-use-dialog.md)
  Klassrumskartan tutorial clips in Hjälp. Owner: Claude parent (Hemma);
  retained `01a13d03-cc0c-731e-a9e5-b3d536821e55`. Task 01 (walking skeleton)
  `done` 2026-10-15: reviews `8576afb7`/`3c95199d`, main `03ba322d`; walk 2 on
  staging passed all five steps (`evidence/staging-walk-prep-b8e43394/walk-2-2026-10-15/WALK.md`).
  Task 02 (Hjälp at 1024 px) `done` `ff25a484`; TASK-SKRIPT-REP-0039 canceled as
  its duplicate. Draft Klass clip (synthetic timing) on dev media. Next: real
  clips wait on HuleFilm ST-VIDEO-12-01 gates (talmanus approval in progress,
  ElevenLabs draft spend, render approval, prod media deploy). Talmanus review
  package retained at `evidence/talmanus-review-package-2026-10-15/` (sent 2026-10-15).
  Guide Steg 1 point 3 (paste parses any format) is wrong: only file import
  parses Skola24; correction and `generate-planner-help` regen still pending.

- [TASK-SKRIPT-06-17-01](docs/backlog/tasks/task-skript-06-17-01-resolve-merge-revision-parents-in-the-migration-idempotency-support.md)
  `proposed`: idempotent migration suite fails on merge revision `6a1e9d3c4b7f`
  (pre-existing on main); found during ST-SKRIPT-08-36 review repair.

- [TASK-SKRIPT-39-05-14](docs/backlog/tasks/task-skript-39-05-14-exam-header-lines-become-document-metadata-and-question-headings-stay-with-their-questions.md)
  reopened `in_progress` 2026-10-16 (user; story ST-SKRIPT-39-05 stays `ready`;
  retained `01a144e3-b8c4-7ea5-bee6-6dfc5e242786`). Owner: Claude parent on the
  Mac. Walk and Exam.net 5344745 passed (`evidence/staging-walk-39-05-14b/`);
  next: Sol pair repairs five main test failures, Sol review, then closure.
  Still failing on main `212ce386` (lead 39-08-01, 2026-10-16), introduced by
  this task's merges: `test_exam_workspace_source_formatting.py` 2 failed
  (Svenska 2 `Fråga 17` missing after replay; morpheme alignment), 2 QTI
  reference mismatches in `test_exam_conversion_parity.py` and, since
  `827c301a`, `test_exam_workspace_docx_grid_points_review.py` (MATCHING vs
  FREE_TEXT). Pre-existing and unowned: docker suite
  `test_exam_workspace_docx_background.py` 2/9 fail on main and at `8bb83759`.
  Evidence `01a145b6.../evidence/lead/*-on-main-2026-10-16.md`.
- [TASK-SKRIPT-39-08-01](docs/backlog/tasks/task-skript-39-08-01-course-picker-at-import-and-exam-metadata-drawer-for-course-title-and-file-name.md)
  `in_progress` 2026-10-16; owner Claude parent on Hemma (session
  `704dc5a5`), retained `01a145b6-c404-761f-aeef-39de058ba7ca`, worktree
  `skriptoteket-task-skript-39-08-01` from `9322879c`. Committed after
  review: U1 `2b29faea`, U2 `b3361de8`, U3 `5409fb07`, U4 `6bc3732e`, U5
  `2a9589f2`, slice mocks `3203b507`, docs `0505b89e` (tasks 2-4 `ready`),
  merge of main `fd0469a6`. Approved, uncommitted in the worktree: U5R3,
  U6 (header course, drawer), U7 (course line in exports), U2R2 (vault
  fake). Next: commit, staging walk, user closure gate, merge into main.

- [ST-SKRIPT-39-06](docs/backlog/stories/st-skript-39-06-teacher-authoring-of-every-exam-net-question-type-with-parent-and-child-questions.md)
  `proposed`, P1-P17, tasks 1-6; follows ST-SKRIPT-39-09.

- [TASK-SKRIPT-REP-0037](docs/backlog/tasks/task-skript-rep-0037-multi-file-script-bank-tool-bundles-and-the-split-of-four-over-long-tools.md)
  `in_progress`, owner Codex (handed over by the Claude exam parent 2026-10-11).
  D6 (every bundle file shown and saved) rereview approved `578d4a4d`, merged
  `4b68bcde`, pushed; staging `skriptoteket-dev` rebuilt on it, Gruppgenerator run
  done. Production was deployed and seeded by mistake: gruppgeneratorn depublished,
  other seeded tools unpublished. Staging grants `skriptoteket-proof-user`
  contributor role and gruppgeneratorn maintainership. Next: staging editor walk
  (edit sibling `grouping.py`, sandbox run, save), record proof, close docs. UX
  note: a saved class list is not selected in step 2 until the class name is filled.

- [TASK-SKRIPT-REP-0036](docs/backlog/tasks/task-skript-rep-0036-resolve-mina-filer-app-export-labels-from-the-app-id-prefix.md)
  `ready` (user 2026-10-11); label behaviour user-witnessed; F1/F2 repaired, Sol
  rereview approved `0f17cc78`, merged `61cce3ac`. Next: user closure. Mina filer
  keeps every workspace version visible by user choice; head-only listing is later.

- TASK-SKRIPT-REP-0035 passive web liveness deployed in production and staging
  (c282c74b, image 0ae40a8a34a2, /healthz 200). Owner skill-repository parent 01a1036b; next: terminal closeout.
  34 focused tests passed; next natural checks 25.005 ms prod / 24.596 ms staging.
  Proof: task-worktree .artifacts/native-health/passive-\*-rollout-proof.json (2026-10-06).

- [EPIC-SKRIPT-40](docs/backlog/epics/epic-skript-40-shared-design-system-convergence.md)
  and ST-SKRIPT-40-01 are `active`. TASK-SKRIPT-40-01-01 is `done` (user
  closure 2026-10-12; review `bda00b6a`; Hemma walk `fc42b918`, retained
  `01a13061-ff38-7099-aa3d-e23f6e5bba43` evidence/staging-walk). Next:
  TASK-SKRIPT-40-01-03 (shared action buttons), which TASK-SKRIPT-39-04-05
  waits on. TASK-SKRIPT-40-02-01 waits on TASK-SKILL-REP-0187. Open defect
  from the walk: Klassrumskartan returns focus to the sidebar, not "Ny klass",
  after the modal closes.

- ST-SKRIPT-40-03 (`proposed`): every screen onto the shared visual direction
  (rules removal into skills, user 2026-10-12; shadow and panel sweep, per-app
  token passes). Retained plan `01a13082-a8f9-7137-aa65-848f7e3c53c2`, S1-S7
  closed. Release first (user 2026-10-12): skill-repository
  `TASK-SKILL-REP-0279` and HuleEdu `TASK-HULE-REP-0142` are done
  (0.1.24 without offset shadows, in repository-governance 0.11.109; HuleEdu
  staging walk clean). Next: this story's first task (not yet scaffolded)
  syncs 0.1.24 and removes local uses in the same commit, before
  TASK-SKRIPT-40-01-02 and 40-01-03. TASK-SKRIPT-39-04-05
  (`proposed`, contract C1-C25 incl. autosave; plan D1-D67 closed in session
  `01a13061-ff38-7099-aa3d-e23f6e5bba43`): frontend-only editor with drawers;
  waits on 40-01-03, the 0.1.24 sync, 39-04-06 (scaffold),
  39-04-08 (scaffold: Mina filer exports, pruning); 39-05-08 is done.
  EPIC-SKRIPT-39 E16 and ST-SKRIPT-39-07 (`proposed`): DigiExam conversion
  becomes a secondary input mode of the workspace.

- Historical 2026-09-05 workspace planning (EPIC-SKRIPT-39 E8-E12, ADR-SKRIPT-0091,
  ST-SKRIPT-39-04): `.codex/long-term-memory/entries/session-2026-09-05-epic-39-handoff-compaction.md`.

- [TASK-SKRIPT-39-03-03](docs/backlog/tasks/task-skript-39-03-03-retire-the-sir-convert-exam-specific-integration.md)
  and [TASK-SKRIPT-39-03-04](docs/backlog/tasks/task-skript-39-03-04-retire-the-hemma-qwen-answer-key-sidecar.md)
  are `done` (2026-09-30, independent reviews approved). Linked Sir
  TASK-SIRCON-07-04-01/REP-0030 and Hule TASK-HULE-01-04-13/REP-0130 are done.
  Sir Convert production and STT stay offline by user decision; the
  Skriptoteket answer-key env keys (Luna/GLM) stay.

- [TASK-SKRIPT-39-02-03](docs/backlog/tasks/task-skript-39-02-03-repair-partial-digiexam-answer-key-enrichment-and-prove-the-real-integrated-vertical.md)
  `done` (rereview approved `e877170d`, main `52ccc0a2`; D5 browser walk on
  staging passed 2026-09-30 at `e3ae9527`; evidence session
  `01a0f227-63b9-7435-8013-5f556eaf4905`). Required predecessor for the DOCX
  skeleton.

- [TASK-SKRIPT-39-01-03](docs/backlog/tasks/task-skript-39-01-03-degrade-unknown-digiexam-question-types-to-reviewable-free-text.md)
  stays canceled; Exam.net acceptance stays user-owned. Dated parity proof is
  retained in the 2026-09-05 archive above.

- [ST-SKRIPT-39-02](docs/backlog/stories/st-skript-39-02-port-the-remote-answer-key-completion-line-with-a-daily-token-lease.md)
  is `done` and independently `VERIFIED`; exact proof is in the archive above.

- [EPIC-SKRIPT-39](docs/backlog/epics/epic-skript-39-skriptoteket-owned-exam-conversion.md)
  and [ADR-SKRIPT-0090](docs/decisions/adr-skript-0090-skriptoteket-owned-exam-conversion-boundary-with-sir-convert-generic-extraction.md)
  stay approved; ADR-0091 (`proposed`) narrows the authoring-UI non-decision.
  Active story/task pointers above hold the current DOCX and QTI state.

- Completed REP/ST-38 outcomes and evidence are in the 2026-09-05 archive above.

## Recent

- [ST-SKRIPT-39-09](docs/backlog/stories/st-skript-39-09-qti-3-0-native-export-for-exam-net.md)
  `done` 2026-10-16: QTI 3.0 for both lanes plus Exam.net routes, tasks 1-9;
  last proofs Exam.net 5339805 (formatting) and 5339836 (section headings);
  follow-up 26c56a03.

- 2026-10-13 `done`: TASK-SKRIPT-39-04-09 (main `c018ae9e`), 39-04-07 (`838baea9`),
  39-05-07 (`ebc2a9c7`); walk records are cited in each task's closeout.

- Historical docs selector reads `docs/_meta/historical-docs-contract.yaml`
  (renamed in `1bcd4a38`); `test_historical_docs_validator.py` 3 passed.

- 2026-10-10: sir-convert-a-lot `main` pushed (`3fb6f672`) with the
  EPIC-SIRCON-07/08 supersession notes; their terminal closure is blocked
  on migrating both epics to the contract-derived profile with open child
  stories (user decision pending; ST-SIRCON-07-01 still states the old QTI
  2.1 claim).

## Facts

- Session Date: 2026-10-15
- Last Refreshed: 2026-10-15
- Current docs validate with `pdm run docs-validate`.
- Historical terminal docs audit separately with `pdm run python -m scripts.historical_docs.validate_historical_docs`.
- Full typecheck passed 2026-10-15: backend (1,588 source files) and SPA;
  TASK-SKRIPT-REP-0040 retained capture `0004-pdm-run-typecheck`.
- Open product questions (undecided, not silently resolved): native doc
  format internals (new versioned doc type vs file-plus-sidecar state);
  deferred scanned-PDF behavior (hard-fail with guidance vs generic
  extraction queue); digital-PDF slice detail follows ST-39-04 review.
- Next: eval triage, item-type and parent/child authoring planning.
- Tutorial media: web serves `MEDIA_ROOT` read-only at `/static/media` (404 while absent); dev bind `/home/paunchygent/apps/skriptoteket-media/dev`, prod bind inert until `hemma-deploy`.
