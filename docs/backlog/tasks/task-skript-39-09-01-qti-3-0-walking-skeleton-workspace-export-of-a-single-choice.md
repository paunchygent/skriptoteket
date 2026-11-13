---
type: task
id: TASK-SKRIPT-39-09-01
title: 'QTI 3.0 walking skeleton: workspace export of a single-choice question imports into Exam.net'
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
  approval_evidence: 'Pi ruthless-reviewer (gpt-6.1-sol) requested one change on 0b66adff (generator and profile ids still named 2.1) and approved the repair 59bd596a (merged b6d6b3f4). Staging walk at b6d6b3f4: QTI export of document 55aecb08 imported into Exam.net as exam 5333228 with both single-choice keys, the gap answers, the grid and all points as in the workspace. Records in Skriptoteket session 01a13c92-d70e-765f-ae36-b6583539e201 evidence/reviews/TASK-SKRIPT-39-09-01/ and evidence/walk/TASK-SKRIPT-39-09-01/staging-walk.md.'
task_kind: story
acceptance_criteria:
  - The staging workspace exports a QTI 3.0 package whose single-choice question Exam.net imports with its key and points
story: ST-SKRIPT-39-09
backlog_document_profile: contract-derived
---

## Implementation Contract

Delivers ST-SKRIPT-39-09 task 1 (story terms Q1, Q2, Q4, Q6): the shared
Exam.net QTI writer emits QTI 3.0, and one single-choice question exported
from the staging workspace imports into Exam.net with its key and points.

- **Package.** The manifest uses the QTI 3.0 content-package namespace
  `http://www.imsglobal.org/xsd/qti/qtiv3p0/imscp_v1p1`, item resources have
  type `imsqti_item_xmlv3p0` and the test resource `imsqti_test_xmlv3p0`.
  The test is `qti-assessment-test` with one `qti-test-part` and one visible
  `qti-assessment-section`, as in the HuleEduOS contract.
- **Items.** Every element and attribute the writer emits uses its QTI 3.0
  name in namespace `http://www.imsglobal.org/xsd/imsqtiasi_v3p0`
  (`qti-assessment-item`, `qti-response-declaration`, `base-type`,
  `qti-correct-response`, `qti-mapping`, `qti-map-entry` with `map-key` and
  `mapped-value`, `qti-choice-interaction` with `max-choices`, and so on),
  and response processing uses the v3p0 template URL. This applies to every
  item kind, so the package is coherent; per-type shape changes (images,
  separators, uniform mappings) belong to task 2.
- **Validation.** `examnet_qti_validation.py` reads the 3.0 names.
- **No 2.1 path.** The 2.1 namespace, names and template URLs are deleted.
  Both lanes (exam workspace and DigiExam converter) use the same writer.
- **Golden files.** `tests/fixtures/exam_conversion/reference-qti-package.zip`
  and `qti_standalone_item_xml_sha256.json` are regenerated from the 3.0
  writer.

## Contract Inputs

- ST-SKRIPT-39-09 terms Q1, Q2, Q4 and Q6.
- HuleEduOS `.codex/skills/examnet-qti-import/references/examnet-qti3-contract.md`
  (Package, Single choice) and the proven probe packages in Skriptoteket session
  `01a13be3-772e-73bb-9d8a-8cf2dd1d5df3` `evidence/probe-r1*/`.
- Writer: `domain/curated_apps/exam_conversion/examnet_qti_terms.py`,
  `examnet_qti_manifest.py`, `examnet_qti_assessment_test_xml.py`,
  `examnet_qti_item_xml.py`, `examnet_qti_xml.py`,
  `examnet_qti_inline_prompt.py`, `examnet_qti_validation.py`, and the
  remaining `examnet_qti*.py` modules that name QTI elements.
- Retained plan: Skriptoteket session `01a13c92-d70e-765f-ae36-b6583539e201`.

## Core Vertical And Performance

Teacher saves a single-choice question in the staging workspace, clicks the
QTI export, and the downloaded package imports into Exam.net as a
single-choice task with the correct option keyed and the item's points.
No performance concern: the writer's output size and work are unchanged.

## Validation

- Focused unit tests under `tests/unit/domain/curated_apps/exam_conversion/`
  and `tests/unit/domain/curated_apps/exam_workspace/` that cover the QTI
  writer, plus `tests/unit/application/curated_apps/test_exam_workspace_exports.py`
  and `test_exam_conversion_parity.py`, pass against the 3.0 output.
- Staging walk: export of a single-choice question, Exam.net import in the
  agent's own tab, readback of type, key and points through
  `/api/exams/automarked/<id>/questions`.

## Stop Conditions

- Exam.net rejects the package or imports the choice without its key.
- A 2.1 name or namespace has to stay for any lane.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                          |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T1  | The writer switches every emitted name to QTI 3.0 in this task, for all item kinds and both lanes; per-type shape changes follow in task 2 (story Q1, Q2, Q6). |
| T2  | The skeleton is proved by one single-choice question exported from the staging workspace and read back after Exam.net import (story Q4).                       |
