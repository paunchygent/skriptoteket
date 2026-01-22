---
type: story
id: ST-19-05
title: "Runner result parser seam (V2)"
status: done
owners: "agents"
created: 2026-01-22
epic: "EPIC-19"
acceptance_criteria:
  - "Given a runner-based tool run completes, when outputs are parsed, then a dedicated result parser produces the ToolExecutionResult."
  - "Given the V2 parser is used, when result.json/stdout/stderr are mapped, then behavior matches current outputs (no contract change)."
  - "Given the parser seam exists, when runner tests execute, then they pass without behavior regressions."
dependencies:
  - "ADR-0065"
ui_impact: "No"
data_impact: "No"
---

## Context

EPIC-19 introduces Contract V3 with structured errors and state updates. We need a parser seam so V2 and V3 mappings
can coexist during migration, without changing Docker lifecycle code.

## Notes

- Refactor only (V2 behavior preserved). No contract change.
- Suggested module: `src/skriptoteket/infrastructure/runner/docker/result_parser.py`.
- PR tasks:
  - Add `V2RunnerResultParser` that wraps current `results.py` behavior.
  - Route `execution.py` and `adoption.py` through the parser for output mapping.
  - Keep `results.py` helper functions as the underlying implementation.
- Test plan:
  - Unit: parser maps result.json/stdout/stderr into `ToolExecutionResult` and errors as before.
  - Integration: `tests/unit/infrastructure/runner/test_docker_runner.py` remains green.
