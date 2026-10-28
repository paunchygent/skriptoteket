## Current

- Hemma orchestrator (Claude desktop SSH session, cwd `~/apps/skriptoteket`), 2026-10-28.
  User priority order of 2026-10-28; all Kodredigerare (script editor) tasks are deferred:
  REP-0037, 41-03-02, 41-03-03.

  - Production: Skriptoteket `50a7b84e3`; HuleEdu `f59ea3b61`. Main is ahead of production
    (40-04-26, 40-02-01, 41-02-07 with migration `f2b9c4d8a701`, 39-10-03, REP-0052/53/54,
    26-06-01, 09-07-01); no production deploy was asked for.
  - USER GATE before the next Skriptoteket production deploy (09-07-01, `1f3f84f9f`):
    production startup now refuses loopback `ALLOWED_HOSTS`, and the production `.env`
    (`~/apps/skriptoteket/.env:74`) still holds `localhost,127.0.0.1,::1`. Set
    `ALLOWED_HOSTS=skriptoteket.hule.education` there first, or web and worker will not start.
  - Staging runs `40d8fc931` (Mac 26-06-01 share-link walk on it). If `hemma-dev start` says
    "container with given ID already exists", stop the orphaned process (postgres with SIGINT),
    remove `/run/user/1000/docker/runtime-runc/moby/<id>` dirs whose init PID is dead, start again.
  - In flight: 39-06-11 (ordering inside a part at 1 point; lead on its worktree, ST-39-06
    stays open), REP-0056 (backlog leftovers; lead on its worktree), 26-06-01 (closes on the Mac
    walk), 09-07-01 (closes on a live staging check at the next rebuild). REP-0024 and
    27-09-04 need a repair task (REP-0024 review is changes_requested).
  - Story closeout waiting: 39-10 (every task is done; no proof-set walk is on record).

- [ST-SKRIPT-08-36](docs/backlog/stories/st-skript-08-36-klassrumskartan-tutorial-clips-in-hj%C3%A4lp-with-a-first-use-dialog.md)
  Klassrumskartan tutorial clips: tasks 01 and 02 `done`; guide Steg 1 corrected on main
  2026-10-28. Real clips wait on HuleFilm ST-VIDEO-12-01 gates (talmanus approval,
  ElevenLabs spend, render approval, prod media deploy); the Steg 1 clip script still shows
  a Skola24 paste. Retained `01a13d03-cc0c-731e-a9e5-b3d536821e55`.

- [TASK-SKRIPT-REP-0037](docs/backlog/tasks/task-skript-rep-0037-multi-file-script-bank-tool-bundles-and-the-split-of-four-over-long-tools.md)
  `in_progress`, deferred by the user 2026-10-28. Next when resumed: staging editor walk
  (edit sibling `grouping.py`, sandbox run, save). Production gruppgeneratorn is depublished.

- Exam epics 39/40/41 working model (user decisions G1-G30 of 2026-10-17, retained
  `01a1495e-8398-75be-b2da-f0b08ba11afa`): walk only exam-converter changes; restyle and
  repairs close on approved review plus unit tests. The Hemma orchestrator runs leads,
  merges, pushes and rebuilds staging; the Mac thread walks staging and Exam.net. Exam.net
  takes QTI; the print PDF renders the DOCX house template. Historical planning:
  `.codex/long-term-memory/entries/session-2026-09-05-epic-39-handoff-compaction.md`.

## Recent

- 2026-10-28 `done`: 39-10-03 (a failed import's message wraps in full, main `ec810361f`) and
  39-06-09 (ordering inside a part probed in Exam.net, main `c0112dfdc`).

- 2026-10-28 `done` (REP-0055 lead, branch `codex/task-skript-rep-0055`): 24 tasks closed
  on merge evidence, 10 tasks and ST-21-04 canceled, 25-06-14 partly canceled, 10 items
  deferred, stories 06-17, 06-18, 39-01, 39-04, 40-02, 40-04 closed, EPIC-SKRIPT-20 active;
  26-06-01 (D4) and 09-07-01 (D5) record their decisions and stay open.

- 2026-10-28 `done` (Hemma orchestrator): 40-04-26 type switch and AI toolbar (`23309e478`),
  40-02-01 icons (`1b2ce75cc`), 39-04-24 rising count, 39-06-08 ordering, 40-04-09 and
  REP-0048 (R14 keeps position numbers, user), 39-01-02 (Mac walks
  `.artifacts/staging-walk-05b3fc12a/walk-record.md`); 41-02-07 claim per draft_id
  (`a5aa760c6`); REP-0052 image PDM pin, REP-0053 Docker replay, REP-0054 ordering step;
  39-04-20; HuleEdu REP-0149 deploy-check SIGPIPE and REP-0148 export download.

- 2026-10-28 `done`: TASK-SKRIPT-REP-0040 Sir Convert public-host retirement (rereview
  `d97caf5b` approved, main `ced7971b`; env check in retained `01a18444`). The user deleted the CNAME (NXDOMAIN).

- 2026-10-22 `done`: 41-03-01 AI for every signed-in teacher (Mac walk
  `.artifacts/staging-walk-41-03-01-78765d330/walk-record.md`); in production at `976d89b5b`.

- 2026-10-22 `done`: 39-04-23 import phases and live signal (retained `01a1639f`; Mac re-walk
  `.artifacts/staging-walk-rewalk-8569092ba/walk-record.md`; production `8569092ba`).

- 2026-10-22 `done`: 41-01-02 script editor on Luna and Sol through the door, and ST-SKRIPT-41-01
  (Mac re-walk `.artifacts/staging-walk-rewalk-8569092ba/walk-record.md`; production `8569092ba`).

- 2026-10-22 `done`: 41-01-04 AI capacity and try-again (`d44e946b5`; review F1-F8, retained
  `01a16352`; Mac walk `.artifacts/staging-walk-41-01-04-d44e946b5/walk-record.md`). HuleEdu door
  14-03-04/05/06 on main `ca7ff9700` (overage, gpt-6.1-sol price, cache writes, backlog 2048);
  deployed to production 2026-10-22.

- 2026-10-22 `done`: 39-04-22 Word drawn shapes as pictures, shapes kept
  for Word export (`74eeceb2d`; review F1-F9 repaired on fail-first proof, retained
  `01a162df`; Mac walk `.artifacts/staging-walk-39-04-22-74eeceb2d/walk-record.md`).
  Follow-up `cae867222`: Word export writes compatibilityMode 15, no Compatibility
  Mode; Mac walk `.artifacts/staging-walk-39-04-22-cae867222/walk-record.md` also
  moved a Q6 box and edited a label by hand in Word.

- 2026-10-22 `done`: 39-10-02 PDF pictures and figures (`7adde567`; Mac walk
  `.artifacts/staging-walk-39-10-02-7adde567c/walk-record.md`; Word drawn
  shapes go to TASK-SKRIPT-39-04-22, ready).

- 2026-10-22 `done` on main: TASK-SKRIPT-40-04-05, 40-04-12 and 39-04-11 (user closure; Mac walk `.artifacts/staging-walk-owed-2026-10-22/walk-record.md`). 39-10-01 PDF import done (walk `.artifacts/staging-walk-39-10-01/walk-record.md`). 40-04-19 done (two-tab fix; 403-message half dropped by the user). 41-01-03 exam AI through the door done (`fe2bc9b9` + D1 `2d16c24d`; HuleEdu staging door key `547e1deb`; B4 notes unit-proof only). REP-0049 done (`b8293abd`; Mac walk `.artifacts/staging-walk-overnight-fe2bc9b9/walk-record.md`). 39-10-04 Lägg till bild done (`4f555442` + W1 `e68e84a1`; Mac walks passed, check 4 re-walk at `fe2bc9b9`).

- 2026-10-22 `done` on main: TASK-SKRIPT-40-04-21, 40-04-23, 39-07-03, 39-04-12, 40-01-04, 06-18-01, REP-0036 and ST-SKRIPT-39-07, 41-02, 40-01 (user closure; Mac walks `.artifacts/staging-walk-closure-ede1ea0d/walk-record.md`). Mina filer keeps every workspace version visible by user choice; head-only listing is later.

- 2026-10-28 `done`: TASK-SKRIPT-REP-0035 passive web liveness (user closure, review waived in D8;
  rollout proof in the task doc; raw receipts no longer on Hemma).

- 2026-10-21 `done` on main: [TASK-SKRIPT-REP-0050](docs/backlog/tasks/task-skript-rep-0050-backend-pytest-runs-parallel-and-quiet-by-default-and-serial-runs-need-a-stated-reason.md) parallel and quiet pytest (merge `6a557b5d`; review 321854a9 F1-F6 medium repaired `b1f019e6`, admitted on focused proof).

- 2026-10-20 `done` on main: TASK-SKRIPT-40-04-20 print keeps imported formatting (`43f47eda`, user closure; Mac walk `.artifacts/staging-walk-e4d15c4a/walk-record.md`). Unreadable-notice wrap fix merged `a8de9ae6` (Pi review `ec4f5dae` approved; walk PASS).

- 2026-10-20 `done` on main: TASK-SKRIPT-41-02-06 unreadable exam files (`0ab8ccb8`, user closure; Mac walk `.artifacts/staging-walk-e4d15c4a/walk-record.md`).

- 2026-10-20 `done` on main: TASK-SKRIPT-40-04-13 and -14 gap lane (merge `f84eb85d`, rereview 12 approved, Mac step 5 re-walk PASS; user closure).

- 2026-10-28 `done`: TASK-SKRIPT-REP-0038 repository rules retired (`eee397e31`, 40-03-09) and
  the Mac-local shared-auth lane removed (`e559cae0e`); orchestrator closure, no review.

- 2026-10-20 `done` on main: TASK-SKRIPT-06-17-02 migration tests pinned to their own revision, plus the pre-push migration stage (`3d3f867a`, user closure; the stage ran on its first push, 118 passed). TASK-SKRIPT-06-17-01 canceled as superseded by it.

- 2026-10-20 `done` on main: TASK-SKRIPT-39-05-16 unused long-form readiness copy deleted (`5611f0c8`, user closure).

- 2026-10-20 `done` on main: TASK-SKRIPT-41-02-05 guest draft handover to Mina filer (`8be9aefa`, user closure; Mac walk `.artifacts/staging-walk-e4d15c4a/walk-record.md`). Follow-ups D10, D24 in Current.

- 2026-10-20 `done` on main: TASK-SKRIPT-39-05-15 type choice on an unconverted question (`e4d15c4a`, user closure; Mac walk `.artifacts/staging-walk-e4d15c4a/walk-record.md`).

- 2026-10-19 `done` on main: TASK-SKRIPT-39-04-21 points wording (`99378586`, user closure; Mac walk `.artifacts/staging-walk-99378586/walk-record.md`). U4 offer line parked.

- 2026-10-19 40-04-11 control system `canceled` as superseded by 40-04-17 (user decision; no product code). The docs-only branch `codex/task-skript-40-04-compact-tools-remote` holds the reuse list (task section "Superseded by TASK-SKRIPT-40-04-17"); the inventory and mocks are in root 01a15383.

- 2026-10-19 `done` on main: 40-04-07 writing areas (staging walk at `003c874a`, Mac `.artifacts/staging-walk-40-04-07/evidence/walk-record.md`), 41-02-01 QTI import, 39-04-15, 39-04-16, 39-04-17, REP-0047, HULE-14-03-01, 39-04-19 Del A left-out repair, REP-0046 re-recorded omprov labeler calls, 39-04-18 facit carry-over, 39-04-20 score field (closed 2026-10-28 on the K7 walk). Pre-push hook SIGPIPE false skip fixed (`003c874a`).

- 2026-10-10: sir-convert-a-lot `main` pushed (`3fb6f672`) with the
  EPIC-SIRCON-07/08 supersession notes; their terminal closure is blocked
  on migrating both epics to the contract-derived profile with open child
  stories (user decision pending; ST-SIRCON-07-01 still states the old QTI
  2.1 claim).

## Facts

- Session Date: 2026-10-15
- Last Refreshed: 2026-10-28
- Pushing `main` runs the full `pdm run typecheck` and `pdm run test` on Hemma first (`scripts/hemma_pre_push_check.sh`, pre-push hook; install with `pre-commit install --hook-type pre-push`). Run the push in the background; a failure blocks it, on Hemma the steps run directly with no ssh, an unverifiable push is blocked, Markdown-only commits reuse the last pass.
- Current docs validate with `pdm run docs-validate`.
- Flunk-Out Frenzy donor work never flattens a richer donor object into local bounds or a
  "good enough" approximation; the rule text is in
  `data/pinball_resources_and_repos/vpw-rom-example-table-donor-map.md` and the
  `pinball-board-authoring` skill.
- Historical terminal docs audit separately with `pdm run python -m scripts.historical_docs.validate_historical_docs`.
- Full typecheck passed 2026-10-15: backend (1,588 source files) and SPA;
  TASK-SKRIPT-REP-0040 retained capture `0004-pdm-run-typecheck`.
- Open product questions (undecided, not silently resolved): native doc
  format internals (new versioned doc type vs file-plus-sidecar state);
  digital-PDF slice detail follows ST-39-04 review.
- Next: eval triage, item-type and parent/child authoring planning.
- Tutorial media: web serves `MEDIA_ROOT` read-only at `/static/media` (404 while absent); dev bind `/home/paunchygent/apps/skriptoteket-media/dev`, prod bind inert until `hemma-deploy`.
