---
type: adr
id: ADR-0009
title: "MVP authentication: admin-provisioned local accounts + server-side sessions"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-13
---

## Context

The v0.1 MVP needs authentication and role-based authorization that is:

- easy to implement and operate (single container + PostgreSQL)
- robust (no hacks), testable via DI/protocols, and DDD/Clean-Architecture aligned
- extensible to future SSO without rewriting business logic

## Decision

For v0.1, use:

- **Admin-provisioned local accounts** (no self-signup).
- **Password authentication** with a strong password hasher.
- **Server-side sessions** stored in PostgreSQL (session ID in a secure cookie).

Defer to future scope:

- magic-link email login
- external SSO/IdP (OIDC) integrations (e.g., HuleEdu; ADR-0011)

## Implementation constraints

- Auth/identity concerns are isolated behind protocols (e.g., `CurrentUserProviderProtocol`, `SessionStoreProtocol`, `PasswordHasherProtocol`).
- The web/api layer owns cookies and request extraction; domain/application code stays framework-agnostic.
- Store `external_id` (nullable) and `auth_provider` on users to enable future identity federation without touching business logic (ADR-0011).
- Baseline security is required (secure cookies, expiration, revocation, CSRF for form posts, audit logging of role changes).

## Consequences

- Minimal operational dependencies for v0.1 (no email infrastructure, no IdP setup).
- Future OIDC can be added by swapping the identity provider implementation and keeping domain/application unchanged.
