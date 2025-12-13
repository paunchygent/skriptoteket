---
type: story
id: ST-02-01
title: "User model and identity service (MVP, testable)"
status: done
owners: "agents"
created: 2025-12-13
epic: "EPIC-02"
acceptance_criteria:
  - "Given a request, when the web/api layer runs, then it can resolve the current user (or anonymous) via an injected identity provider."
  - "Given a valid session cookie, when a request is processed, then the current user is resolved via a server-side session stored in PostgreSQL."
  - "Given v0.1, when a new user is created, then it is created by an admin (no self-signup)."
  - "Given a user with assigned roles, when an action requires a role, then access is granted/denied deterministically."
  - "Given unit tests, when identity is mocked via protocols, then application handlers can be tested without FastAPI or database."
  - "Given the federation-ready user model, when a user is stored, then `external_id` is nullable and `auth_provider` is recorded (e.g., `local`, future `huleedu`) without affecting role checks."
---
