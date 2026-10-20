---
type: adr
id: ADR-SKRIPT-0093
title: A saved file the app cannot read is offered for download or removal, and format changes ship with an upgrade step
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-20'
status: accepted
deciders:
  - user
links:
  governing:
    - TASK-SKRIPT-41-02-06
---

## Context

Every stored native exam document names its format version in `schema_version`
(`native_exam_document_v<N>`). The reader accepted only the current version, so an exam saved in
an older format could not be opened, and the teacher had no way to keep or remove it. TASK-SKRIPT-41-02-05
handled the same case for a guest draft held in the browser.

The user decided this rule on 2026-10-20 in the Hemma orchestrator session; it is accepted through
`agent-planning:user-closure-gate` on that decision.

## Decision

- **One rule.** A file the app cannot read is never retried forever and never deleted silently.
  The teacher sees that it cannot be opened and gets two actions: download it, or remove it.
  Download gives the stored file unchanged, the exam and its pictures in one zip. Remove is the
  teacher's own action and moves a saved exam to the papperskorg like any other Mina filer file.
- **The oldest readable version.** `OLDEST_READABLE_NATIVE_EXAM_DOCUMENT_VERSION` in
  `domain/curated_apps/exam_workspace/native_exam_document_versions.py` names the oldest format
  version the app reads. Every stored document below it falls under the rule. Raising it is one
  deliberate code edit; nothing is deleted when it rises.
- **The upgrade-step contract.** After release, every format change ships with one upgrade step
  from the previous version to the new one, registered in `NATIVE_EXAM_DOCUMENT_UPGRADE_STEPS`,
  and one saved sample file of the previous version in
  `tests/fixtures/exam_workspace/document_versions/`. The server runs the steps in order whenever
  it reads a stored document, through `parse_native_exam_document`.
- **The safeguard test.** `test_native_exam_document_versions.py` fails unless there is an upgrade
  step and a sample for every version from the oldest readable one up to the current one, and every
  sample reads into the current format. Before release no upgrade steps exist: the oldest readable
  version equals the current one, and the chain is empty.

## Non-Decisions

- No upgrade step is written by this decision.
- The undo history's own stored steps follow the same reader; how a raise treats history steps
  older than the new oldest readable version is decided at the first raise after release.

## Consequences

- `exam_index.document_format_version` records each saved exam's format version, so the saved list
  knows which exams it can open without reading their files.
- A format change after release costs one upgrade step and one sample file; the safeguard test
  blocks a change that skips them.
- Before release, a format change makes every older file unreadable, and the teacher downloads or
  removes it.
