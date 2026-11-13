---
type: adr
id: ADR-SKRIPT-0009
title: 'MVP authentication: admin-provisioned local accounts + server-side sessions'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: accepted
deciders:
- user-lead
retired_ids:
- ADR-0009
---

## Context

### Source: Context

The v0.1 MVP needs authentication and role-based authorization that is:

- easy to implement and operate (single container + PostgreSQL)
- robust (no hacks), testable via DI/protocols, and DDD/Clean-Architecture aligned
- extensible to future SSO without rewriting business logic

## Decision

### Source: Decision

For v0.1, use:

- **Admin-provisioned local accounts** (no self-signup).
- **Password authentication** with a strong password hasher.
- **Server-side sessions** stored in PostgreSQL (session ID in a secure cookie).

Defer to future scope:

- magic-link email login
- external SSO/IdP (OIDC) integrations (e.g., HuleEdu; ADR-0011)

### Source: Implementation constraints

- Auth/identity concerns are isolated behind protocols (e.g., `CurrentUserProviderProtocol`, `SessionStoreProtocol`, `PasswordHasherProtocol`).
- The web/api layer owns cookies and request extraction; domain/application code stays framework-agnostic.
- Store `external_id` (nullable) and `auth_provider` on users to enable future identity federation without touching business logic (ADR-0011).
- Baseline security is required (secure cookies, expiration, revocation, CSRF for form posts, audit logging of role changes).

## Non-Decisions

### Source: Implementation constraints

- Auth/identity concerns are isolated behind protocols (e.g., `CurrentUserProviderProtocol`, `SessionStoreProtocol`, `PasswordHasherProtocol`).
- The web/api layer owns cookies and request extraction; domain/application code stays framework-agnostic.
- Store `external_id` (nullable) and `auth_provider` on users to enable future identity federation without touching business logic (ADR-0011).
- Baseline security is required (secure cookies, expiration, revocation, CSRF for form posts, audit logging of role changes).

## Consequences

### Source: Consequences

- Minimal operational dependencies for v0.1 (no email infrastructure, no IdP setup).
- Future OIDC can be added by swapping the identity provider implementation and keeping domain/application unchanged.
