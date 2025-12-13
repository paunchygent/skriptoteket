---
type: adr
id: ADR-0011
title: "Future HuleEdu integration: identity federation without shared authorization"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-13
---

## Context

Skriptoteket launches as a standalone service with its own PostgreSQL and local accounts (session auth). In a later phase,
HuleEdu users should automatically get access to Skriptoteket via HuleEdu SSO, while Skriptoteket may still keep local
accounts for admins/legacy cases.

We must avoid coupling domain/application logic to *how* authentication happens and keep authorization rules local.

## Decision

1. **Identity behind protocols.** All authentication and “current user” resolution is behind `typing.Protocol` and injected
   via DI. Domain/application code must not depend on FastAPI, cookies, JWT, or external IdPs.

   ```py
   class CurrentUserProviderProtocol(Protocol):
       async def get_current_user(self) -> User | None: ...
   ```

2. **Roles are local.** HuleEdu provides identity, not authorization. A user’s role in Skriptoteket (`user`/`contributor`/
   `admin`/`superuser`) is always determined by Skriptoteket’s own role management.

3. **Prepare for two auth flows.**
   - v0.1: local email+password → server-side session (PostgreSQL)
   - future: HuleEdu OIDC/JWT → (a) server-side session bridge or (b) stateless verification, without changing business logic

4. **User model is federation-ready.** Include nullable `external_id` and `auth_provider` to support future HuleEdu users:

   ```py
   class User:
       id: UUID                 # Skriptoteket internal ID
       external_id: str | None  # HuleEdu user ID (future)
       email: str
       role: Role
       auth_provider: str       # "local" | "huleedu"
   ```

## Not in scope now

- Implementing SSO/IdP integration
- Kafka/event integration with HuleEdu
- Shared database between systems

## Consequences

- We can add HuleEdu SSO later by swapping identity/adapters and keeping domain/application unchanged.
- v0.1 data model includes fields needed for future federation, reducing migration risk.
