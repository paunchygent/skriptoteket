---
type: adr
id: ADR-0049
title: "Login events audit trail"
status: accepted
owners: "agents"
deciders: ["lead-developer", "user-lead"]
created: 2025-12-29
updated: 2025-12-29
links: ["ST-17-07"]
---

## Context

Skriptoteket currently tracks only the latest login state on each user (last login, failed login, lockout). This is
insufficient for account-level investigations and support questions. Aggregate metrics (ST-17-06) help detect trends,
but they cannot answer per-user audit questions.

We need a durable login audit trail with reasonable privacy controls, limited retention, and superuser-only access.

## Decision

Introduce a `login_events` audit table and expose it via a superuser-only admin API/UI.

### Storage

- Store raw IP address and user-agent string for each login attempt.
- Include nullable geo fields for future enrichment (no external geo lookup yet).
- Capture request metadata (e.g., correlation id and auth provider).
- Keep `user_id` nullable so failed attempts can be recorded even when no user resolves.
- Track status (`success`/`failure`) and failure code when applicable.

### Retention

- Retain login events for **90 days**.
- Enforce retention via a CLI cleanup command plus a systemd timer (same operational pattern as sandbox snapshots).

### Access

- Superuser-only API endpoint to list a user's recent login events.
- Superuser-only UI panel on the admin user detail page.

## Consequences

### Positive

- Provides account-level history for security review and user support.
- Preserves privacy scope via limited retention and superuser-only access.
- Aligns with existing ops patterns (CLI + systemd cleanup).

### Negative

- Stores raw IP/user-agent data (higher privacy sensitivity).
- Requires schema migration, cleanup tooling, and UI/API changes.
- Geo fields remain empty until a later enrichment phase.
