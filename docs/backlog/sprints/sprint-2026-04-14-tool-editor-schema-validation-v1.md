---
type: sprint
id: SPR-2026-04-14
title: "Sprint 2026-04-14: Tool editor schema validation v1"
status: done
owners: "agents"
created: 2025-12-29
updated: 2026-01-12
starts: 2026-04-14
ends: 2026-04-27
objective: "Add fast, accurate schema validation feedback in the editor via a dedicated backend validation endpoint."
prd: "PRD-editor-sandbox-v0.1"
epics: ["EPIC-14"]
stories: ["ST-14-15", "ST-14-16"]
---

## Objective

Provide backend-authoritative schema validation feedback without requiring a save/run loop.

Reference context: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`

## Scope (committed stories)

- [ST-14-15: API endpoint to validate tool schemas (settings_schema/input_schema)](../stories/story-14-15-editor-schema-validation-endpoint.md)
- [ST-14-16: Editor UX for structured schema validation errors](../stories/story-14-16-editor-schema-validation-errors-ux.md)

## Out of scope

- Schema “v2” format changes.
- Auto-fixing schemas (lint autofix).

## Decisions required (ADRs)

- Decide the public shape of validation errors (reuse existing DomainError details vs a dedicated error payload).

## Risks / edge cases

- Validation must match runtime normalization exactly to avoid “passes validation but fails at run”.
- Rate limiting / UX spam: avoid hammering the endpoint on every keystroke.

## Demo checklist

- Show invalid schema and immediate structured errors.
- Show valid schema and “ready” state without saving.

## Verification checklist

- `pdm run docs-validate`
- `pdm run lint`
- `pdm run test`
- `pdm run fe-gen-api-types`
- Live functional check (backend + SPA dev); record steps in `.agent/handoff.md`.
