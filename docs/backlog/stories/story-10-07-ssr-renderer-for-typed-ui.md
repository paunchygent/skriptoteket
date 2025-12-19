---
type: story
id: ST-10-07
title: "SSR rendering for typed outputs/actions"
status: ready
owners: "agents"
created: 2025-12-19
epic: "EPIC-10"
acceptance_criteria:
  - "Given a stored ui_payload with allowlisted output kinds, when rendered in a server-rendered page, then the user sees the same outputs without requiring the SPA island"
  - "Given a stored ui_payload with next_actions and a session state_rev, when rendered, then the server renders a submit path that calls start_action with expected_state_rev"
  - "Given an output of kind html_sandboxed, when rendered, then scripts do not execute (iframe sandbox without allow-scripts)"
ui_impact: "Enables interactive tool UI to ship incrementally on SSR pages before (or alongside) SPA islands."
dependencies: ["ADR-0022", "ST-10-03", "ST-10-04"]
---

## Context

Even with SPA islands approved for high-complexity surfaces, Skriptoteket should be able to render typed outputs and
actions in server-rendered pages to keep the default UI paradigm consistent and to allow incremental rollout.
