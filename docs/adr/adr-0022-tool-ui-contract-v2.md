---
type: adr
id: ADR-0022
title: "Tool UI contract v2 (typed outputs, actions, and state)"
status: proposed
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-19
links: ["PRD-script-hub-v0.2", "EPIC-10"]
---

## Context

Skriptoteket currently renders tool results primarily via:

- `html_output` (runner contract v1) displayed in an `<iframe sandbox>`
- `stdout`/`stderr` logs
- `artifacts` as downloads

This is sufficient for linear “upload → run → view output” tools, but it makes it difficult to evolve towards:

- multi-turn “apps” (user interaction + state preservation)
- consistent UX across tools (scripts fighting the UI)
- safe, richer outputs (tables, charts, structured data) without allowing arbitrary script-provided JS

We also want a contract that supports:

- a future embedded editor SPA (admin/contributor) without changing the runtime contract
- backend-integrated capabilities (e.g. NLP analysis) without giving scripts arbitrary network access

## Decision

Adopt a new **Tool UI contract v2** as a typed boundary between execution and rendering.

### 1) Extend runner `result.json` to contract version 2

`/work/result.json` becomes (conceptually):

- `contract_version: 2`
- `status: succeeded|failed|timed_out`
- `error_summary: safe string | null`
- `outputs[]`: typed UI blocks (platform-rendered)
- `next_actions[]`: allowed next steps with a constrained input schema
- `state`: small JSON object (optional)
- `artifacts[]`: as in v1 (paths under `output/`)

Contract v1 is not supported once v2 is adopted; runner and app are upgraded together and mismatched versions are treated as contract violations.

### 2) All interactivity is platform-rendered (no arbitrary JS)

Tools MUST NOT return executable script content for the UI.

- HTML is allowed only as `html_sandboxed` and rendered in a sandboxed iframe without `allow-scripts`.
- Rich interactivity is implemented by Skriptoteket UI components that render typed outputs and action forms.

### 3) Normalization is deterministic and policy-driven

The application normalizes execution output into a stored `ui_payload` using:

- a strict allowlist of output kinds and action schemas
- size budgets (state + payload + per-kind caps)
- deterministic truncation rules

Normalization must be pure and unit-testable.

## Consequences

### Benefits

- Enables safe, consistent interactivity and richer outputs for end users.
- Separates “what to show” (typed outputs) from “how it looks” (UI components).
- Provides a single, evolvable seam for runner-based tools, curated apps, and backend capability actions.
- Prevents UI security regression by keeping script-provided JS out of the main origin.

### Tradeoffs / Risks

- Requires implementing and maintaining a small “UI capability surface” (supported output kinds).
- Some tool authors may find typed outputs more restrictive than HTML; this is intentional for safety and UX.
- Adds persistence complexity (session state + ui_payload storage) which must be carefully size-capped.
