---
type: story
id: ST-02-03
title: "Self-registration"
status: ready
owners: "agents"
created: 2025-12-23
epic: "EPIC-02"
acceptance_criteria:
  - "Given a visitor on the landing page, when they click 'Skapa konto', then they see a registration form"
  - "Given a visitor filling the registration form with valid email/password/name, when they submit, then a new user account is created with role=user"
  - "Given successful registration, when the account is created, then the user is automatically logged in and redirected to home"
  - "Given a visitor trying to register with an existing email, when they submit, then they see an error 'E-postadressen är redan registrerad'"
  - "Given a visitor with weak password, when they submit, then they see validation error for password strength"
dependencies: ["ADR-0034"]
ui_impact: "New RegisterView.vue, registration link in header/login modal"
data_impact: "Creates user + user_profile rows atomically"
---

## Context

Currently users can only be created via CLI by admins. This story enables self-registration so users can create their own accounts.

## Implementation notes

### API

- `POST /api/v1/auth/register`
- Request: `{ email, password, first_name, last_name }`
- Response: `{ user, profile }` + session cookie
- Errors: `DUPLICATE_ENTRY` (409), `VALIDATION_ERROR` (422)

### Domain

- Reuse `create_local_user` logic from existing provisioning
- Set `role=user` and `email_verified=false` for self-registered users
- Create `UserProfile` atomically with `User`

### SPA

- `RegisterView.vue` at `/register`
- Form: email, password, confirm password, first name, last name
- Route guard: redirect to home if already authenticated
- Add "Skapa konto" link to `LandingLayout.vue` header and `LoginModal.vue`

### Validation

- Email: valid format, unique
- Password: minimum 8 characters (can strengthen later)
- Names: required, max 100 chars
