---
type: sprint
id: SPR-2026-02-24
title: "Sprint 2026-02-24: Tool data libraries v1"
status: planned
owners: "agents"
created: 2026-01-12
starts: 2026-02-24
ends: 2026-03-09
objective: "Enable per-user datasets and reusable file vault inputs for tool runs."
prd: "PRD-script-hub-v0.2"
epics: ["EPIC-14"]
stories: ["ST-14-35", "ST-14-36"]
adrs: ["ADR-0058", "ADR-0059"]
---

## Objective

Ship the first version of reusable, per-user tool data: datasets (structured lists) and a file vault (reusable inputs).

## Scope (committed stories)

- [ST-14-35: Tool datasets: per-user CRUD + picker](../stories/story-14-35-tool-datasets-crud-and-picker.md)
- [ST-14-36: User file vault: reusable uploads + picker](../stories/story-14-36-user-file-vault-and-picker.md)
  - Includes explicit "save artifact to vault" actions.

## Out of scope

- Action defaults/prefill (ST-14-23).
- First-class file references (ST-14-24).
- Sharing datasets/files across users (collaboration primitives).

## Decisions required (ADRs)

- ADR-0058: Tool datasets (proposed)
- ADR-0059: User file vault (proposed)

## Risks / edge cases

- Privacy: enforce strict per-user access boundaries.
- Storage caps: avoid unbounded growth; define retention and size limits.
- Soft delete requires clear UX to avoid confusion (deleted vs purged).
- UX: clarify dataset vs settings so users understand what is reused.

## Execution plan

1) Define persistence models + repositories (datasets + vault files).
2) Implement API endpoints + validation (CRUD + list).
3) Build tool run UI pickers (datasets + vault files) with clear empty states.
4) Runner integration: inject selected dataset into memory and stage vault files as inputs.
5) Add explicit "save artifact to vault" actions in run results.
6) Implement soft delete + restore + retention purge for vault files.

## Demo checklist

- Create a dataset and reuse it in a tool run.
- Select a vault file for a run without re-uploading it.
- Delete a vault file, restore it, and confirm the picker updates.

## Verification checklist

- `pdm run docs-validate`
- Tool run flow: dataset selection + vault file selection (manual check)

## Notes / follow-ups

- Add dataset suggestions UI to streamline saving from tool runs (ST-14-34).
