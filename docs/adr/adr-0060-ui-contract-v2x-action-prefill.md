---
type: adr
id: ADR-0060
title: "UI contract v2.x: action prefill defaults"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2026-01-15
updated: 2026-01-15
links: ["ADR-0022", "ADR-0024", "ADR-0030", "ADR-0038", "EPIC-14", "ST-14-23"]
---

## Context

Tool UI contract v2 (ADR-0022) enables interactive multi-step tools via `ui_payload.next_actions[]` (forms) and
persisted session `state` (ADR-0024).

Today, action fields can only be "prefilled" via client-side stickiness (remember last submitted values). This is not a
platform feature:

- Tools cannot intentionally guide the user by providing defaults derived from current state or prior outputs.
- Stored `ui_payload` replay cannot reconstruct "suggested" values deterministically.

ST-14-23 requires a backwards-compatible extension so tools can provide explicit defaults/prefill metadata for action
fields.

## Decision

### 1) Add optional `prefill` on `UiFormAction`

Extend the existing action schema with an **optional** prefill map on each form action:

- Location: `next_actions[].prefill`
- Shape: `{[field_name: string]: JsonValue}`
- Versioning: **no contract_version bump** (still `contract_version: 2`); this is a v2.x additive extension.

Rationale:

- Keeps the schema change minimal (single optional field on `UiFormAction`).
- Allows deterministic validation and stripping during normalization (not parse-time contract rejection).
- Preserves prefill metadata inside stored `ui_payload` for historical replay.

### 2) Deterministic normalization rules (reject/strip with actionable error)

The normalizer MUST validate `prefill` against the action's (normalized) `fields[]` and apply deterministic rules:

- Unknown `prefill` keys (no matching field name) are invalid.
- Prefill values must match field kinds:
  - `string`, `text`: `str`
  - `boolean`: `bool`
  - `integer`: `int`
  - `number`: `int | float`
  - `enum`: `str` and must match an available option `value`
  - `multi_enum`: `list[str]` and each entry must match an available option `value`
- Prefill entries targeting fields dropped by policy/caps (e.g. disallowed kind or truncated fields list) are dropped.

Invalid prefill entries are **stripped deterministically**. The normalizer MUST surface an actionable error by adding a
system notice output describing what was dropped (consistent with existing deterministic notice patterns).

### 3) Frontend rendering semantics

When rendering action forms:

- If `prefill` is present, matching fields are initialized to those values.
- If `prefill` is absent, behavior remains unchanged (existing UI defaults).
- Prefill is **initial-value only**; user edits take precedence and must not be overwritten on re-render.

Runtime/editor UIs include a "shared fields + multiple action buttons" component (`ToolRunActions`). For this component,
prefill values are merged deterministically by field name based on the normalized `next_actions` order.

## Consequences

### Benefits

- Tools can provide intentional defaults derived from state/outputs without client-side workarounds.
- Stored `ui_payload` replays preserve prefill metadata deterministically.
- Minimal, backwards-compatible contract extension (no v2 version bump).

### Tradeoffs / Risks

- Prefill is a JSON map (not per-field typed defaults); correctness relies on server-side validation.
- Shared-fields rendering cannot express different defaults per action for the same field name; tools should use distinct
  field names when action-specific defaults are required.
