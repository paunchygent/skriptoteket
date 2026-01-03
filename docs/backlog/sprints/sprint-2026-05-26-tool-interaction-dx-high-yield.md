---
type: sprint
id: SPR-2026-05-26
title: "Sprint 2026-05-26: Tool interaction DX high-yield wins"
status: planned
owners: "agents"
created: 2025-12-29
updated: 2026-01-03
starts: 2026-05-26
ends: 2026-06-08
objective: "Ship high-leverage interaction UX improvements for multi-step tools (progress + files available view)."
prd: "PRD-tool-authoring-v0.1"
epics: ["EPIC-14"]
stories: ["ST-14-22"]
---

## Objective

Reduce friction when iterating on interactive tools by making multi-step flows feel guided and repeatable, without a UI
contract breaking change.

Reference context: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`

## Scope (committed stories)

- [ST-14-22: Tool run UX conventions for progress + input file references](../stories/story-14-22-tool-run-ux-progress-and-file-references.md)

## Out of scope

- UI contract v2.x changes (defaults/prefill map, first-class file references).
- Fully reactive conditional fields inside a single action form.

## Decisions required (ADRs)

- None expected if we treat progress/file references as UI conventions derived from existing payload/state.

## Risks / edge cases

- Privacy: file names/references must not leak internal filesystem paths or other implementation details.
- Backwards compatibility: conventions must be opt-in (ignore unknown state keys).

## Execution plan (suggested)

1) Define and document a minimal progress convention (e.g., `state.progress = { current, total, label? }`) and render it.
2) Expose a “Files available” panel derived from the known input manifest, using names/references (no filesystem paths).

## Demo checklist

- Show step progress for a 2–3 step tool (step indicator updates after each action).
- Upload 1–2 files and show the “Files available” UX (names + copyable references) and that the tool can consume them.

## Verification checklist

- `pdm run docs-validate`
- `pdm run lint`
- `pdm run test`
- Live functional check (backend + SPA dev); record steps in `.agent/handoff.md`.
