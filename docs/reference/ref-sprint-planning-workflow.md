---
type: reference
id: REF-sprint-planning-workflow
title: "Retired sprint planning workflow"
status: deprecated
owners: "agents"
created: 2025-12-19
updated: 2026-04-06
topic: "sprint-planning"
---

Sprint docs are no longer a live planning shape in this repo.

## What changed

Planning should now flow through:

1. `PRD`
2. `ADR`
3. `EPIC`
4. `STORY`
5. `PR` backlog slices
6. target-based retained `REVIEW` docs when a decision gate is needed

## What to do instead

- Use epics and stories to describe the backlog.
- Use PR backlog docs to define narrow implementation slices.
- Use `docs/reference/ref-review-workflow.md` for the retained review model.
- Keep `.agents/handoff.md` current instead of maintaining a separate sprint plan.

## Legacy sprint docs

The existing files under `docs/backlog/sprints/` are preserved as historical planning records only.
They should not be treated as the current planning workflow and should not be copied forward into
new work.
