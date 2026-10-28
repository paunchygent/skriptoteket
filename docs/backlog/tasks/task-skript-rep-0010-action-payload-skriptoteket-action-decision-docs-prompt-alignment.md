---
type: task
id: TASK-SKRIPT-REP-0010
title: 'Action payload: SKRIPTOTEKET_ACTION decision + docs/prompt alignment'
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-07-31'
status: canceled
closeout_review:
  record: inline
  status: not_required
  decided_at: '2026-10-28'
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: 'The user decided on 2026-10-28 (TASK-SKRIPT-REP-0055 D2) to cancel this task as superseded; the Closeout section records what replaced or removed the work.'
task_kind: repository
acceptance_criteria:
  - ADR-0024/0038/0039 explicitly record the decision to transport action payload via SKRIPTOTEKET_ACTION (not action.json).
  - System prompts no longer mislead tool authors about action inputs (initial run inputs vs action runs are clearly separated).
  - stakeholders/guide-teacher-developers.md is updated to match Contract v2 (dict with outputs/next_actions/state; inputs via env vars).
  - Docs are cross-linked to EPIC-14 + ST-14-19 so implementation work is easy to discover.
backlog_document_profile: contract-derived
---

## Implementation Contract

Canceled on 2026-10-28 under TASK-SKRIPT-REP-0055 D2. The original contract below is kept as history; see Closeout.

## Contract Inputs

The source record did not define a separate section for this package heading.

## Core Vertical And Performance

The source record did not define a separate section for this package heading.

## Context

The source does not provide a separate context section; no additional context is recorded.

## Impact And Escalation

The source does not provide a separate impact and escalation section; no additional impact and escalation is recorded.

## Decision And Assumption Ledger

The source does not provide a separate decision and assumption ledger section; no additional decision and assumption ledger is recorded.

## Plan

### Source: Implementation plan

1. ADR updates (decision)

   - Update `docs/adr/adr-0024-tool-sessions-and-ui-payload-persistence.md` with the `SKRIPTOTEKET_ACTION` decision.
   - Update `docs/adr/adr-0038-editor-sandbox-interactive-actions.md` and `docs/adr/adr-0039-session-file-persistence.md`
     to match the new action payload transport.

2. Prompt alignment (avoid “wrong code”)

   - Update the system prompt templates so they clearly distinguish:
     - initial run form inputs (`SKRIPTOTEKET_INPUTS`)
     - action runs (`SKRIPTOTEKET_ACTION`; prefer runner toolkit helpers)

3. Stakeholder guide cleanup

   - Update `stakeholders/guide-teacher-developers.md` so external AI guidance matches:
     - Contract v2 return shape (dict with `outputs/next_actions/state`)
     - env vars (`SKRIPTOTEKET_INPUT_MANIFEST`, `SKRIPTOTEKET_INPUTS`, `SKRIPTOTEKET_MEMORY_PATH`)

4. Cross-links

   - Ensure EPIC-14 and ST-14-19 are referenced from ADRs and this PR doc.

## Implementation Steps

The source does not provide a separate implementation steps section; no additional implementation steps is recorded.

## Proof

### Source: Test plan

- Run docs validation: `pdm run docs-validate`

## Validation

The source does not provide a separate validation section; no additional validation is recorded.

## Stop Conditions

### Source: Non-goals

- Implementing the runner toolkit (ST-14-19).
- Changing runtime behavior of tool execution in this PR.

### Source: Rollback plan

- Revert the docs + prompt copy changes.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                  |
| --- | -------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | Canceled on 2026-10-28 by the user's decision (TASK-SKRIPT-REP-0055 D2); the Closeout section names what replaced or removed the work. |

## Lessons Learned

The source does not provide a separate lessons learned section; no additional lessons learned is recorded.

## Notes

The source does not provide a separate notes section; no additional notes is recorded.

### Source: Problem

Tool authors (and AI assistants) have conflicting guidance about:

- where action inputs come from (env vs `action.json`)
- how files/paths behave in the runner (`files[].path` absolute vs relative)
- what the Contract v2 return shape is (dict vs list)

This creates avoidable handhavandefel, brittle scripts, and prompt drift.

### Source: Goal

- Record the platform decision: action payload will move to `SKRIPTOTEKET_ACTION` (ADR-0024).
- Align high-signal help surfaces (system prompts + teacher guide) with the current Contract v2 mental model.
- Make the follow-up implementation work (ST-14-19 runner toolkit) easy to execute without re-litigating the contract.

## Readiness

The source does not provide a separate readiness section; no additional readiness is recorded.

## Closeout

The source does not provide a separate closeout section; no additional closeout is recorded.

## Closeout

Canceled on 2026-10-28 under TASK-SKRIPT-REP-0055 D2.

Cancelled as superseded. The criterion to record `SKRIPTOTEKET_ACTION` as the action transport was decided the other way: ADR-SKRIPT-0063 (accepted) makes `/work/request.json` the runner request envelope, ADR-0024 section 6, ADR-0038 and ADR-0039 describe it, and commits 82cc14500 and a33fba397 removed the JSON environment variables (`src/skriptoteket/infrastructure/runner/docker/env.py`, `runner/skriptoteket_toolkit.py`). The editor system prompts and `prompt_fragments.py` already describe request.json and toolkit helpers. The teacher-guide update (criterion 3) is not done and is dropped with this task unless a new task takes it. Stale guidance stays and has no owner yet: `stakeholders/guide-teacher-developers.md:159` still tells scripts to read `SKRIPTOTEKET_INPUTS`, a variable that is no longer set, and `frontend/apps/skriptoteket/src/composables/editor/skriptoteketMetadata.ts:58` has the same wording.

Correction on 2026-10-28 under TASK-SKRIPT-REP-0056 D8: the stale guidance named above is corrected. The example in `stakeholders/guide-teacher-developers.md` now reads its inputs with `from skriptoteket_toolkit import read_inputs`, and the Swedish help text of `read_inputs`, `read_input_manifest` and `read_action` in `skriptoteketMetadata.ts` (lines 58, 65 and 79) names the `/work/request.json` envelope instead of `SKRIPTOTEKET_INPUTS`, `SKRIPTOTEKET_INPUT_MANIFEST` and `SKRIPTOTEKET_ACTION`; its spec asserts `request.json`. Other places that still name the removed variables, outside D8: the sandbox input panel text (`SandboxInputPanel.vue:104`), the Playwright editor smoke check (`scripts/playwright_ui_editor_smoke.py:315`) and several active reference and runbook documents (the runner contract v3 reference, the tool editor DX review, the AI script generation knowledge base, the runner image smoke-test runbook).
