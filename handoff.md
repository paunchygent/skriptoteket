## Current

- 39-04-24 `in_progress`, owner Codex `01a1647b`: production deployed 2026-10-22
  at Skriptoteket `50a7b84e3`, paired HuleEdu door `9d4ae61f9`; readiness passed.
  Batch16; AI output received stays separate from saved/editable status.
  Pi implemented; Opus5.5 reviewed; medium repairs admitted on focused proof.
  Next: MacBook parent walks Word/PDF. Retained `01a1647c-736c-7c8c-827d-c8b616ccb074`,
  evidence/implementation/production-release.md and macbook-walk-handoff.md.

- 41-02-05 follow-up (unscheduled): D24 a server claim per draft_id.

- Hemma orchestrator 2026-10-22:

  - Production runs `976d89b5b` (deployed 16:2x UTC by user decision; AI open to every
    signed-in teacher; migration `aa30c309b36c`; seating gate and /healthz green). HuleEdu prod
    runs `4e5b010c2` (door: skriptoteket 20% small, 10% full, no USD ceiling). HuleEdu prod `.env` still holds a stale
    `LLM_PROVIDER_SERVICE_USE_MOCK_LLM=true` (compose pins "false").
  - HuleEdu TASK-HULE-09-02-02 done (`a9e6eeaa`): boot startup installed, ntfy
    reaches the phone, Healthchecks check "Hemma" up with receipt verified (`4d8ebe9d`).
  - Next lead: 39-10-03 needs the user's "start 39-10-03" here.

- Hemma orchestrator (2026-10-21, retained `01a15f48-0f71-77ba-b7df-f48c8e838efb`):
  all 82 Hemma task and verify worktrees hold no work missing from main
  (survey in that root's `evidence/admission/`); removal waits on user approval.

- [TASK-SKRIPT-REP-0038](docs/backlog/tasks/task-skript-rep-0038-retire-repository-rules-and-route-staging-walks-to-staging-walk.md)
  `ready`, owner delegated Codex lead on `codex/task-skript-rep-0038`.
  D1-D2 live routing edits pass focused gates (2026-10-11; retained session
  `01a12706-566c-7480-acc3-427145283942`, captures 0426-0430).
  The 22 rule files are deleted on main by TASK-SKRIPT-40-03-09 (facts folded into
  skills). Next: the REP-0038 owner reconciles its remaining D1-D2 scope against that.
  The branch is absent on Hemma (2026-10-21), so the owner pointer is stale.

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

- [TASK-SKRIPT-REP-0037](docs/backlog/tasks/task-skript-rep-0037-multi-file-script-bank-tool-bundles-and-the-split-of-four-over-long-tools.md)
  `in_progress`, owner Codex (handed over by the Claude exam parent 2026-10-11).
  D6 (every bundle file shown and saved) rereview approved `578d4a4d`, merged
  `4b68bcde`, pushed; staging `skriptoteket-dev` rebuilt on it, Gruppgenerator run
  done. Production was deployed and seeded by mistake: gruppgeneratorn depublished,
  other seeded tools unpublished. Staging grants `skriptoteket-proof-user`
  contributor role and gruppgeneratorn maintainership. Next: staging editor walk
  (edit sibling `grouping.py`, sandbox run, save), record proof, close docs. UX
  note: a saved class list is not selected in step 2 until the class name is filled.

- TASK-SKRIPT-REP-0035 passive web liveness deployed in production and staging
  (c282c74b, image 0ae40a8a34a2, /healthz 200). Owner skill-repository parent 01a1036b; next: terminal closeout.
  34 focused tests passed; next natural checks 25.005 ms prod / 24.596 ms staging.
  Proof: task-worktree .artifacts/native-health/passive-\*-rollout-proof.json (2026-10-06).

- Exam epics 39/40/41, backlog reconciled 2026-10-20 against main 114ca971; each open
  task's `## Progress` names its main merge and what is owed. Plan 2026-10-17 (user
  decisions G1-G30, retained `01a1495e-8398-75be-b2da-f0b08ba11afa`
  evidence/planning/decisions-2026-10-17.md): walk only exam-converter changes, once
  per wave; restyle and repairs close on approved review plus unit tests. Mac parent
  integrates, pushes main and walks staging; the Hemma orchestrator (desktop SSH
  session, cwd ~/apps/skriptoteket) runs leads. Leads Opus 5.5, reviews Pi Sol 6.1,
  explorers Haiku. Exam.net has no QTI export; QTI is the Exam.net route and the print
  PDF renders the DOCX house template (user 2026-10-18).

  - On main, closeout owed (user or orchestrator closes):
    - 40-04-09: F1 rereview and the R14 Exam.net check (REP-0048) owed.
    - 39-06-08: walk with the Exam.net import owed.
    - 39-01-02: review of the 2026-10-18 commits owed.
    - 40-02-01: tranche 3 review, 13 exam-held wrappers, `lucide-vue-next` removal.
  - Closed by the user 2026-10-20: TASK-SKRIPT-40-04-10 and ST-SKRIPT-40-03.
  - Ready, not started:
    - 39-06-09: waits on 39-06-08.
    - Proposed follow-ups chosen by the user 2026-10-22: 41-03-02 ghost text, 41-03-03 chat
      Markdown, 39-04-24 rising import count.
    - ST-SKRIPT-41-03 AI for every signed-in teacher (user grilling 2026-10-22, Mac root
      `01a160e1-08de-706a-8728-3510b9547579`): 41-03-01 done and in production;
      next 41-03-02/03 proposed.
  - ST-SKRIPT-39-10 digital-PDF import `ready` (user grilling 2026-10-21, plan
    in Mac root `01a1602d-173d-72ed-b3ac-83c6a24e9070`); owner Hemma orchestrator,
    one lead per task. Real PDF exams from the user go in `.artifacts/pdf-import-proof/`.

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

- 2026-10-28 `done`: TASK-SKRIPT-REP-0040 Sir Convert public-host retirement (rereview
  `d97caf5b` approved, main `ced7971b`; env check in retained `01a18444`). User step: Namecheap CNAME deletion.

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

- 2026-10-21 `done` on main: [TASK-SKRIPT-REP-0050](docs/backlog/tasks/task-skript-rep-0050-backend-pytest-runs-parallel-and-quiet-by-default-and-serial-runs-need-a-stated-reason.md) parallel and quiet pytest (merge `6a557b5d`; review 321854a9 F1-F6 medium repaired `b1f019e6`, admitted on focused proof).

- 2026-10-20 `done` on main: TASK-SKRIPT-40-04-20 print keeps imported formatting (`43f47eda`, user closure; Mac walk `.artifacts/staging-walk-e4d15c4a/walk-record.md`). Unreadable-notice wrap fix merged `a8de9ae6` (Pi review `ec4f5dae` approved; walk PASS).

- 2026-10-20 `done` on main: TASK-SKRIPT-41-02-06 unreadable exam files (`0ab8ccb8`, user closure; Mac walk `.artifacts/staging-walk-e4d15c4a/walk-record.md`).

- 2026-10-20 `done` on main: TASK-SKRIPT-40-04-13 and -14 gap lane (merge `f84eb85d`, rereview 12 approved, Mac step 5 re-walk PASS; user closure).

- 2026-10-20 `done` on main: TASK-SKRIPT-06-17-02 migration tests pinned to their own revision, plus the pre-push migration stage (`3d3f867a`, user closure; the stage ran on its first push, 118 passed). TASK-SKRIPT-06-17-01 canceled as superseded by it.

- 2026-10-20 `done` on main: TASK-SKRIPT-39-05-16 unused long-form readiness copy deleted (`5611f0c8`, user closure).

- 2026-10-20 `done` on main: TASK-SKRIPT-41-02-05 guest draft handover to Mina filer (`8be9aefa`, user closure; Mac walk `.artifacts/staging-walk-e4d15c4a/walk-record.md`). Follow-ups D10, D24 in Current.

- 2026-10-20 `done` on main: TASK-SKRIPT-39-05-15 type choice on an unconverted question (`e4d15c4a`, user closure; Mac walk `.artifacts/staging-walk-e4d15c4a/walk-record.md`).

- 2026-10-19 `done` on main: TASK-SKRIPT-39-04-21 points wording (`99378586`, user closure; Mac walk `.artifacts/staging-walk-99378586/walk-record.md`). U4 offer line parked.

- 2026-10-19 40-04-11 control system `canceled` as superseded by 40-04-17 (user decision; no product code). The docs-only branch `codex/task-skript-40-04-compact-tools-remote` holds the reuse list (task section "Superseded by TASK-SKRIPT-40-04-17"); the inventory and mocks are in root 01a15383.

- 2026-10-19 `done` on main: 40-04-07 writing areas (staging walk at `003c874a`, Mac `.artifacts/staging-walk-40-04-07/evidence/walk-record.md`), 41-02-01 QTI import, 39-04-15, 39-04-16, 39-04-17, REP-0047, HULE-14-03-01, 39-04-19 Del A left-out repair, REP-0046 re-recorded omprov labeler calls, 39-04-18 facit carry-over. Pre-push hook SIGPIPE false skip fixed (`003c874a`).

- 2026-10-10: sir-convert-a-lot `main` pushed (`3fb6f672`) with the
  EPIC-SIRCON-07/08 supersession notes; their terminal closure is blocked
  on migrating both epics to the contract-derived profile with open child
  stories (user decision pending; ST-SIRCON-07-01 still states the old QTI
  2.1 claim).

## Facts

- Session Date: 2026-10-15
- Last Refreshed: 2026-10-22
- Pushing `main` runs the full `pdm run typecheck` and `pdm run test` on Hemma first (`scripts/hemma_pre_push_check.sh`, pre-push hook; install with `pre-commit install --hook-type pre-push`). Run the push in the background; a failure blocks it, on Hemma the steps run directly with no ssh, an unverifiable push is blocked, Markdown-only commits reuse the last pass.
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
