---
type: pr
id: PR-0181
title: "ST-27-04 follow-up: Smart-inställningar sittschemat wording fix"
status: done
owners: "agents"
created: 2026-03-31
updated: 2026-03-31
stories:
  - "ST-27-04"
tags: ["frontend", "docs", "ux", "swedish", "klassrumskartan"]
acceptance_criteria:
  - "Given the teacher opens `Smart-inställningar` in `Grupper`, when they inspect the classroom-aware compactness control, then the visible label reads `Sittschemat` and the surrounding helper copy uses straightforward teacher-facing Swedish."
  - "Given the teacher opens `Smart-inställningar` in `Sittplatser`, when they read the history and rules explanations, then the copy explains the behavior in plain Swedish instead of internal product wording."
  - "Given the follow-up is verified, when focused frontend, backend, docs, and live dev-stack checks run, then the updated wording is consistent across code, tests, and backlog docs."
---

## Problem

The Smart-settings copy around classroom-aware grouping and seating history drifted into stiff,
internal-sounding wording (`Sittning`, `väga in`, and similar phrases) that teachers should not
need to interpret.

## Goal

Rewrite the relevant Smart-settings copy into plain teacher-facing Swedish and align the visible
control label with the correct term `Sittschemat`.

## Non-goals

- Changing Smart grouping or Smart seating behavior.
- Reworking history defaults or first-run execution semantics.
- Renaming unrelated seating vocabulary outside this Smart-settings follow-up.

## Implementation plan

1. Update the grouping Smart-settings drawer so the visible control reads `Sittschemat`.
2. Rewrite the grouping and seating helper copy into shorter, clearer Swedish.
3. Refresh the linked smart-grouping docs so the approved wording matches the shipped UI.
4. Verify with focused tests, docs validation, and a live Playwright check against `:5173` + `:8000`.

## Test plan

- `pdm run fe-test -- --run src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/useSmartGroupingRun.spec.ts src/views/apps/useClassroomState.spec.ts`
- `pdm run pytest tests/unit/application/apps/classroom_planner/test_smart_grouping.py -q`
- `pdm run docs-validate`
- `pdm run python -m scripts.playwright_pr_0181_smart_settings_copy_check --base-url http://127.0.0.1:5173`

## Rollback plan

- Restore the previous wording if later review finds a repo-wide localization convention that this
  follow-up should conform to instead.
