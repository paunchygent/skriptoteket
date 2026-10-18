---
type: task
id: TASK-SKRIPT-41-02-01
title: Teachers and guests import a QTI package into the exam workspace
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-18'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- A QTI package exported by Skriptoteket or Exam.net imports into a native exam document with its items, points and answer keys, signed-in and as a guest, with no AI
- Unsupported QTI items are skipped with a visible note
story: ST-SKRIPT-41-02
backlog_document_profile: contract-derived
---

## Implementation Contract

The workspace exports QTI (`examnet_qti_export.py`, `examnet_qti_leaf_items.py`) but cannot import it. This task adds a deterministic QTI package importer that maps the item kinds the workspace exports (choice, gap fill, inline choice, free text, information items) back to a native exam document, the way `build_native_exam_from_digiexam` maps DigiExam, and offers it as `QTI` in the Öppna drawer for signed-in teachers and as a stateless parse for guests (Q1-Q3).

Non-goals: AI repair of imported items; QTI versions other than the one the export writes and Exam.net's own export.

## Contract Inputs

- ST-SKRIPT-41-02 P1; User grilling 2026-10-18 in the Mac orchestration session (retained root 01a14ee0-903e-7423-b969-30e3661e9006); explorer maps of the DigiExam lines and paid AI call sites the same day.
- `domain/curated_apps/exam_workspace/digiexam_import.py` (mapper pattern), `examnet_qti_export.py`, `docs/reference/ref-skript-research-exam-net-qti-import-routes-per-question-type-*.md`.
- Mac parent rulings 2026-10-18, relayed by the orchestrator to the implementation lead:
  - Ordering items import, with answer-key origin `teacher_authored`, because the QTI key is the order the teacher wrote. They are not skipped under 39-06-08 D3.
  - These Q2 round-trip losses are accepted because the export cannot carry them. Tests assert each one by name: free-text rubric criterion text (never written), document instructions folded into every item prompt, automatic gap values merged into accepted values, and a parent with one non-gap child flattened to a standalone item.
  - AC1's Exam.net part stays in this task. The Skriptoteket QTI shape is built and proven first. A real Exam.net export, supplied by the Mac parent, becomes a fixture and is proven before review.

## Core Vertical And Performance

The vertical is one pure domain mapper from a parsed QTI package to a `NativeExamDocument`, used by the signed-in import (stored in Mina filer like the DigiExam import) and by a public stateless parse route returning the document. Round trip: export then import gives the same items, points and keys. No performance concern beyond package size limits.

## Validation

- Focused tests: round trip of the omprov fixture export; each supported item kind; skipped unsupported items with notes; malformed packages refused with a Swedish error.
- Vitest for the Öppna QTI entry. Lint and typecheck for touched domains.

## Stop Conditions

Stop and report if Exam.net's own export uses item kinds the export never writes and they need a product decision.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| Q1  | QTI import is deterministic and makes no AI call. |
| Q2  | A Skriptoteket QTI export imported again gives the same items, points and answer keys. |
| Q3  | Unsupported items are skipped with a visible note, as in the DigiExam import. |

## Resume Here (clean break 2026-10-18)

- Branch `codex/task-skript-41-02-01-remote` in worktree
  `/home/paunchygent/apps/skriptoteket-task-skript-41-02-01-remote`; head is
  the commit that adds this note. Never push it.
- Retained root:
  `/home/paunchygent/apps/skriptoteket/.orchestration/context/sessions/01a14f56-3344-77cc-a009-f435f5884ea7`;
  work orders are under its `evidence/work-orders/`.
- Units done and committed: U4 zip reader, U1a rich-content reader, U1b item
  reader, U2 native mapper with robustness repair, U3 parent reader, and U5
  application handlers, the stateless guest parse entry
  `ParseExamWorkspaceQtiPackageHandler` and the signed-in route
  `POST /exam-workspace/import-qti`.
- Units in flight at the break (OpenCode juniors on GLM; they keep running and
  write uncommitted files into the worktree):
  - U6 frontend Öppna-drawer QTI entry, work order `u6-frontend.md`, child
    `7663d340-0ce8-4e89-a82e-5100d97391c9`. Only the regenerated
    `openapi.d.ts` was committed at the break.
  - U7 round trip of the omprov exports, work order `u7-round-trip.md`, child
    `01685541-4cb2-4728-aef1-7e105a8e462c`.
  - Each result lands at the retained root's `evidence/results/<child id>.json`.
- Next action: read both results, then verify and commit the U6 and U7 files.
  Rerun any unit whose child died as a fresh junior from the same work order.
- Open findings: the plain space between two marked runs is lost to
  `ElementTree.indent` in the writer. TASK-SKRIPT-REP-0048 removes it; after it
  merges, flip `test_plain_space_between_marked_runs_is_lost_to_writer_indentation`
  to expect no loss.
- Gates: the parent supplies a real Exam.net QTI export, which becomes a fixture
  and must be proven before review. Merge `origin/main` only when the parent says
  REP-0044 or REP-0048 has landed. After that comes closeout: lint, typecheck,
  frontend checks, `docs-validate` and one domain-wide suite, then the final
  checkpoint and review routing by the parent.
