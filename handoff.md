## Current

- [TASK-SKRIPT-REP-0038](docs/backlog/tasks/task-skript-rep-0038-retire-repository-rules-and-route-staging-walks-to-staging-walk.md)
  `ready`, owner delegated Codex lead on `codex/task-skript-rep-0038`.
  D1-D2 live routing edits pass focused gates (2026-10-11; retained session
  `01a12706-566c-7480-acc3-427145283942`, captures 0426-0430).
  The 22 rule files are deleted on main by TASK-SKRIPT-40-03-09 (facts folded into
  skills). Next: the REP-0038 owner reconciles its remaining D1-D2 scope against that.

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

- Plan 2026-10-17 (user decisions G1-G30, lead L1-L9; retained
  `01a1495e-8398-75be-b2da-f0b08ba11afa` evidence/planning/decisions-2026-10-17.md).
  Owner: Mac Opus parent, root `01a149c9-5bc7-7713-ba64-12dee0470bdd`. Rules: walk
  only exam-converter changes, once per wave; restyle and repairs close on approved
  review plus unit tests. Wave 2 is closed (Recent).
  2026-10-18 on main: TASK-SKRIPT-40-04-03 `done` (merge 10eef9fd, staging walk
  passed, root 01a149c9 evidence/staging-walk-10eef9fd/); REP-0043 `done`; 39-06-02
  `done`; ordering TASK-SKRIPT-39-06-08 `in_progress` (Mac Opus lead 58ebedec, worktree Skriptoteket-task-skript-39-06-08, root 01a14c27); tutorial
  video focus fix 39230851.
  Next lanes: 39-07-03 retire old converter routes (40-04-03 now on main); implement
  39-06-08 ordering; stories 39-04, 39-06, 39-07 await closeout.
  Ready (user grilling 2026-10-18, plans in root 01a14c27): 40-04-04 dropdown option editor, 40-04-05 export names from the exam title, 39-06-09 Exam.net probe of ordering inside a part.
  39-06-10 lead 146bc2d8, both from a0a81ab5a; 39-06-10 ruling: a question moved out lands after its part.
  40-04-07 ruling (user 2026-10-18): print PDF renders the DOCX house template; Exam.net import PDF is a fallback only; QTI is the Exam.net route.
  RESUMED 2026-10-19 after the 2026-10-18 account switch: Mac parent session 0d4e482f integrates and pushes; Hemma orchestrator is desktop SSH session local_42174b78 (cwd ~/apps/skriptoteket), briefed to resume every lane below with fresh leads. Roster is identical on Mac and Hemma (routes.toml byte-identical, skill-repository 1a22d64e): juniors OpenCode Spark 1.3 high (`junior-route` default `spark`), task-monitor/researcher OpenCode deepseek-v4.1-flash-free, explorers Haiku, leads Opus 5.5 (no code, never reused across tasks), reviews Pi Sol 6.1. Exam.net has no QTI export (UI + help center checked 2026-10-19): 41-02-01 uses a Skriptoteket package Exam.net accepted as its fixture. Lanes (Hemma branch @ head: next):

  - 40-04-08 (gap/short-answer editor, click-a-word gaps, popover): lead on Hemma; its Mac staging walk also covers the owed 40-04-04 walk, then close 40-04-04.
  - 39-04-20 score field (lone "/" from "/4 p"): in review; user accepted the whitespace side effect (corrected counts to confirm). 40-04-09 gap tool: plan awaits user acceptance. 40-04-10 points banner: user chose list A and grey-number dismiss as the prominent primary action; dismiss label open. 40-04-11 glyph-only tools: four user questions open (mockups shown).
  - 41-02-02: merged to main (review approved, b9b3e6a9); next Mac guest staging walk (ST-SKRIPT-41-02), then close. Production deploy with nginx-proxy fixed IP 172.18.255.10 and `TRUSTED_PROXY_CIDRS=172.18.255.10/32` is a USER GATE (restarts shared nginx-proxy).
  - REP-0048: 6 Exam.net walk checks (Mac walk).
  - 41-02-04 workspace width (proposed): lead bd0f1693 planned it on branch `codex/task-skript-41-02-workspace-width-remote`. Root cause: LandingLayout's 1040 px frame. Next: the user answers Q1-Q5 (drawer, list and preview widths, editor line length, resize) in plan `01a153bf.../evidence/planning/TASK-SKRIPT-41-02-04/plan.md`.
  - HuleEdu after HULE-14-03-01: 41-01-03, 41-01-02, 41-01-04; http_runtime workers repair.
    Hemma Opus lead `3b164d53`: 40-03-01..09 and 08-36-02 `done`; 40-02-01 tranche 1 on
    main 761b1b59, tranche 2 a67afa90 (`in_progress`: shared `play` meaning in
    session add-a-shared-play-glyph, exam-held wrappers and lucide removal open).

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

- 2026-10-19 `done` on main: 40-04-07 writing areas (staging walk at `003c874a`, Mac `.artifacts/staging-walk-40-04-07/evidence/walk-record.md`), 41-02-01 QTI import, 39-04-15, 39-04-16, 39-04-17, REP-0047, HULE-14-03-01, 39-04-19 Del A left-out repair, REP-0046 re-recorded omprov labeler calls, 39-04-18 facit carry-over. Pre-push hook SIGPIPE false skip fixed (`003c874a`).

- Wave 2 closed 2026-10-17 at `agent-overseer:approved-review-closeout`:
  39-04-06, 39-04-08, 39-04-10, 39-06-03, 39-06-04, 39-06-05, 39-06-07, 39-07-01,
  39-07-02, 40-04-02 (`baf1e2e7`) and 39-06-06 on tests by user ruling (`69c0610b`).
  Staging and Exam.net proof at main `1f9e4367` (exam 5345261):
  `01a149c9.../evidence/staging-proof-1f9e4367/proof.md`.

- [TASK-SKRIPT-40-03-10](docs/backlog/tasks/task-skript-40-03-10-adopt-huleedu-integrated-0-1-30-and-make-delete-and-edit-actions-glyph-only-across-skriptoteket.md)
  `done` 2026-10-17 (approved review): huleedu-integrated 0.1.30, delete and
  edit controls glyph-only and frameless (0.1.31), roomier school forms; main `e5ab32c6`.

- 2026-10-17 hooks: `precommit-install` now runs the package installer
  `repository-governance-hooks-install` (TASK-SKILL-REP-0321, runtime 0.11.134),
  so an install from a task worktree keeps the shared hook on the primary
  `.venv`; repository-governance pin 0.11.134 (`70bbfefd`, binding `6363b36e`).

- [TASK-SKRIPT-REP-0042](docs/backlog/tasks/task-skript-rep-0042-repair-the-two-failing-docker-suite-tests-in-the-docx-background-job-proof.md)
  `done` 2026-10-17 (approved review): the docker DOCX job proof asserts the
  formatting diagnostics contract; one live recording answers the bf26 typed
  type-conflict resend; replays require a recording per build request; main
  `ef8cd6ea`, docker suite 9/9; review `01a148db.../evidence/review-rep0042.md`.

- [ST-SKRIPT-39-05](docs/backlog/stories/st-skript-39-05-ai-first-docx-exam-conversion-with-a-gold-corpus-eval-loop.md)
  and [TASK-SKRIPT-39-05-14](docs/backlog/tasks/task-skript-39-05-14-exam-header-lines-become-document-metadata-and-question-headings-stay-with-their-questions.md)
  `done` 2026-10-17 (user closure): the five main test failures are repaired
  (R1, R1F, R1G; D15 split-question review; rereview2 approved), main
  `d92b828e`; staging walk and Exam.net 5344901 passed; retained
  `01a144e3.../evidence/staging-walk-39-05-14c/`; worktree retired.

- [TASK-SKRIPT-REP-0041](docs/backlog/tasks/task-skript-rep-0041-repair-ten-main-test-failures-in-worker-healthchecks-the-compose-contract-and-alignment-timing.md)
  `done` 2026-10-17 (approved review): healthcheck tests use the real
  `timeout`, compose contract tests track the native worker healthcheck, the
  host-dependent repair6 timing test is deleted; main `23fc5cf0`; reviews in
  `01a146ac.../evidence/`.

- [ST-SKRIPT-39-08](docs/backlog/stories/st-skript-39-08-course-and-tag-metadata-for-saved-exams.md)
  `done` 2026-10-17 (user closure gate), tasks 1-5 `done`; epic summary
  updated. Story check: list grouping and sort preference on staging
  `d31e939a` (`01a14b79.../evidence/staging-list-check/CHECK.md`); tags from
  the wave-2 walk; task evidence in each task's closeout. Worktree retired.

- [ST-SKRIPT-39-09](docs/backlog/stories/st-skript-39-09-qti-3-0-native-export-for-exam-net.md)
  `done` 2026-10-16: QTI 3.0 for both lanes plus Exam.net routes, tasks 1-9;
  last proofs Exam.net 5339805 (formatting) and 5339836 (section headings);
  follow-up 26c56a03.

- Historical docs selector reads `docs/_meta/historical-docs-contract.yaml`
  (renamed in `1bcd4a38`); `test_historical_docs_validator.py` 3 passed.

- 2026-10-10: sir-convert-a-lot `main` pushed (`3fb6f672`) with the
  EPIC-SIRCON-07/08 supersession notes; their terminal closure is blocked
  on migrating both epics to the contract-derived profile with open child
  stories (user decision pending; ST-SIRCON-07-01 still states the old QTI
  2.1 claim).

## Facts

- Session Date: 2026-10-15
- Last Refreshed: 2026-10-19
- Pushing `main` runs the full `pdm run typecheck` and `pdm run test` on Hemma first (`scripts/hemma_pre_push_check.sh`, pre-push hook, ~10 min; install with `pre-commit install --hook-type pre-push`). Run the push in the background; a failure blocks it, unreachable Hemma warns, Markdown-only commits reuse the last pass.
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
