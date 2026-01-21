---
type: story
id: ST-06-16
title: "Backend SRP refactor of god modules"
status: ready
owners: "agents"
created: 2026-01-21
epic: "EPIC-06"
acceptance_criteria:
  - "Targeted backend modules are split into smaller units (generally <=400–500 LOC) with clear single responsibilities."
  - "DDD/Clean boundaries are preserved: domain stays pure, web stays thin, infra implements protocols."
  - "Protocol-first DI remains intact; repositories still avoid committing and UoW owns transactions."
  - "Existing behavior is preserved and covered by updated/added tests."
  - "Docs and module entrypoints are updated to reflect the new structure."
---

## Context

Several backend modules have grown into large, multi-responsibility files that are harder to reason about and test.
We need a clean refactor pass that prioritizes clarity and SRP over minimizing churn.

## Notes

- This is a refactor story: no feature behavior changes.
- Prefer extraction into focused modules over large helper sections.
