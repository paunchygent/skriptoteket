---
type: story
id: ST-02-04
title: "User profile and password change"
status: ready
owners: "agents"
created: 2025-12-23
epic: "EPIC-02"
acceptance_criteria:
  - "Given an authenticated user, when they navigate to /profile, then they see their profile information (name, email, locale)"
  - "Given a user on the profile page, when they update first_name/last_name/display_name/locale and save, then the profile is updated"
  - "Given a user changing their password, when they enter correct current password and valid new password, then the password is changed"
  - "Given a user changing their password, when they enter incorrect current password, then they see error 'Fel lösenord'"
  - "Given a user changing their email, when they enter a new email and save, then email is updated and email_verified is set to false"
  - "Given a user changing email to an already-used address, when they save, then they see error 'E-postadressen är redan registrerad'"
dependencies: ["ADR-0034", "ST-02-03"]
ui_impact: "New ProfileView.vue, profile link in sidebar/top bar"
data_impact: "Updates user_profiles and users tables"
---

## Context

Users need to manage their own profile information and change their password without admin intervention.

## Implementation notes

### API

- `GET /api/v1/profile` - Returns `{ user, profile }`
- `PATCH /api/v1/profile` - Updates profile fields
- `POST /api/v1/profile/password` - Changes password (requires `current_password`)
- `PATCH /api/v1/profile/email` - Changes email

### Domain

- `GetProfileHandler` - Load user + profile
- `UpdateProfileHandler` - Update profile fields
- `ChangePasswordHandler` - Verify current password, hash new password
- `ChangeEmailHandler` - Update email, reset email_verified

### SPA

- `ProfileView.vue` at `/profile` (requires auth)
- Sections:
  - Personal info: first_name, last_name, display_name
  - Preferences: locale dropdown (sv-SE, en-US)
  - Email: current email + change form
  - Password: current + new + confirm fields
- Add "Profil" link to `AuthSidebar.vue` and `AuthTopBar.vue`
- Use `useProfile.ts` composable for API calls

### Password change flow

1. User enters current password + new password + confirm
2. Client validates: new matches confirm, meets strength requirements
3. POST to `/api/v1/profile/password` with CSRF token
4. Success: show toast, clear form
5. Error: show inline error
