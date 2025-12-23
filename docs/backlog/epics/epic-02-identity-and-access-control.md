---
type: epic
id: EPIC-02
title: "Identity and access control (RBAC)"
status: active
owners: "agents"
created: 2025-12-13
updated: 2025-12-23
outcome: "Users can authenticate, self-register, manage their profiles, and role checks reliably gate contributor/admin/superuser capabilities."
dependencies: ["ADR-0006", "ADR-0011", "ADR-0034"]
---

## Scope

- Minimal identity model and role hierarchy (`user`, `contributor`, `admin`, `superuser`).
- Testable identity service behind protocols (DI).
- Role guards in web/api for protected actions.
- Self-registration for new users (ADR-0034).
- User profiles aligned with HuleEdu model (ADR-0034).
- Password change (self-service).
- Brute-force protection with account lockout.

## Out of scope

- Email verification flow (field added, enforcement deferred).
- Admin user management UI (admins use CLI for now).
- HuleEdu SSO integration (ADR-0011, future).

## Stories

- [ST-02-01: User model and identity service](../stories/story-02-01-user-model-and-identity-service.md) (done)
- [ST-02-02: Admin nomination and superuser approval](../stories/story-02-02-admin-nomination-and-superuser-approval.md) (ready)
- [ST-02-03: Self-registration](../stories/story-02-03-self-registration.md) (ready)
- [ST-02-04: User profile and password change](../stories/story-02-04-user-profile-and-password-change.md) (ready)
- [ST-02-05: Brute-force lockout](../stories/story-02-05-brute-force-lockout.md) (ready)

## Dependencies

- ADR-0006 (identity/authorization MVP)
- ADR-0011 (HuleEdu federation design)
- ADR-0034 (self-registration and profiles)
