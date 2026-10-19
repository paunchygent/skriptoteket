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
  - A QTI package exported by Skriptoteket, including one Exam.net accepted on import, imports into a native exam document with its items, points and answer keys, signed-in and as a guest, with no AI
  - Unsupported QTI items are skipped with a visible note
story: ST-SKRIPT-41-02
backlog_document_profile: contract-derived
---

## Implementation Contract

The workspace exports QTI (`examnet_qti_export.py`, `examnet_qti_leaf_items.py`) but cannot import it. This task adds a deterministic QTI package importer that maps the item kinds the workspace exports (choice, gap fill, inline choice, free text, information items) back to a native exam document, the way `build_native_exam_from_digiexam` maps DigiExam, and offers it as `QTI` in the Öppna drawer for signed-in teachers and as a stateless parse for guests (Q1-Q3).

Non-goals: AI repair of imported items; QTI versions other than the one the export writes. Exam.net offers no QTI or exam-content export (Mac parent check 2026-10-19: no export control in its exam editor or Mina prov row menu, no QTI help article, and every 'exportera' article covers student results), so no Exam.net-authored package exists to import.

## Contract Inputs

- ST-SKRIPT-41-02 P1; User grilling 2026-10-18 in the Mac orchestration session (retained root 01a14ee0-903e-7423-b969-30e3661e9006); explorer maps of the DigiExam lines and paid AI call sites the same day.

- `domain/curated_apps/exam_workspace/digiexam_import.py` (mapper pattern), `examnet_qti_export.py`, `docs/reference/ref-skript-research-exam-net-qti-import-routes-per-question-type-*.md`.

- Mac parent rulings 2026-10-18, relayed by the orchestrator to the implementation lead:

  - Ordering items import, with answer-key origin `teacher_authored`, because the QTI key is the order the teacher wrote. They are not skipped under 39-06-08 D3.
  - These Q2 round-trip losses are accepted because the export cannot carry them. Tests assert each one by name: free-text rubric criterion text (never written), document instructions folded into every item prompt, automatic gap values merged into accepted values, and a parent with one non-gap child flattened to a standalone item.
  - Mac parent ruling 2026-10-19 (relaying the user, "create one on your own"): Exam.net has no exam-content export. The import fixture is the Skriptoteket QTI 3.0 package that Exam.net accepted on import as exam 5345261 (`39-06-svenska2-rev11-qti.zip`, the Svenska 2 rev11 workspace exam exported from main 1f9e4367; proof in retained root `01a149c9-5bc7-7713-ba64-12dee0470bdd` at `evidence/staging-proof-1f9e4367/proof.md` steps 8-9). It is committed with a provenance note and its import is proven before review, each accepted loss named in a test.

- Parent ruling 2026-10-19 (review 596c1654 repair): scores are never guessed
  and never silently dropped. A present zero is zero. A gap or inline-choice
  child inside a part gets a score only from exact evidence (the part total
  minus the other children's stated scores, consistent with its per-gap
  share); otherwise its points stay absent and the item goes to review with a
  visible reason. Untrusted package XML is parsed through one hardened entry
  point (defusedxml, DTD and entities refused), nesting and numbers are
  bounded, and a package that references one item file twice is refused.

## Core Vertical And Performance

The vertical is one pure domain mapper from a parsed QTI package to a `NativeExamDocument`, used by the signed-in import (stored in Mina filer like the DigiExam import) and by a public stateless parse route returning the document. Round trip: export then import gives the same items, points and keys. No performance concern beyond package size limits.

## Validation

- Focused tests: round trip of the omprov fixture export; each supported item kind; skipped unsupported items with notes; malformed packages refused with a Swedish error.
- Vitest for the Öppna QTI entry. Lint and typecheck for touched domains.

## Stop Conditions

Stop and report if the Exam.net-accepted fixture shows a round-trip loss that is not one of the accepted losses.

## Decided Contract Terms

| ID  | Decided contract term                                                                  |
| --- | -------------------------------------------------------------------------------------- |
| Q1  | QTI import is deterministic and makes no AI call.                                      |
| Q2  | A Skriptoteket QTI export imported again gives the same items, points and answer keys. |
| Q3  | Unsupported items are skipped with a visible note, as in the DigiExam import.          |

## Resume Here (lead 769b36fd, 2026-10-19)

- Branch `codex/task-skript-41-02-01-remote` in worktree
  `/home/paunchygent/apps/skriptoteket-task-skript-41-02-01-remote`. Never push it.
- Retained root:
  `/home/paunchygent/apps/skriptoteket/.orchestration/context/sessions/01a14f56-3344-77cc-a009-f435f5884ea7`;
  work orders under `evidence/work-orders/`, results under `evidence/results/`.
- Done: U1-U7 (readers, mapper, handlers, `POST /exam-workspace/import-qti`,
  Öppna QTI `.zip` entry, omprov round trip with named losses). Merge of
  `origin/main` (REP-0044, 39-06-10) is commit 368f6bb4; a QTI `.zip` stays
  open to every role past the REP-0044 Word gate.
- Done after the merge: U8-U12, U9 (commits 820b6056..4b254bae); review
  596c1654 at 4b254bae returned changes_requested (F1-F5 high, F6-F7 medium).
- Repair done: 8e78331a production splits (F7); 94b22c51 hardened XML entry
  point and refused repeated references (F1, F6, F2); 2afe9833 and 91b914a3
  bounded, exact scores and kept zeros (F3, F4, F5); d4a3991a test splits (F7).
  Lint, typecheck and 407 focused tests plus the PostgreSQL QTI API test pass.
- Next: one domain suite on the parent's go (shared DI and handler modules
  moved), then rereview of F1-F5 by 596c1654 through the parent.
- Product consequence of F4: a part with two or more gap children imports
  those children with points absent and review required, because the export
  states only rounded-down per-gap shares.
- Open finding: the plain space between two marked runs is lost to
  `ElementTree.indent` in the writer. After TASK-SKRIPT-REP-0048 lands on main,
  merge it and flip
  `test_plain_space_between_marked_runs_is_lost_to_writer_indentation`.
