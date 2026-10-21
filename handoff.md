## Current

- 41-02-05 follow-up (unscheduled): D24 a server claim per draft_id.

- TASK-SKRIPT-40-04-19 `proposed` (user, 2026-10-20): two tabs holding exam
  locks invalidate each other's CSRF token on every renew. Not started.

- Closeout owed: TASK-SKRIPT-06-18-01 is merged on main but still `proposed`;
  its readiness and closure go to the user through the Mac orchestrator.

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
    - 40-04-12: K11 passed; K7 "/" check owed, shared with 39-04-20 (f7eeada5).
    - 40-01-04: review owed.
    - 40-04-09: F1 rereview and the R14 Exam.net check (REP-0048) owed.
    - 40-04-05: review and walk owed.
    - 39-04-11 and 39-04-12: staging omprov/Svenska 2 import owed.
    - 39-06-08: walk with the Exam.net import owed.
    - 39-07-03: suites and walk not recorded.
    - 39-01-02: review of the 2026-10-18 commits owed.
    - 40-02-01: tranche 3 review, 13 exam-held wrappers, `lucide-vue-next` removal.
  - Closed by the user 2026-10-20: TASK-SKRIPT-40-04-10 and ST-SKRIPT-40-03.
  - Ready, not started:
    - 41-02-03: removes the old guest DigiExam converter (user 2026-10-20).
    - 39-06-09: waits on 39-06-08.
    - 41-01-02, -03, -04: wait on HuleEdu TASK-HULE-14-03-01 on staging.
  - Planned, no story yet: EPIC-SKRIPT-39 item 06, digital-PDF import (scanned
    deferred).

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
- Last Refreshed: 2026-10-21
- Pushing `main` runs the full `pdm run typecheck` and `pdm run test` on Hemma first (`scripts/hemma_pre_push_check.sh`, pre-push hook; install with `pre-commit install --hook-type pre-push`). Run the push in the background; a failure blocks it, unreachable Hemma warns, Markdown-only commits reuse the last pass.
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
