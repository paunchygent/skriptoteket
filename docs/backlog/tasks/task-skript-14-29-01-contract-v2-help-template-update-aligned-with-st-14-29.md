---
type: task
id: TASK-SKRIPT-14-29-01
title: Contract v2 help + template update (aligned with ST-14-29)
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
story: ST-SKRIPT-14-29
task_kind: story
acceptance_criteria:
- Given a new tool is created, when the editor opens, then the template explains tool.py,
  input_schema.json, and settings_schema.json with short, actionable examples.
- Given a user opens the editor help modal, then it explains inputs vs settings, memory.json,
  SKRIPTOTEKET_INPUTS, and output contract v2.
- Given a user hovers on 'Begar publicering' or is blocked by validation, then they
  see contextual help and a link to the long-form onboarding doc.
- A dedicated long-form onboarding doc exists and is linked from help surfaces.
- AI context prompt templates are updated so injected shards reflect the current contract
  guidance (inputs vs settings, env vars, outputs).
---

## Context
### Problem
Tool authors lack a single, discoverable explanation of the contract v2
expectations (inputs vs settings, memory.json, outputs/next_actions/state),
causing confusion and incorrect implementations.

## Decision And Assumption Ledger
The source record did not define a separate section for this package heading.

## Story Contract Slice
### Goal
- Provide clear in-editor help surfaces without adding new panels.
- Update the starter template to teach the contract and schemas.
- Publish a long-form onboarding doc that consolidates contract v2 guidance.
### Non-goals
- Adding new editor panels or workflow states.
- Changing contract v2 behavior or field kinds.

## Contract Inputs
The source record did not define a separate section for this package heading.

## Plan
### Implementation plan
1) Long-form doc
   - Add a reference doc (e.g. `docs/reference/ref-tool-developer-contract-v2.md`)
     that consolidates: inputs vs settings, env vars, memory.json, outputs,
     next_actions/state, sandbox vs production differences, and size limits.

2) Help surfaces
   - Update the editor help modal to include the new guidance and link to the
     long-form doc.
   - Add hover help on the submit-review CTA and a focused toast when blocked.

3) Template update
   - Update the new-tool template to include short examples for:
     - tool.py
     - input_schema.json
     - settings_schema.json
   - Align template sections with ST-14-29 bundle v1 headers.

4) AI context prompt templates (system prompts + injected fragments)
   - System prompt templates:
     - `src/skriptoteket/application/editor/system_prompts/inline_completion_v1.txt`
     - `src/skriptoteket/application/editor/system_prompts/edit_suggestion_v1.txt`
   - Template registry + composition:
     - `src/skriptoteket/application/editor/prompt_templates.py`
     - `src/skriptoteket/application/editor/prompt_composer.py`
   - Injected fragments ("shards"):
     - `src/skriptoteket/application/editor/prompt_fragments.py`
   - Update wording to reflect clarified contract guidance
     (inputs vs settings, SKRIPTOTEKET_INPUTS vs memory.json, outputs/next_actions/state).
### Test plan
- Manual: verify help modal content + hover + toast links.
- Manual: create new tool and confirm the template includes contract guidance.
### Rollback plan
- Remove the new doc and revert template/help copy changes.

## Implementation Steps
The source record did not define a separate section for this package heading.

## Proof
The source record did not define a separate section for this package heading.

## Validation
The source record did not define a separate section for this package heading.

## Stop Conditions
The source record did not define a separate section for this package heading.

## Lessons Learned
The source record did not define a separate section for this package heading.

## Notes
The source record did not define a separate section for this package heading.

## Plan Document Review
The source record did not define a separate section for this package heading.

## Implementation Review
The source record did not define a separate section for this package heading.
