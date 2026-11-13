---
type: task
id: TASK-SKRIPT-REP-0048
title: QTI item serializer indents block structure only and never mixed inline content
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-18'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: orchestrator
  decided_at: '2026-10-28'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'Mac staging walk at 05b3fc12a with the user''s Exam.net account, 2026-10-28 (Mac ~/Repos/Skriptoteket/.artifacts/staging-walk-05b3fc12a/walk-record.md): nested marks and marked runs keep their spacing in the export and in Exam.net. R14 ends with position numbers kept in the PDF för Exam.net headings and the QTI titles (user decision 2026-10-28, AskUserQuestion: Keep position numbers); a QTI package titled 2a and 2b imported without error and Exam.net numbers questions itself.'
task_kind: repository
acceptance_criteria:
  - Nested marks and a single space between marked runs serialize with exact inner text and no added whitespace
  - Block structure stays indented and the reference QTI package bytes are regenerated with the diff explained
backlog_document_profile: contract-derived
---

## Implementation Contract

`serialize_qti_assessment_item` in `src/skriptoteket/domain/curated_apps/exam_conversion/examnet_qti_item_xml.py` calls `ElementTree.indent(root, space="  ")` on the whole item. `ElementTree.indent` rewrites every empty or whitespace-only `text` and `tail` of an element that has children. Inside mixed inline content that changes the rendered text: nested marks `<strong><em>x</em></strong>` become `<strong>\n  <em>x</em>\n</strong>`, so Exam.net shows " x " with spurious spaces, and a single space tail between two marked runs is replaced by a newline and indentation in the same way.

This task replaces that call with a block-structure indenter in the item serializer (R2-R4). It regenerates the pinned reference package and its recorded hashes (R5) and explains the byte diff below.

Non-goals: the assessment-test and manifest serializers (`examnet_qti_assessment_test_xml.py`, `examnet_qti_manifest.py`). They hold structure only, no inline content, and keep `ElementTree.indent`. The QTI importer of TASK-SKRIPT-41-02-01 and its test that asserts the indentation loss are updated on that branch after this merge.

## Contract Inputs

- Mac parent ruling 2026-10-18; defect found by the TASK-SKRIPT-41-02-01 lead.
- `examnet_qti_rich_text.py` (`MARK_ELEMENT_NAMES`, `append_marked_text`) and `examnet_qti_inline_prompt.py` (inline `br`, `img`, gap interactions).
- Pins: `tests/fixtures/exam_conversion/reference-qti-package.zip`, `reference-summary.json` (`qti_package_sha256`), `qti_standalone_item_xml_sha256.json`.
- CPython `xml.etree.ElementTree.indent` documentation (Context7 `/python/cpython`, fetched 2026-10-18).

## Core Vertical And Performance

The vertical is one QTI item built in memory and serialized to bytes in an Exam.net package. The indenter makes one pass over the tree. No performance concern.

## Validation

- Focused: `tests/unit/domain/curated_apps/exam_conversion/test_examnet_qti_item_indentation.py` (new), `test_examnet_qti_inline_prompt.py`, `test_examnet_qti_package.py`, `tests/unit/application/curated_apps/test_exam_conversion_parity.py`, `tests/unit/domain/curated_apps/exam_workspace/test_examnet_qti_parents_and_matching.py`.
- The exam_conversion domain suite once at the end; `pdm run lint` and `pdm run typecheck`.
- Behaviour: the next staging walk re-checks nested marks and marked runs in Exam.net.
- Walk check from TASK-SKRIPT-40-04-09 R14 (user 2026-10-19, "Test first"): import into Exam.net a PDF för Exam.net and a QTI package whose question headings and titles use list labels such as "2a", and record whether Exam.net accepts them. Today both keep position numbers; they switch to list labels only after this check passes.

## Stop Conditions

Stop and report to the parent if a test outside the pinned hashes asserts the old whitespace, if a pin changes in an entry that holds no inline content, or if the fix needs a change to item construction.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                                              |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R1  | Root cause: `ElementTree.indent` on the whole item rewrites empty and whitespace-only `text` and `tail` inside mixed inline content (see Implementation Contract).                                                                                                                                                                                 |
| R2  | A private block-structure indenter in `examnet_qti_item_xml.py` replaces the `ElementTree.indent` call there; the call is deleted, with no fallback.                                                                                                                                                                                               |
| R3  | An element's children are indented only when the element is block-only: its `text` is `None` or `""`, every child's `tail` is `None` or `""`, and no child is an inline element. Inline elements are the `MARK_ELEMENT_NAMES` values plus `br`, `img`, `qti-text-entry-interaction` and `qti-inline-choice-interaction`, all in the QTI namespace. |
| R4  | The indenter leaves a non-block-only element's whole subtree exactly as built. Block-only elements get the same whitespace as `ElementTree.indent` with two spaces per level, so structure-only output is byte-identical to before.                                                                                                                |
| R5  | The reference package zip, `reference-summary.json` `qti_package_sha256` and `qti_standalone_item_xml_sha256.json` are regenerated from the new serializer. The byte diff is explained in this doc.                                                                                                                                                |
| R6  | Adversarial tests: nested marks keep exact inner text with no added whitespace; a single space between two marked runs survives; block elements are still indented; the XML parses and its `itertext` content equals the built text.                                                                                                               |

## Byte Diff (R5)

- `reference-qti-package.zip` and `reference-summary.json` are byte-identical. The DigiExam reference exam has no marks, and none of its paragraphs or choices start with an inline element, so every element `ElementTree.indent` touched there was block-only.
- `qti_standalone_item_xml_sha256.json`: 68 item hashes change in seven of the eight recorded exams (metodprov unchanged). Every change removes whitespace only; the content with all whitespace removed is identical (lead probe, 2026-10-18). The old indenter opened 40 `p` elements and 9 `qti-simple-choice` elements with a newline because they begin with an inline child. Example, bf26 diagnostic grammar item 008: old `<p>` newline, indent, `<qti-text-entry-interaction .../> (Det här är) ...`; new `<p><qti-text-entry-interaction .../> (Det här är) ...`.

## Resume Here

- Branch `codex/task-skript-rep-0048-remote`; retained root `/home/paunchygent/apps/skriptoteket/.orchestration/context/sessions/01a14f6c-926f-77fe-99f0-471ae948c619`.
- Done: indenter (u1), adversarial tests and regenerated pins (u2), byte-diff explanation, focused proof.
- Next: independent review routed by the parent, then merge to main. After the merge, TASK-SKRIPT-41-02-01 updates its importer test that asserts the indentation loss.
- User gate: the next staging walk re-checks nested marks and marked runs in Exam.net.
- Walk check: Exam.net imports list-label headings and titles such as "2a" (from TASK-SKRIPT-40-04-09 R14; see `Validation`).
