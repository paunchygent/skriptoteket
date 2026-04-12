---
type: adr
id: ADR-0011
title: "Superseded future HuleEdu integration: identity federation without shared authorization"
status: superseded
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-13
superseded_by: ADR-0083
---

## Supersession

ADR-0083 supersedes this earlier future-SSO plan. The current architecture is
the HuleEdu shared browser-session/product-realm ceremony: HuleEdu owns browser
login, session/CSRF, Gateway ceremony validation, and signed identity context;
Skriptoteket owns app continuation, local projection, and local roles/RBAC.
This document remains as historical context for the protocol-first and
local-authorization decisions.

## Context

Skriptoteket launches as a standalone service with its own PostgreSQL and local accounts (session auth). In a later phase,
HuleEdu users should automatically get access to Skriptoteket via a HuleEdu-owned
login ceremony, while Skriptoteket may still keep local roles and projection
state.

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

3. **Prepare for external identity without shared authorization.**
   - v0.1: local email+password → server-side session (PostgreSQL)
   - current cutover: HuleEdu shared browser-session/product-realm ceremony,
     without changing business logic

4. **User model is provider-ready.** Include nullable `external_id` and `auth_provider` to support external HuleEdu identities:

   ```py
   class User:
       id: UUID                 # Skriptoteket internal ID
       external_id: str | None  # HuleEdu user ID (future)
       email: str
       role: Role
       auth_provider: str       # "local" | "huleedu"
   ```

## Not in scope now

- Implementing the ADR-0083 product-realm ceremony
- Kafka/event integration with HuleEdu
- Shared database between systems

## Consequences

- ADR-0083 replaced the speculative SSO/OIDC shape with the product-realm
  shared browser-session ceremony.
- The protocol and local-role decisions still hold.
