---
type: epic
id: EPIC-02
title: "Identity and access control (RBAC)"
status: active
owners: "agents"
created: 2025-12-13
updated: 2026-03-30
outcome: "Users can authenticate, self-register, verify email, recover local-account access, manage their profiles, and role checks reliably gate contributor/admin/superuser capabilities."
dependencies: ["ADR-0006", "ADR-0011", "ADR-0034", "ADR-0078"]
---

## Scope

- Minimal identity model and role hierarchy (`user`, `contributor`, `admin`, `superuser`).
- Testable identity service behind protocols (DI).
- Role guards in web/api for protected actions.
- Self-registration for new users (ADR-0034).
- Email verification for self-registered users.
- User profiles aligned with HuleEdu model (ADR-0034).
- Password change (self-service).
- Local password reset via emailed token.
- Brute-force protection with account lockout.

## Out of scope

- Admin user management UI (admins use CLI for now).
- HuleEdu SSO integration (ADR-0011, future).
- Password reset for federated/HuleEdu identities.
- Magic-link login.

## Stories

- [ST-02-01: User model and identity service](../stories/story-02-01-user-model-and-identity-service.md) (done)
- [ST-02-02: Admin nomination and superuser approval](../stories/story-02-02-admin-nomination-and-superuser-approval.md) (ready)
- [ST-02-03: Self-registration](../stories/story-02-03-self-registration.md) (done)
- [ST-02-04: User profile and password change](../stories/story-02-04-user-profile-and-password-change.md) (done)
- [ST-02-05: Brute-force lockout](../stories/story-02-05-brute-force-lockout.md) (done)
- [ST-02-06: Swedish school domain allowlist for registration](../stories/story-02-06-swedish-school-domain-allowlist-registration.md) (ready)
- [ST-02-07: Local password reset via emailed token](../stories/story-02-07-local-password-reset-via-emailed-token.md) (ready)
- [ST-02-08: Registration preflight validation and password visibility](../stories/story-02-08-registration-preflight-validation-and-password-visibility.md) (in_progress)
- [ST-02-09: Distributed password-reset hardening for scaled auth](../stories/story-02-09-distributed-password-reset-hardening-for-scaled-auth.md) (ready)

## Dependencies

- ADR-0006 (identity/authorization MVP)
- ADR-0011 (HuleEdu federation design)
- ADR-0034 (self-registration and profiles)
- ADR-0078 (local password reset via emailed token)
