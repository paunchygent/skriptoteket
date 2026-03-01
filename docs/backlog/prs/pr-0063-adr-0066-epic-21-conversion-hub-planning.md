---
type: pr
id: PR-0063
title: "Conversion Hub: ADR-0066 + EPIC-21 planning scaffold"
status: ready
owners: "agents"
created: 2026-03-01
updated: 2026-03-01
stories:
  - "ST-21-01"
  - "ST-21-02"
tags: ["docs", "planning", "curated-apps"]
acceptance_criteria:
  - "Docs-as-code scaffolds exist for ADR-0066, EPIC-21, ST-21-01, ST-21-02, and REV-EPIC-21."
  - "All new docs are indexed in `docs/index.md` and `pdm run docs-validate` passes."
---

## Problem

We need reviewable, contract-valid planning artifacts before implementing a new curated app surface that replaces a
production tool script.

## Goal

- Add ADR + epic/story/review scaffolds for the Conversion Hub work.
- Make ordering explicit via checkboxes (story order in epic; PR task order in stories).
- Keep docs index complete.

## Non-goals

- No production code changes.

## Implementation plan

- [ ] Add `docs/adr/adr-0066-...`
- [ ] Add `docs/backlog/epics/epic-21-...`
- [ ] Add stories `ST-21-01` and `ST-21-02` with PR task checklists
- [ ] Add review `REV-EPIC-21`
- [ ] Update `docs/index.md` to include all new docs
- [ ] Run `pdm run docs-validate`

## Test plan

- `pdm run docs-validate`

## Rollback plan

- Revert the doc additions if review rejects the epic/ADR.
