---
type: story
id: ST-10-03
title: "UI payload normalizer + storage on tool runs"
status: in_progress
owners: "agents"
created: 2025-12-19
epic: "EPIC-10"
acceptance_criteria:
  - "Given a contract v2 result, when normalized, then only allowlisted output kinds and actions are persisted to ui_payload"
  - "Given payload or state exceeds configured size budgets, when normalized, then deterministic truncation occurs and a system notice is added"
  - "Given the same input payload and policy, when normalized twice, then the produced ui_payload is byte-for-byte identical"
data_impact: "Add tool_runs.ui_payload JSONB (normalized, not raw)."
dependencies: ["ADR-0022", "ADR-0024"]
---

## Context

The platform must render tool outputs safely and consistently. Normalization is the enforcement point for:

- output/action allowlists
- size budgets
- deterministic behavior (unit-testable)
