## Current

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
  filer; PDF/DOCX/QTI are on-demand exports only. Cleanup first: 02-03,
  03-03, 03-04 must finish before DOCX implementation, which also waits for
  ADR-0091/story review. Verbose prior history archived to
  `.codex/long-term-memory/entries/session-2026-09-05-epic-39-handoff-compaction.md`.
- [TASK-SKRIPT-39-03-03](docs/backlog/tasks/task-skript-39-03-03-retire-the-sir-convert-exam-specific-integration.md)
  is `in_progress`: both consumers moved (03-01/03-02 `done`), so its stop
  condition is met; cross-repo surfaces need linked authority in the owning
  repo. Generic Sir extraction, OCR, and STT are preserved.
- [TASK-SKRIPT-39-03-04](docs/backlog/tasks/task-skript-39-03-04-retire-the-hemma-qwen-answer-key-sidecar.md)
  is `ready`, blocked until 03-03 plus last-consumer-moved proof. Its
  retirement is governed by 03-04; no live deployment state is asserted
  here. Luna/GLM plus the daily lease remain.
- [TASK-SKRIPT-39-02-03](docs/backlog/tasks/task-skript-39-02-03-repair-partial-digiexam-answer-key-enrichment-and-prove-the-real-integrated-vertical.md)
  is `ready`: item-local enrichment repair for
  `1776888013-ak7-lag-och-ratt.dxe` with real-DXE integration plus Docker
  browser gates. It is a required predecessor for the DOCX skeleton.
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

- 2026-09-05: reconciled EPIC-39/ADR-0090 with the approved workspace scope
  via scaffolder-created ADR-0091, ST-39-04, and TASK-39-04-01 (all
  `proposed`); `pdm run docs-validate` green; `git diff --check` clean.
- 2026-08-30/31: public (03-02) and authenticated (03-01) cutovers done;
  both lanes run Skriptoteket-owned with zero Sir exam calls.

## Facts

- Session Date: 2026-09-05
- Last Refreshed: 2026-09-05
- Current docs validate with `pdm run docs-validate`.
- Historical terminal docs audit separately with `pdm run python -m scripts.historical_docs.validate_historical_docs`.
- No code changes in this slice; no staging, commit, merge, push, branch
  switch, or worktree change.
- Open product questions (undecided, not silently resolved): native doc
  format internals (new versioned doc type vs file-plus-sidecar state);
  deferred scanned-PDF behavior (hard-fail with guidance vs generic
  extraction queue); digital-PDF slice detail follows ST-39-04 review.
- Next executable task: finish TASK-SKRIPT-39-03-03, then 03-04 (and 02-03),
  then review ADR-0091/ST-SKRIPT-39-04 before TASK-SKRIPT-39-04-01.
