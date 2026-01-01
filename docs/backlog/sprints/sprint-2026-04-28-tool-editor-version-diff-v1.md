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

## Before / After

**Before**

- Reviewers can navigate version history, but “what changed” requires manual copy/paste or eyeballing.
- There is no reusable diff preview surface for other workflows (e.g., AI proposed changes).

**After**

- Reviewers can compare source code, entrypoint, schemas, and instructions with a first-class diff view.
- Compare targets are sensible by default and can be deep-linked without leaking access.
- The diff viewer is implemented as a reusable primitive that can later be reused for AI “proposed changes” preview.

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

## Pacing checklist (suggested)

- [ ] Implement the diff viewer as a reusable component that can compare arbitrary before/after text blobs.
- [ ] Build the version compare UI on top of the diff viewer (code + schemas + instructions).
- [ ] Add compare target selection rules + deep links (including which field is being compared).
- [ ] Enforce permissions and keep large diffs usable (copy/download of compared content).

## Demo checklist

- Select a version and compare against previous/derived version.
- Show review action decisions (publish/reject) with diff visible.

## Verification checklist

- `pdm run docs-validate`
- `pdm run lint`
- `pdm run test`
- Live functional check (backend + SPA dev); record steps in `.agent/handoff.md`.
