---
type: task
id: TASK-SKRIPT-REP-0037
title: Multi-file script-bank tool bundles and the split of four over-long tools
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-11'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
- A script-bank tool version can carry a bundle (entrypoint plus its own modules and data files); the seeder stores a tool's folder, and the runner makes only that tool's bundle directory importable.
- gruppgenerator, html_to_pdf_preview, markdown_to_docx and yrkesgenerator ship as bundles whose files are each under 500 lines, and each runs through the real runner with unchanged outputs.
- Single-file tools and every existing reader of a tool version's source keep working without new UI.
backlog_document_profile: contract-derived
---

## Implementation Contract

Four script-bank tools in `src/skriptoteket/script_bank/scripts/` are single
files over 500 lines: `gruppgenerator.py` (595), `html_to_pdf_preview.py`
(979), `markdown_to_docx.py` (715) and `yrkesgenerator.py` (683). The runner
loads one file, so they cannot be split today. This task adds tool-owned
bundles and splits the four tools.

- **Bundle.** A tool version can carry its entrypoint plus its own modules and
  data files. The seeder stores a tool's folder. The request factory writes
  the bundle into `/work`, and the runner makes only the tool's own bundle
  directory importable. The shared runner gains no tool code.
- **Storage.** The storage shape (extra rows, one archive column or a JSON
  file map) is chosen by what the existing persistence and read paths need,
  and lands through a migration that follows the repository's migration
  rules.
- **Splits.** Each tool splits by the responsibilities named in finding N2 of
  the 39-05-01 Boy Scout rereview. The career data and HTML template in
  `yrkesgenerator.py` become a data module and a template file.
- **ADR.** After implementation, an ADR records the built design with status
  proposed.

## Contract Inputs

- User decision, 2026-10-11: the four tools stay single files only until this
  task, which runs right after TASK-SKRIPT-39-05-01; the design is decided
  quickly and the ADR is written afterwards from the result.
- `docs/reference/ref-skript-general-runner-tool-code-modularization-map-*.md`
  ("Direction B": tool-owned bundles per version).
- Current single-file path: `cli/commands/seed_script_bank.py:394-396`,
  `infrastructure/db/models/tool_version.py:28`, `request_factory.py:17-19,106`,
  `execution.py:127,137`, `_runner.py:201-207,267`.

## Core Vertical And Performance

The core vertical is a seeded bundled tool executed by the real runner in its
container. Bundle size adds to stored version size and request transfer; keep
it to the tool's own files.

## Validation

`pdm run lint`, `pdm run typecheck` and the affected tests. Each split tool
runs through the real runner on real input.

## Stop Conditions

- A reader of `source_code` (script editor, version views, Mina filer or
  other) cannot handle a bundled version without new UI.
- The bundle mechanism would need the shared runner to import tool code or
  widen what `/work` exposes beyond the tool's bundle directory.

## Decided Contract Terms

| ID | Decided contract term |
| --- | --- |
| D1 | A tool version carries a tool-owned bundle; the shared runner does not grow. |
| D2 | Only the tool's own bundle directory is importable; single-file tools keep working unchanged. |
| D3 | The four tools split into files under 500 lines each, by the responsibilities in N2; career data and template become a data module and a template file. |
| D4 | Storage shape follows the existing persistence and read paths, through a migration. |
| D5 | The ADR is written after implementation from what was built, status proposed, and reviewed by the advisor. |
| D6  | The script editor and version views show every file of a bundled version, entrypoint first, and the editor edits and saves them together as one new version (user decision 2026-10-11, resolving the source-code reader stop condition). |
