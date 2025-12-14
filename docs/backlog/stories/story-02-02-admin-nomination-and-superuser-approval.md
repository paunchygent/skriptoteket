---
type: story
id: ST-02-02
title: "Admin nomination and superuser approval"
status: ready
owners: "agents"
created: 2025-12-13
epic: "EPIC-02"
acceptance_criteria:
  - "Given an admin, when they nominate a user for admin, then the nomination is recorded with nominator, rationale, and timestamp."
  - "Given a superuser, when they view pending nominations, then they can see the nominee, nominator, rationale, and creation timestamp."
  - "Given a superuser, when they approve a nomination, then the nominee becomes an admin and the approval decision is recorded with actor and timestamp."
  - "Given a superuser, when they deny a nomination, then the nominee's role is unchanged and the denial decision is recorded with actor and timestamp."
  - "Given a non-superuser, when they attempt to approve/deny a nomination, then they are denied."
---

## Context

Admins have elevated governance capabilities (including publishing tools and tool script versions). Promoting a user to
admin therefore requires a superuser gate as described in ADR-0005.

## Notes

- Implement with protocol-first DI and an append-only, auditable decision record (mirror the suggestions decisioning
  pattern: nominate → decide).
