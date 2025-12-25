---
type: story
id: ST-06-09
title: "Playwright test isolation: prevent source code pollution"
status: ready
owners: "agents"
created: 2025-12-25
epic: "EPIC-06"
acceptance_criteria:
  - "All Playwright tests that modify tool source code restore original state after completion"
  - "Tests use dedicated test tools instead of polluting demo-next-actions"
  - "Running any Playwright test does not require manual cleanup afterward"
  - "New demo tools created: demo-regression-table, demo-settings-test"
---

## Context

Playwright E2E tests modify `demo-next-actions` tool source code without cleanup, causing confusing state for subsequent manual testing.

### Problem

When running Playwright tests, they create drafts or publish versions with test-specific source code. After tests complete, this modified code persists, causing:

1. Manual testing shows unexpected behavior (no `next_actions` buttons)
2. Developer confusion about why the demo tool doesn't work
3. Need to run `pdm run seed-script-bank --sync-code` after every Playwright run

## Audit Results

| Script | Modifies Source | Restores | Severity |
|--------|-----------------|----------|----------|
| `playwright_st_11_07_spa_tool_run_e2e.py` | Creates draft via API | NO | HIGH |
| `playwright_st_12_03_personalized_tool_settings_e2e.py` | Publishes new version | NO | CRITICAL |
| `playwright_st_12_02_native_pdf_output_helper_e2e.py` | Modifies CodeMirror | YES | OK |
| Others | Read-only | N/A | OK |

## Root Cause

### playwright_st_11_07_spa_tool_run_e2e.py (lines 126-139)

Creates draft via API with `regression_script` that has `next_actions: []`:

```python
draft = context.request.post(
    f"{base_url}/api/v1/editor/tools/{tool_id}/draft",
    data=json.dumps({"source_code": regression_script, ...})
)
```

No cleanup after test.

### playwright_st_12_03_personalized_tool_settings_e2e.py (lines 193-199)

Modifies source AND publishes:

```python
_set_codemirror_value(page, tool_code)
_save_source(page)
_submit_for_review(page)
_publish(page)
```

No cleanup. Publishes modified code!

## Implementation Plan

### Recommended: Create dedicated test tools

Rationale:
- Cleanup code is fragile (test failure = dirty state)
- Dedicated tools are explicit about their purpose
- No risk of polluting production demo tools
- Tests become self-contained

### New tools needed

1. `demo-regression-table` - For ST-11-07 column order test
2. `demo-settings-test` - For ST-12-03 personalized settings test

### Migration steps

1. Create `demo_regression_table.py` in script_bank with the regression script
2. Create `demo_settings_test.py` with settings schema
3. Update `playwright_st_11_07_spa_tool_run_e2e.py` to use new tool
4. Update `playwright_st_12_03_personalized_tool_settings_e2e.py` to use new tool
5. Add tools to seed script manifest
6. Remove source modification code from tests

## Files to Create/Modify

| File | Action |
|------|--------|
| `src/skriptoteket/script_bank/scripts/demo_regression_table.py` | NEW |
| `src/skriptoteket/script_bank/scripts/demo_settings_test.py` | NEW |
| `src/skriptoteket/script_bank/manifest.py` | Add new tools |
| `scripts/playwright_st_11_07_spa_tool_run_e2e.py` | Use new tool, remove source modification |
| `scripts/playwright_st_12_03_personalized_tool_settings_e2e.py` | Use new tool, remove source modification |

## Immediate Workaround

Until fixed, developers must run after Playwright tests:

```bash
pdm run seed-script-bank --sync-code
```
