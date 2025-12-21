---
type: story
id: ST-10-10
title: "Runtime SPA island MVP (end-user interactive tool UI)"
status: done
owners: "agents"
created: 2025-12-19
epic: "EPIC-10"
acceptance_criteria:
  - "Given a user opens an interactive tool/app page, when it loads, then the SPA island renders stored ui_payload outputs and exposes next_actions"
  - "Given the user submits an action, when start_action succeeds, then the SPA updates to show the new run outputs and the updated session state_rev"
  - "Given expected_state_rev is stale, when start_action is attempted, then the SPA shows a concurrency error and offers a refresh path"
ui_impact: "Unlocks a rich multi-turn tool UX for teachers/admins without moving the whole site to a SPA."
dependencies: ["ADR-0022", "ADR-0024", "ADR-0025", "ST-10-02", "ST-10-03", "ST-10-04", "ST-10-08"]
---

## Context

Typed outputs/actions/state enable safe platform-rendered interactivity. A SPA island can provide a richer UX for
multi-turn tools and curated apps while keeping the rest of Skriptoteket server-rendered.
