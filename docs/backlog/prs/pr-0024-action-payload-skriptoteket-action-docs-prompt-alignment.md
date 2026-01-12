---
type: pr
id: PR-0024
title: "Action payload: SKRIPTOTEKET_ACTION decision + docs/prompt alignment"
status: ready
owners: "agents"
created: 2026-01-12
updated: 2026-01-12
stories:
  - "ST-14-19"
tags: ["docs", "backend", "ai", "ux"]
acceptance_criteria:
  - "ADR-0024/0038/0039 explicitly record the decision to transport action payload via SKRIPTOTEKET_ACTION (not action.json)."
  - "System prompts no longer mislead tool authors about action inputs (initial run inputs vs action runs are clearly separated)."
  - "stakeholders/guide-teacher-developers.md is updated to match Contract v2 (dict with outputs/next_actions/state; inputs via env vars)."
  - "Docs are cross-linked to EPIC-14 + ST-14-19 so implementation work is easy to discover."
---

## Problem

Tool authors (and AI assistants) have conflicting guidance about:

- where action inputs come from (env vs `action.json`)
- how files/paths behave in the runner (`files[].path` absolute vs relative)
- what the Contract v2 return shape is (dict vs list)

This creates avoidable handhavandefel, brittle scripts, and prompt drift.

## Goal

- Record the platform decision: action payload will move to `SKRIPTOTEKET_ACTION` (ADR-0024).
- Align high-signal help surfaces (system prompts + teacher guide) with the current Contract v2 mental model.
- Make the follow-up implementation work (ST-14-19 runner toolkit) easy to execute without re-litigating the contract.

## Non-goals

- Implementing the runner toolkit (ST-14-19).
- Changing runtime behavior of tool execution in this PR.

## Implementation plan

1) ADR updates (decision)
   - Update `docs/adr/adr-0024-tool-sessions-and-ui-payload-persistence.md` with the `SKRIPTOTEKET_ACTION` decision.
   - Update `docs/adr/adr-0038-editor-sandbox-interactive-actions.md` and `docs/adr/adr-0039-session-file-persistence.md`
     to match the new action payload transport.

2) Prompt alignment (avoid “wrong code”)
   - Update the system prompt templates so they clearly distinguish:
     - initial run form inputs (`SKRIPTOTEKET_INPUTS`)
     - action runs (`SKRIPTOTEKET_ACTION`; prefer runner toolkit helpers)

3) Stakeholder guide cleanup
   - Update `stakeholders/guide-teacher-developers.md` so external AI guidance matches:
     - Contract v2 return shape (dict with `outputs/next_actions/state`)
     - env vars (`SKRIPTOTEKET_INPUT_MANIFEST`, `SKRIPTOTEKET_INPUTS`, `SKRIPTOTEKET_MEMORY_PATH`)

4) Cross-links
   - Ensure EPIC-14 and ST-14-19 are referenced from ADRs and this PR doc.

## Test plan

- Run docs validation: `pdm run docs-validate`

## Rollback plan

- Revert the docs + prompt copy changes.
