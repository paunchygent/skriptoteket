---
type: story
id: ST-10-01
title: "Tool UI contract v2 (runner result.json)"
status: ready
owners: "agents"
created: 2025-12-19
epic: "EPIC-10"
acceptance_criteria:
  - "Given a tool execution completes, when the runner emits result.json, then the app requires contract_version=2 and treats other versions as a contract violation"
  - "Given contract_version=2, when the app persists the run, then a validated ui_payload is stored for replay/audit"
  - "Given outputs include html_sandboxed, when rendered, then scripts do not execute (iframe sandbox without allow-scripts)"
---

## Context

To enable platform-rendered interactivity and consistent UX, we need to evolve from HTML-only results to a typed
outputs/actions/state contract.

## Scope

- Update the runner result contract to v2 (outputs/actions/state + artifacts)
- Update app parsing and strict contract version enforcement
- Ensure html outputs remain sandboxed (no script execution)

## Dependencies

- ADR-0022
