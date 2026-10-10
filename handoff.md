## Current

- [TASK-SKRIPT-39-04-01](docs/backlog/tasks/task-skript-39-04-01-docx-walking-skeleton-import-native-edit-and-create-save-and-reopen-export.md)
  is `in_progress`; reviewed work merged to `main` (`8b46ba8f`, pushed).
  Supporting gates: fe vitest/typecheck/lint/build green, ruff clean, mypy
  12 baseline errors, 9 unit failures all reproduced on origin/main; 5
  Postgres integration tests and migration tests pass. D5 live walk
  2026-10-10 (Claude, built-in browser, viewport 846x822) on Hemma
  staging `http://127.0.0.1:15173` at `8b46ba8f`, signed in through the
  HuleEdu browser-session ceremony as the staging proof user: imported
  `grammatik_omprov_examnet_import_med_facit.docx` (8 items, 38 points, 5
  review_required); edited Fråga 1, added Fråga 9 (2 points), marked all
  9 Granskad, saved v2; left and reopened from "Sparade prov" with every
  edit (40 points); QTI, PDF and DOCX exports returned 200 and all contain
  the edits; QTI zip has imsmanifest, 9 items, correctResponse on the 7
  gap items. Evidence: session `01a1257f-b1b7-741b-ac62-044125c05d6b/evidence/staging-walk/`.
  Not proven: proposal acceptance. Every gap item in the fixture is keyed,
  and clearing a gap's accepted values returns 422 "gap gap_001 needs
  accepted values for a keyed item" under a generic Swedish error, so no
  item becomes eligible. Other findings: the review reason shows the raw
  code `long_answer_key`; the QTI test title is the filename, not the exam
  title. Owner: Claude session. User gates: the gap-clearing fix
  (prerequisite for the proposal step), proposal carry-over across saves,
  D5 acceptance, terminal closure.
- [TASK-SKRIPT-REP-0036](docs/backlog/tasks/task-skript-rep-0036-resolve-mina-filer-app-export-labels-from-the-app-id-prefix.md)
  is `proposed` with the fix committed (`8a0fc469`, 8 unit tests); user owns
  proposed->ready. Follow-up: Mina filer keeps every workspace version
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
  gate): ADR-0091 is `accepted`, the story and TASK-SKRIPT-39-04-01 are
  `ready`, and the DOCX walking skeleton is unblocked.
- TASK-SKRIPT-REP-0035 passive web liveness is deployed in production and staging.
  Owner: skill-repository parent 01a1036b; next: terminal closeout.
  Published c282c74b; exact image 0ae40a8a34a2; full startup healthy; /healthz 200.
  34 focused tests passed; next natural checks 25.005 ms prod / 24.596 ms staging.
  Proof: task-worktree .artifacts/native-health/passive-*-rollout-proof.json (2026-10-06).


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
- Full typecheck keeps the existing 10-error baseline in three
  `src/skriptoteket/script_bank/scripts/` demo scripts.
- Open product questions (undecided, not silently resolved): native doc
  format internals (new versioned doc type vs file-plus-sidecar state);
  deferred scanned-PDF behavior (hard-fail with guidance vs generic
  extraction queue); digital-PDF slice detail follows ST-39-04 review.
- Next: fix the gap-clearing 422 so a keyed gap can lose its key, then
  finish the D5 proposal step on staging; ADR-0091/ST-SKRIPT-39-04 review
  accepted 2026-10-09.
