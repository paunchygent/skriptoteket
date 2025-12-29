---
type: sprint
id: SPR-2026-06-09
title: "Sprint 2026-06-09: Tool UI contract v2.x (action defaults + file references)"
status: planned
owners: "agents"
created: 2025-12-29
starts: 2026-06-09
ends: 2026-06-22
objective: "Introduce backwards-compatible UI contract extensions for true action defaults/prefill and first-class file references."
prd: "PRD-tool-authoring-v0.1"
epics: ["EPIC-14"]
stories: ["ST-14-23", "ST-14-24"]
---

## Objective

Turn the highest-friction multi-step tool gaps into first-class, contract-supported capabilities:

- **True action defaults/prefill** (tool can specify default values for action fields, optionally derived from state)
- **First-class file references** (UI and runner agree on stable file identifiers instead of hard-coded `/work/input/...`)

This enables a more robust implementation of the “high-yield” sprint (SPR-2026-05-26) by replacing client-side
workarounds with platform capabilities.

Reference context: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`

## Scope (committed stories)

- [ST-14-23: UI contract v2.x: action defaults/prefill](../stories/story-14-23-ui-contract-action-defaults-prefill.md)
- [ST-14-24: UI contract v2.x: first-class file references](../stories/story-14-24-ui-contract-file-references.md)

## Out of scope

- Breaking changes to existing tools or stored `ui_payload`.
- Reactive conditional fields inside a single action form (pre-submit).
- A full “workflow engine” abstraction; keep the contract minimal and composable.

## Decisions required (ADRs)

- Add an ADR for the specific contract shape and compatibility strategy (e.g. optional fields on v2 payloads vs v2.1
  version bump).

## Risks / edge cases

- Compatibility: old tools and old stored payloads must continue to render.
- Security: file references must not allow arbitrary file reads (must remain constrained to the run/session files).
- Validation: server-side normalization should reject/strip invalid defaults or unknown file refs deterministically.

## Execution plan (suggested)

1) Specify the contract extension + server normalization rules (incl. budgets).
2) Extend API models + stored `ui_payload` schema typing (backwards compatible).
3) Implement SPA rendering + runner integration for the new fields.

## Demo checklist

- Tool returns next_actions with defaults; UI renders prefilled values without client-side stickiness.
- Tool returns/receives file references; UI shows a file picker for “existing files” and the runner can resolve them.
- Verify fallback behavior: tools without these fields render as before.

## Verification checklist

- `pdm run docs-validate`
- `pdm run lint`
- `pdm run test`
- `pdm run fe-gen-api-types` (if API typing changes)
- Live functional check (backend + SPA dev); record steps in `.agent/handoff.md`.
