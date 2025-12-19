---
type: epic
id: EPIC-10
title: "Interactive tool UI contract and curated apps"
status: proposed
owners: "agents"
created: 2025-12-19
outcome: "End users can run multi-turn tools with typed outputs/actions/state, and curated owner apps can be served in Katalog without exposing the tool editor workflow."
---

## Scope

- Tool UI contract v2 (typed outputs + actions + persisted state)
- Deterministic app-side normalization (allowlists + size budgets)
- Persistence model: tool sessions + stored UI payload per run
- Minimal API surface for interactive turn-taking
- Curated apps registry + execution path (owner-authored, not editor-managed)

## Out of scope

- Full notebook kernels / long-running interactive compute sessions
- Allowing tools to ship arbitrary client-side JavaScript
- A full site-wide SPA rewrite

## Stories

- [ST-10-01: Tool UI contract v2 (runner result.json)](../stories/story-10-01-tool-ui-contract-v2.md)
- [ST-10-02: Tool sessions persistence (state + optimistic concurrency)](../stories/story-10-02-tool-sessions.md)
- [ST-10-03: UI payload normalizer + storage on tool runs](../stories/story-10-03-ui-payload-normalizer.md)
- [ST-10-04: Interactive tool API endpoints (start_action + read APIs)](../stories/story-10-04-interactive-tool-api.md)
- [ST-10-05: Curated apps registry and catalog integration](../stories/story-10-05-curated-apps-registry.md)
- [ST-10-06: Curated app execution + persisted runs](../stories/story-10-06-curated-apps-execution.md)

## Risks

- Contract drift between runner and app (mitigate: single-source schema + strict version checks).
- Payload/state bloat (mitigate: strict size caps + artifacts for large data).
- Two execution paths (runner tools vs curated apps) (mitigate: shared UI contract + shared normalizer).

## Dependencies

- ADR-0022 (Tool UI contract v2)
- ADR-0023 (Curated apps)
- ADR-0024 (Persistence model)
