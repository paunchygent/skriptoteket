---
type: story
id: ST-10-02
title: "Tool sessions (state + optimistic concurrency)"
status: done
owners: "agents"
created: 2025-12-19
epic: "EPIC-10"
acceptance_criteria:
  - "Given a user starts a tool session, when requested, then the system returns current state and state_rev for that (tool_id, user_id, context)"
  - "Given expected_state_rev matches the stored state_rev, when an action completes with updated state, then state is persisted and state_rev increments by 1"
  - "Given expected_state_rev is stale, when an action is started, then the system rejects the request with a concurrency error"
  - "Given a user clears tool memory, when invoked, then the session state resets to {} and state_rev increments"
data_impact: "Add tool_sessions table (state JSONB + state_rev) keyed by tool/user/context."
dependencies: ["ADR-0024"]
---

## Context

Multi-turn tools require a small persisted state per user and tool, with concurrency controls to avoid multi-tab races.
