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
- who can edit a specific tool (tool-scoped permissions)

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

### Tool-Scoped Edit Permissions (Maintainers + Owner)

In addition to global roles, editing rights for a specific tool are modeled as **tool-scoped permissions**:

- A tool has a persisted `owner_user_id` (the canonical author/owner; initially the user who submitted the draft for publication).
- A tool has a set of maintainers (“redigeringsbehörigheter”) who are allowed to edit the tool.
- The tool owner MUST be a maintainer.

Permission rules for changing tool maintainers:

- Admins can add/remove maintainers for a tool, **except**:
  - Admins cannot add or remove **superuser** maintainer permissions.
  - Admins cannot remove the **tool owner** from maintainer permissions.
- Only **superusers** can add/remove **superuser** maintainer permissions, and only superusers can remove the tool owner.

## Consequences

- Admin UI/workflows become part of the product surface (even if minimal in v0.1).
- “Advanced permission model” (multi-tenant, fine-grained RBAC, SSO/IdP integrations) can be deferred, but the role hierarchy and policy points should exist early.
- Editor authorization is not only role-based; it also depends on tool-scoped maintainer permissions, with explicit superuser/owner escalation rules.
