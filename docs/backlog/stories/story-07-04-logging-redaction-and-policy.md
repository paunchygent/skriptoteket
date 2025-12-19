---
type: story
id: ST-07-04
title: "Logging redaction + sensitive data policy"
status: done
owners: "agents"
created: 2025-12-16
epic: "EPIC-07"
acceptance_criteria:
  - "A documented policy defines what may/must not be logged (PII, secrets, student data)."
  - "A redaction processor scrubs common secret keys (password, token, secret, api_key) from structured logs."
  - "Security review checklist includes logging/PII verification."
---

## Context

Skriptoteket handles school-related data. Observability must not become a data leakage vector.

## Scope

- Add a redaction processor to structlog configuration.
- Add a short policy section to the observability runbook and reference it from relevant stories/ADRs.
