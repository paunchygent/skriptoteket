---
type: task
id: TASK-SKRIPT-39-09-02
title: 'QTI 3.0 port: proven Exam.net shapes for pictures, uneven points and gap values
  in both lanes'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-15'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-reviewer
  decided_at: '2026-10-15'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'Pi ruthless-reviewer (gpt-6.1-sol, high) approved 83d522c6 with no findings (merged 6807d20c). Staging walk at 6807d20c: DigiExam conversion with a picture imported into Exam.net as 5333308 (picture shown, all-or-nothing 4p, equal 1p and 3p rows, gaps 0.66 x3); workspace export with a 2p three-pair grid subquestion imported as 5333310 (ALL_CORRECT 1p, Q16 flag case). Records in Skriptoteket session 01a13c92-d70e-765f-ae36-b6583539e201 evidence/reviews/TASK-SKRIPT-39-09-02/ and evidence/walk/TASK-SKRIPT-39-09-02/staging-walk.md.'
task_kind: story
acceptance_criteria:
- Exam.net imports a staging workspace export and a DigiExam conversion with every
  picture shown and every question's key and points as the contract states
story: ST-SKRIPT-39-09
backlog_document_profile: contract-derived
---

## Implementation Contract

Delivers ST-SKRIPT-39-09 task 2 (story terms Q2, Q6, Q16, Q17): both lanes,
the exam workspace and the DigiExam converter, write the QTI 3.0 shapes that
Exam.net imports with pictures shown and with every key and point as below.

- **Pictures.** Each picture is stored at `items/images/<item>-<asset>.<ext>`,
  referenced from the item as `src="images/<item>-<asset>.<ext>"`, and listed
  as a `file` of its item resource in the manifest. Validation accepts only
  picture sources that resolve to a package file under `items/images/`; the
  `resources/` location and its `../resources/` rule are deleted.
- **Equal shares.** A choice, multiple-response or matching question keeps
  one mapping in which every correct answer has the same value, the points
  divided by the number of correct answers, when that value is exact to 2
  decimals.
- **All-or-nothing (Q16).** When that value is not exact to 2 decimals, the
  question has a correct response, no mapping and MAXSCORE equal to its
  points. Custom response processing gives the points when the response
  matches the correct response, standalone and as a shared-instruction child
  (the match_correct template would give 1 point). The parent's processing
  starts SCORE at 0, adds each answered mapped child, then the all-or-nothing
  children, in valid QTI 3.0.
  Validation allows match_correct on choice and match items without a
  mapping, and rejects match_correct together with a mapping.
- **Gap values (Q17).** Every gap of one Lucktext has the same mapped value:
  the points divided by the number of gaps, rounded down to 2 decimals. A
  Lucktext whose rounded value is 0 has no mapping.
- **Unequal shares deleted.** `_split_point_values` and every unequal split
  are deleted; no lane writes unequal mapped values within one response or
  one Lucktext.
- **Golden files.** `tests/fixtures/exam_conversion/reference-qti-package.zip`,
  `reference-summary.json` and `qti_standalone_item_xml_sha256.json` are
  regenerated from the new writer.
- **Out of scope.** The export-panel list of flagged questions (story Q15) is
  task 6; Kategorisera grids, Fritext criteria and Kort svar are tasks 3–5.

## Contract Inputs

- ST-SKRIPT-39-09 terms Q2, Q6, Q16 and Q17.
- Probe round 19 readback, Exam.net 5333233, 5333235, 5333272 and 5333273:
  Skriptoteket session `01a13c92-d70e-765f-ae36-b6583539e201`
  `evidence/probe-r19/readback.md`.
- HuleEduOS `.codex/skills/examnet-qti-import/references/examnet-qti3-contract.md`
  (picture row, proven in probe round 11, exam 5243167).
- Writer: `domain/curated_apps/exam_conversion/examnet_qti_package.py`
  (picture paths, `_image_file`), `examnet_qti_manifest.py`,
  `examnet_qti_xml.py` (mappings, `_gap_point_values`,
  `_split_point_values`), `examnet_qti_item_xml.py` (response processing),
  `examnet_qti_inline_prompt.py`, `examnet_qti_validation.py`
  (`_match_correct_template_errors`, `_validate_item_image_references`).
- Tests that assert the old picture paths, gap split and template rule:
  `test_examnet_qti_package.py`, `test_examnet_qti_contract_rules.py`,
  `test_examnet_qti_inline_prompt.py`, `test_examnet_qti_interactions.py`,
  `test_digiexam_fractional_source_repairs.py`,
  `test_digiexam_recoverable_source_repairs.py` and
  `exam_workspace/test_examnet_qti_parents_and_matching.py`.

## Core Vertical And Performance

A teacher exports a workspace exam with a picture, an uneven multiple-response
question (standalone and as a shared-instruction child) and a multi-gap
Lucktext with uneven points; a DigiExam file is converted on the public
converter. Both packages import into Exam.net with every picture shown, the
multiple-response questions as one ALL_CORRECT rule each, and the Lucktext
with equal gap rows. No performance concern: package size and work are
unchanged.

## Validation

- Focused unit tests under `tests/unit/domain/curated_apps/exam_conversion/`
  and `tests/unit/domain/curated_apps/exam_workspace/` for the QTI writer and
  validation, plus `tests/unit/application/curated_apps/test_exam_workspace_exports.py`
  and `test_exam_conversion_parity.py`, pass against the new output. New tests
  cover equal shares, all-or-nothing standalone and as a child, rounded gap
  values, zero gap value, and picture paths.
- Staging walk: the workspace export and a DigiExam conversion of
  `tests/fixtures/exam_conversion/1772718003-test-samma-prov-i-digiexam.dxe`
  are imported into Exam.net in the agent's own tab and read back through
  `/api/exams/automarked/<id>/questions`; pictures are checked in the editor.

## Stop Conditions

- Exam.net drops a picture stored under `items/images/`.
- A lane needs unequal mapped values to keep a question's points.
- The parent's all-or-nothing response processing cannot be expressed in valid
  QTI 3.0 next to mapped children.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                              |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| T1  | Pictures live at `items/images/`, are referenced as `images/<file>` and are listed as item-resource files; the `resources/` location is deleted (story Q6).        |
| T2  | Choice, multiple-response and matching questions use equal mapped values when exact to 2 decimals and otherwise all-or-nothing, standalone and as children (Q16). |
| T3  | Every gap of one Lucktext has the points divided by the gaps rounded down to 2 decimals; unequal splits are deleted (Q17).                                         |
| T4  | Both lanes use the same writer and are each proved by an Exam.net import with readback (story Q2).                                                                 |
