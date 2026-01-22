---
type: story
id: ST-19-06
title: "Runner contract selection seam (V2 default)"
status: ready
owners: "agents"
created: 2026-01-22
epic: "EPIC-19"
acceptance_criteria:
  - "Given a runner execution starts, when a contract selector is applied, then the V2 request factory and V2 result parser are chosen by default."
  - "Given the selector is configurable, when a non-default selection is introduced later, then V2 remains the default until explicitly switched."
  - "Given the selector seam exists, when runner tests execute, then they pass without behavior regressions."
dependencies:
  - "ST-19-04"
  - "ST-19-05"
ui_impact: "No"
data_impact: "No"
---

## Context

To avoid a big-bang migration for Contract V3, we need a single selection point that chooses request construction and
result parsing strategies. This keeps V2 as the default while allowing V3 to be introduced safely.

## Notes

- Refactor only (V2 behavior preserved). No contract change.
- Suggested location: `src/skriptoteket/infrastructure/runner/docker/runner.py` or a small selector module.
- PR tasks:
  - Add a contract selector that chooses request factory + result parser (V2 default).
  - Wire selector into the Docker runner orchestrator (`runner.py`).
  - Keep selection surface minimal (single switch or config hook).
- Test plan:
  - Unit: selector returns V2 factory/parser by default.
  - Integration: `tests/unit/infrastructure/runner/test_docker_runner.py` remains green.
