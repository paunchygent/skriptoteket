---
type: adr
id: ADR-0005
title: "User roles and script governance (RBAC)"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-13
---

## Context

The MVP is teacher-first, but must be expandable. We need clear role boundaries for:

- who can run scripts vs propose new ones
- who can publish/depublish scripts
- who can manage users and contributor permissions

## Decision

Define a role hierarchy:

1. **User**
   - Browse and run published scripts/tools.
2. **Contributor**
   - All user capabilities.
   - Can propose/suggest new scripts (and improvements) for review.
3. **Admin**
   - All contributor capabilities.
   - Can manage users and contributors.
   - Can accept/modify/deny proposals.
   - Can publish/depublish scripts/tools.
   - Can nominate new admins for superuser approval.
4. **Superuser**
   - Final authority over admin promotion/demotion and governance changes.

Role checks happen at the interface layer (web/api). Business logic depends on role abstractions (e.g., `CurrentUserProtocol`) and never on framework-specific auth.

## Consequences

- Admin UI/workflows become part of the product surface (even if minimal in v0.1).
- “Advanced permission model” (multi-tenant, fine-grained RBAC, SSO/IdP integrations) can be deferred, but the role hierarchy and policy points should exist early.
