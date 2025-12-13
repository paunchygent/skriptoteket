---
type: epic
id: EPIC-02
title: "Identity and access control (RBAC)"
status: proposed
owners: "agents"
created: 2025-12-13
outcome: "Users can authenticate and role checks reliably gate contributor/admin/superuser capabilities."
---

## Scope

- Minimal identity model and role hierarchy (`user`, `contributor`, `admin`, `superuser`).
- Testable identity service behind protocols (DI).
- Role guards in web/api for protected actions.

## Dependencies

- ADR-0006 (identity/authorization).

