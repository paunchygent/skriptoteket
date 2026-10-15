---
type: task
id: TASK-SKRIPT-39-05-11
title: Rewire the labeling feasibility report to the v14 batch recordings
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-15'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- The evaluate command scores the converter baseline from the committed v14 docx_w batch recordings for all eight corpus exams, with no path argument
- No reference to round1.json, the old retained-context recordings path or the --converter-recordings flag remains
- ruff and mypy pass on scripts/labeling_feasibility and one evaluate run on an empty evidence directory completes with no provider calls
story: ST-SKRIPT-39-05
backlog_document_profile: contract-derived
---

## Implementation Contract

Repairs two stale integrations in the experiment package
`scripts/labeling_feasibility/` that TASK-SKRIPT-39-05-10 left behind when it
replaced the converter recordings with the v14 batch recordings.

- `__main__.py` defaults `--converter-recordings` to `_CONVERTER_RECORDINGS`, a
  retained-context path on one Mac from TASK-SKRIPT-39-05-03.
- `report.build_report` reads one whole-exam `round1.json` per exam from that
  path to score the "converter today" baseline.
- `postconv.py` already discovers the current recordings:
  `postconv.RECORDINGS` and `postconv.RECORDED_CONVERSIONS` (8 exams, 64
  `docx_w*.json` batches, first-attempt `w1` batches plus `w2` per-question
  retries).

The report stays: it is the only scorer of saved labeling and post-conversion
runs. The baseline joins the `items` of every `docx_w*.json` batch of an exam
into one converted exam and scores it with `evaluate.converter_baseline`.

## Contract Inputs

- `tests/fixtures/exam_conversion/docx_key_provenance_v14/` and its README.
- Shape check 2026-10-15: no source anchor appears in more than one batch of
  an exam; every v14 item carries `kind`, `points`, `choices` and gap
  `body[].segments[].accepted_values`, the fields `converter_baseline` and
  `_keyed_equal` read.

## Core Vertical And Performance

One function in `report.py` assembles an exam's converted items from
`postconv.RECORDED_CONVERSIONS`; `build_report` takes only the evidence
directory. The CLI flag and path constant go away. The Markdown baseline line
names the v14 recordings. Reading 64 small JSON files is negligible.

## Validation

- `pdm run ruff check scripts/labeling_feasibility` and
  `pdm run mypy scripts/labeling_feasibility`.
- `pdm run python -m scripts.labeling_feasibility evaluate --evidence-dir
  <scratch dir>` on an empty directory: no provider calls, eight
  `converter_today` lines with plausible non-zero kind and keyed accuracy.

## Stop Conditions

- The v14 item shape cannot be scored by `converter_baseline` without
  rewriting it.
- A change needs a term outside this contract.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D1 | Keep the report and rewire it to the v14 recordings rather than delete it (user decision 2026-10-15). |
| D2 | The baseline for an exam is the joined items of all its `docx_w*.json` batches, retries included (parent decision 2026-10-15, no anchor overlap found). |
| D3 | Remove `_CONVERTER_RECORDINGS` and `--converter-recordings` with no fallback; the repo keeps no backward compatibility (CLAUDE.md, parent decision 2026-10-15). |
| D4 | A Sol 6.1 implementation-specialist implements and a Sol 6.1 ruthless-reviewer reviews (user decision 2026-10-15). |
