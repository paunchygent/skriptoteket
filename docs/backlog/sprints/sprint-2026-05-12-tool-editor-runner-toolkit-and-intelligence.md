---
type: sprint
id: SPR-2026-05-12
title: "Sprint 2026-05-12: Tool editor runner toolkit + intelligence"
status: planned
owners: "agents"
created: 2025-12-29
starts: 2026-05-12
ends: 2026-05-25
objective: "Reduce script author friction by providing a small runner-side toolkit and editor intelligence support for it."
prd: "PRD-tool-authoring-v0.1"
epics: ["EPIC-14", "EPIC-08"]
stories: ["ST-14-19", "ST-14-20", "ST-08-17"]
---

## Objective

Make it easier to write correct tools by standardizing common boilerplate (inputs/settings/action parsing) and surfacing it
in editor completions/hover/linting.

Reference context: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`

## Scope (committed stories)

- [ST-14-19: Runner toolkit helper module (inputs/settings/actions)](../stories/story-14-19-runner-toolkit-helper-module.md)
- [ST-14-20: Editor intelligence updates for toolkit (completions/hover/lints)](../stories/story-14-20-editor-intelligence-toolkit-support.md)
- [ST-08-17: Tabby edit suggestions + prompt A/B evaluation](../stories/story-08-17-tabby-edit-suggestions-ab-testing.md)

## Out of scope

- AI code generation.
- Large-scale “SDK” or external package distribution.

## Decisions required (ADRs)

- None expected if the toolkit remains small and backwards compatible; otherwise propose an ADR for “runner stdlib”.

## Risks / edge cases

- Backwards compatibility: existing scripts should not break due to toolkit introduction.
- Keep the toolkit minimal to avoid long-term maintenance drag.

## Demo checklist

- Use toolkit helpers in a demo tool and show it works in sandbox.
- Show editor completions/hover/lints for the toolkit APIs.

## Verification checklist

- `pdm run docs-validate`
- `pdm run lint`
- `pdm run test`
- Live functional check (backend + SPA dev); record steps in `.agent/handoff.md`.
