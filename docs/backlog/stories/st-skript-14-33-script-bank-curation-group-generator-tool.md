---
type: story
id: ST-SKRIPT-14-33
title: Script bank curation + group generator tool
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-07-31'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: orchestrator
  decided_at: '2026-10-28'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'ST-SKRIPT-14-33#closeout'
epic: EPIC-SKRIPT-14
acceptance_criteria:
  - Given script bank seeding runs with profile=dev, when seeded, then curated + test tools are created in dev/staging DB.
  - Given script bank seeding runs with profile=prod, when seeded, then only curated tools are created (test tools are not seeded at all).
  - Given curated script bank tools are updated, when executed, then they read inputs/actions/settings via runner toolkit helpers and action field kinds use enum.
  - Given a roster file (CSV/XLSX) and a group size, when the group generator tool runs, then it outputs student groups and exports an artifact.
  - Given a class roster is saved in tool settings, when the tool runs again, then the teacher can select exactly one saved class and assign a user-provided group set name.
retired_ids:
  - ST-14-33
backlog_document_profile: contract-derived
---

## Slice Contract

Closed as done on 2026-10-28 under TASK-SKRIPT-REP-0056 D5, because its acceptance holds on main. The original story text below is kept as history; see Closeout.

## Context

We need a strict separation between curated production tools and dev/test tools, while keeping dev/staging seeded with
both sets for QA. At the same time, curated tools should demonstrate the latest runner toolkit helpers for inputs,
actions, and settings. A new teacher-facing “group generator” tool is also needed as a curated example.

## Epic Contract Slice

No separate material is recorded in the source snapshot.

## ADR Coverage

No separate material is recorded in the source snapshot.

## Contract Inputs

No separate material is recorded in the source snapshot.

## Tasks

- TASK-SKRIPT-14-33-01 (done)

## Verification

The source record did not define a separate section for this package heading.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                            |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | Closed as done on 2026-10-28 because the story's acceptance holds on main (orchestrator decision 2026-10-28, TASK-SKRIPT-REP-0056 D5); the Closeout section lists the evidence and the checks that were not run. |

## Live Verification Plan

No separate material is recorded in the source snapshot.

## Non-Goals

No separate material is recorded in the source snapshot.

## Notes

### Context

We need a strict separation between curated production tools and dev/test tools, while keeping dev/staging seeded with
both sets for QA. At the same time, curated tools should demonstrate the latest runner toolkit helpers for inputs,
actions, and settings. A new teacher-facing “group generator” tool is also needed as a curated example.

### Notes

- Curated set must include:
  - `demo_inputs.py`
  - `ist_vh_mejl_bcc.py`
  - `yrkesgenerator.py`
  - `markdown_to_docx.py`
  - `html_to_pdf_preview.py`
- Test/demo tools must not be seeded into production at all.
- Group generator tool requirements:
  - Accept CSV/XLSX (incl. Google Sheets export) with student names.
  - Accept group size input.
  - Optionally accept previous groups input to avoid repeats.
  - Persist class rosters in settings (memory.json) for reuse.
  - Allow selecting one saved class at a time and naming the group set.

## Decision And Assumption Ledger

The source snapshot is the governing record for the decisions and assumptions stated above.

## Plan Document Review

No separate material is recorded in the source snapshot.

## Story Closeout Review

No separate material is recorded in the source snapshot.

## Closeout

Closed as done on 2026-10-28 under TASK-SKRIPT-REP-0056 D5 (orchestrator closeout on code evidence). Its only child, TASK-SKRIPT-14-33-01, is done. Acceptance on main:

1. Profile `dev` seeds curated and test tools: `src/skriptoteket/cli/commands/seed_script_bank.py:79` makes `dev` the default and `:216-217` select the curated and test groups (10 entries, three of them test tools).
2. Profile `prod` seeds only curated tools: `:214-215` (7 entries, no test tool). The `--group` option (`:82-86`, `:212-213`) replaces the profile's set, so `--profile prod --group test` would seed the test tools; the criterion names only the profile.
3. Curated tools read inputs, actions and settings through toolkit helpers and closed-choice action fields use `enum`: `src/skriptoteket/script_bank/scripts/gruppgenerator/tool.py:16-21` and `:72`, `html_to_pdf_preview/tool.py:25-29`, `:140` and `:149`, `markdown_to_docx/inputs.py:6`, `yrkesgenerator/tool.py:8`; no `os.environ` or `getenv` use under `scripts/`.
4. Roster CSV or XLSX plus group size produces groups and an artifact: `gruppgenerator/tool.py:134-137`, `:243-246`, `:281` and `:297-299`; `roster.py:91-102`. A probe with a 6-name CSV and group size 3 produced 2 groups and a `grupper_*.txt` artifact.
5. One saved class and a group set name: the single-select `saved_class` field (`tool.py:62-75`), `group_set_name` (`:88-92`, `:283-288`). A probe with `saved_class=7B` and `group_set_name="Labb 2"` produced the groups "Labb 2 1" and "Labb 2 2".

Not checked: no real `seed-script-bank` run and no sandbox run (the probes replaced the toolkit readers with fakes), and the XLSX branch was not run. The production gruppgeneratorn is depublished on purpose (handoff, 2026-10-28); a plain reseed would publish it again (`seed_script_bank.py:87-90`, `seed_script_bank_entry.py:270`). The tool does not write class rosters to settings; it prints a JSON block for the teacher to paste into Settings (`tool.py:340-357`).
