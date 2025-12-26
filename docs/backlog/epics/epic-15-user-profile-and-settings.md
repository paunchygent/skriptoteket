---
type: epic
id: EPIC-15
title: "User Profile & Settings"
status: active
owners: "agents"
created: 2025-12-26
outcome: "Users can view and edit their profile with clear view/edit separation, brutalist design, and mobile responsiveness."
---

## Scope

- Profile page redesign with view/edit mode separation (inline expansion pattern).
- Initials-based avatar display with placeholder for future upload feature.
- Personal info editing (first name, last name, display name, locale).
- Email change flow (validated against current email).
- Password change flow (current password, new password with confirmation).
- Brutalist design following HuleEdu design tokens (navy, burgundy, canvas).
- Mobile-responsive layout.

## Out of Scope

- Avatar upload (deferred to ST-15-02).
- App-wide settings page (locale remains on profile for now).
- Two-factor authentication / security settings page.
- Profile visibility / privacy settings.

## Stories

- [ST-15-01: User Profile Page Redesign](../stories/story-15-01-user-profile-redesign.md)
- [ST-15-02: Avatar Upload](../stories/story-15-02-avatar-upload.md) (planned)

## Risks

- None identified for current scope.

## Dependencies

- ADR-0040 (Profile View/Edit Mode Separation)
- ADR-0037 (Toast and System Messages)
- Existing `useProfile()` composable and API endpoints (no backend changes needed)
