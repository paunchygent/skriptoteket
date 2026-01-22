---
type: story
id: ST-19-04
title: "Runner request factory seam (V2)"
status: done
owners: "agents"
created: 2026-01-22
epic: "EPIC-19"
acceptance_criteria:
  - "Given a runner-based tool run, when Docker execution begins, then request construction is delegated to a dedicated request factory that returns a structured request object."
  - "Given the request factory is used, when inputs/action/files are prepared, then the env vars, manifest JSON, and workdir archive match current behavior (no contract change)."
  - "Given the request factory seam exists, when runner tests execute, then they pass without behavior regressions."
dependencies:
  - "ADR-0063"
ui_impact: "No"
data_impact: "No"
---

## Context

Runner input construction is currently split across helper functions. EPIC-19 replaces env-var payloads with
`/work/request.json`, so we need a clean seam that can swap request construction without touching the Docker lifecycle
logic.

## Notes

- Refactor only (V2 behavior preserved). No request.json, no contract changes.
- Suggested module: `src/skriptoteket/infrastructure/runner/docker/request_factory.py`.
- PR tasks:
  - Add `RunnerRequest` dataclass and `V2RunnerRequestFactory` for env/manifest/workdir assembly.
  - Route `execute_sync` to consume the request factory output instead of rebuilding inline.
  - Keep `prepare_execution_inputs` and `workdir_archive` behavior unchanged.
- Test plan:
  - Unit: request factory builds env/manifest/workdir identical to current behavior.
  - Integration: `tests/unit/infrastructure/runner/test_docker_runner.py` remains green.
