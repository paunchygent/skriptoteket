---
type: story
id: ST-17-07
title: "Login events audit trail"
status: done
owners: "agents"
created: 2025-12-29
updated: 2025-12-29
epic: "EPIC-17"
dependencies:
  - "ST-17-06"
links:
  - "ADR-0049"
acceptance_criteria:
  - "Given a login attempt succeeds, when it completes, then a login_events record is created with user_id, status='success', ip_address, and user_agent"
  - "Given a login attempt fails, when it completes, then a login_events record is created with status='failure', failure_code, ip_address, user_agent, and user_id when resolvable"
  - "Given a login event is stored, when inspected, then it includes nullable geo fields and request metadata"
  - "Given a superuser requests login events for a user, when the API responds, then it returns only that user's events (newest-first) within the last 90 days"
  - "Given a non-superuser requests login events, when the API is called, then access is denied"
  - "Given the retention policy, when cleanup runs, then login events older than 90 days are deleted"
  - "Given the admin user detail view, when the viewer is a superuser, then recent login events are visible"
---

## Context

We need account-level visibility into login activity for support and security workflows. The existing user fields only
capture the latest login state, and metrics provide aggregate views without per-user history.

This story introduces an audit trail of login events with raw IP/user-agent data and optional geo fields, retained for
90 days, and exposed only to superusers.

## Notes

- Storage: new `login_events` table with raw IP address, user agent, nullable geo fields, and request metadata.
- Access: superuser-only API plus a small user detail panel in the admin UI.
- Retention: 90 days, enforced by CLI cleanup and a systemd timer (per ADR-0049).
