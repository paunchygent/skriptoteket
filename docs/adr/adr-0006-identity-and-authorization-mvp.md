---
type: adr
id: ADR-0006
title: "Identity and authorization (MVP, testable, extensible)"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-13
---

## Context

We need authentication and role-based authorization that is easy to implement for v0.1, but robust and extensible (no hacks). It must remain testable and follow DDD + Clean Architecture.

## Decision

- Implement a minimal internal identity model with roles: `user`, `contributor`, `admin`, `superuser`.
- Keep authentication and “current user” behind protocols (DI), so application logic never depends on FastAPI/session/JWT implementations.
- Enforce authorization at the interface layer (web/api) with clear role guards; application handlers receive an actor/role abstraction when needed.
- Defer SSO/IdP integrations to future scope; the design must allow swapping the identity provider implementation without changing business logic.
- When external identity is introduced (HuleEdu), roles remain local to Skriptoteket (identity ≠ authorization). See ADR-0011.

## Consequences

- Early clarity on role boundaries prevents ad-hoc permission checks.
- Identity becomes a first-class domain with tests and protocols, not a framework detail.
