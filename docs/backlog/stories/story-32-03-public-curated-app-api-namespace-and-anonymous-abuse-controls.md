---
type: story
id: ST-32-03
title: "Public curated-app API namespace and anonymous abuse controls"
status: done
owners: "agents"
created: 2026-04-03
updated: 2026-04-30
epic: "EPIC-32"
dependencies: ["ST-32-02", "ADR-0079"]
acceptance_criteria:
  - "Given a curated app supports public helper APIs, when the public contract is defined, then those endpoints live in a dedicated public namespace rather than inside the authenticated `/api/v1/apps/{app_id}/...` seam."
  - "Given a public helper request is processed, when payloads or identifiers are validated, then the request accepts guest-local ids or embedded guest payloads only and never owner-scoped references such as account roster/template/draft ids."
  - "Given a public helper endpoint exists, when its authority model is reviewed, then it never depends on `require_user_api`, `require_session_api`, or `require_csrf_token`, ignores ambient account authority, and returns the same guest semantics whether or not a session cookie is present."
  - "Given public helper endpoints are exposed, when security/operations review them, then rate limits, payload-size caps, MIME/type validation, request-time budgets, and structured reason codes are explicitly documented."
  - "Given failures are observed in production or support, when logs/metrics/events are emitted, then `public_helper_*` signals are distinguished from later `authenticated_upgrade_*` signals without retaining raw sensitive guest payloads."
ui_impact: "No direct UI redesign; enables later guest import/smart/export flows through a safe public API seam."
data_impact: "No owner-scoped persistence by default; transient buffers only where explicitly approved."
---

## Context

Klassrumskartan guest import preview, smart runs, and direct export all require
server help, but the current app-specific API surface is consistently
authenticated and owner-scoped. Public work therefore needs a parallel API
boundary with explicit abuse controls.

## Notes

- Public helper routes should be as small as possible.
- The contract should describe what public endpoints can never do:
  - no owner lookup by authenticated ids
  - no Vault/MyFiles writes
  - no guest artifact recovery lane
- Public endpoints must remain guest/public endpoints even if the browser is
  currently logged in.
- Conversion Hub remains the counterexample that stays authenticated-only.

## Status Reconciliation (2026-04-30)

This story is now marked `done`. Public Klassrumskartan bootstrap, import
preview, Smart helper, and direct-download export routes live under
`/api/v1/public/apps/classroom.group-seating-studio/...` with public-helper
validation, throttling, and reason-code handling separated from authenticated
owner-scoped APIs.
