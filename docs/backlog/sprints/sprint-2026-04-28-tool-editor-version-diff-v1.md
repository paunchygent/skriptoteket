---
type: sprint
id: SPR-2026-04-28
title: "Sprint 2026-04-28: Tool editor version diff v1"
status: planned
owners: "agents"
created: 2025-12-29
starts: 2026-04-28
ends: 2026-05-11
objective: "Improve review/publish confidence by adding a first-class diff/compare view across tool versions."
prd: "PRD-tool-authoring-v0.1"
epics: ["EPIC-14"]
stories: ["ST-14-17", "ST-14-18"]
---

## Objective

Reduce review friction and mistakes by making “what changed” obvious before publish/reject actions.

Reference context: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`

## Scope (committed stories)

- [ST-14-17: Editor version compare/diff view (code + schemas + instructions)](../stories/story-14-17-editor-version-diff-view.md)
- [ST-14-18: Reviewer navigation improvements (compare targets + deep links)](../stories/story-14-18-editor-review-navigation-and-compare.md)

## Out of scope

- Full “review queue” workflow changes.
- Automated review checks beyond schema validation.

## Decisions required (ADRs)

- Confirm comparison target rules (previous visible version vs derived_from_version_id).

## Risks / edge cases

- Diff rendering performance for large scripts.
- Permissions: ensure reviewers only compare versions they’re allowed to view.

## Demo checklist

- Select a version and compare against previous/derived version.
- Show review action decisions (publish/reject) with diff visible.

## Verification checklist

- `pdm run docs-validate`
- `pdm run lint`
- `pdm run test`
- Live functional check (backend + SPA dev); record steps in `.agent/handoff.md`.
