---
type: story
id: ST-06-01
title: "Improve test coverage for Admin Scripting and Docker Runner"
status: ready
owners: "agents"
created: 2025-12-16
epic: "EPIC-06"
acceptance_criteria:
  - "admin_scripting.py coverage increases from 41% to >80%"
  - "docker_runner.py coverage increases from 46% to >80%"
  - "All tests pass without regressions"
---

## Context

Recent coverage reports identified two critical modules with low test coverage:
1. `src/skriptoteket/web/pages/admin_scripting.py` (41%): Handles critical admin workflows like editing, saving drafts, and version history.
2. `src/skriptoteket/infrastructure/runner/docker_runner.py` (46%): The core execution engine for user scripts.

Improving coverage in these areas is essential for system stability and security.

## Plan for `admin_scripting.py`

**Current State:**
- Existing tests (`test_admin_scripting_review_routes.py`) cover publish and request-changes flows.
- Missing coverage:
    - GET `/admin/tools/{tool_id}`: Rendering logic, permission checks, starter template generation.
    - POST `/admin/tools/{tool_id}/versions`: Creating new drafts (including error handling).
    - POST `/admin/tool-versions/{version_id}/save`: Saving drafts (including concurrency checks).
    - GET `/admin/tool-versions/{version_id}`: Version rendering logic.
    - Error handling paths (e.g., tool not found, version not visible).

**Proposed Tests:**
1. **Test Editor Rendering:**
    - GET tool (admin/contributor).
    - GET specific version.
    - Verify correct template context (versions list, selected version, source code).
2. **Test Draft Creation:**
    - POST create draft (success).
    - POST create draft with invalid data (validation error UI feedback).
    - POST create draft when derived version missing.
3. **Test Draft Saving:**
    - POST save draft (success).
    - POST save draft with conflict (stale parent version).
4. **Test Permissions:**
    - Verify contributors can only access their own/published tools (if applicable) or follow RBAC.

## Plan for `docker_runner.py`

**Current State:**
- 46% coverage suggests happy paths might be tested via integration tests, but edge cases and error handling in the runner are likely missing.
- `DockerToolRunner` has complex logic for container management, volume mounting, and output extraction.

**Proposed Tests (Unit/Mocked):**
Since real Docker tests are slow, we should use `unittest.mock` to mock the `docker` python client.

1. **Test Execution Flow (Mocked):**
    - Verify container creation arguments (image, limits, volumes).
    - Verify tar archive injection (input files).
    - Verify execution wait/timeout handling.
    - Verify output extraction (stdout, stderr, result.json).
2. **Test Error Handling:**
    - Docker API errors (create/start failure).
    - Timeout handling (container kill).
    - Malformed result.json (contract violation).
    - Missing result.json.
    - Artifact extraction failures.
3. **Test Security/Limits:**
    - Verify limits are passed to Docker container config.
    - Verify input filename sanitization.

## Implementation Steps

1. Create `tests/integration/web/test_admin_scripting_editor_routes.py`.
2. Create `tests/unit/infrastructure/runner/test_docker_runner.py`.
3. Implement tests iteratively, checking coverage after each batch.
