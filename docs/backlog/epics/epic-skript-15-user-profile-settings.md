---
type: epic
id: EPIC-SKRIPT-15
title: User Profile & Settings
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
outcome: Users can view and edit their profile with clear view/edit separation, brutalist
  design, and mobile responsiveness.
retired_ids:
- EPIC-15
---

## Scope

Source: `docs/backlog/epics/epic-15-user-profile-and-settings.md`. User Profile & Settings.

- Profile page redesign with view/edit mode separation (inline expansion pattern). - Initials-based avatar display with placeholder for future upload feature. - Personal info editing (first name, last name, display name, locale). - Email change flow (validated against current email). - Password change flow (current password, new password with confirmation). - Brutalist design following HuleEdu design tokens (navy, burgundy, canvas). - Mobile-responsive layout. - Avatar upload (deferred to ST-15-02). - App-wide settings page (locale remains on profile for now). - Two-factor authentication / security settings page. - Profile visibility / privacy settings. - [ST-15-01: User Profile Page Redesig

## Epic Contract

The epic outcome and capability boundary remain those declared by the source record.

## ADR Coverage

Source relationship evidence: ST-15-02, ST-15-01, ADR-0040, ADR-0037.

## Contract Inputs

- Source record and audit-approved migration authority.
- Current relationship fields in candidate frontmatter.

## Stories

Current story references remain only where represented by candidate frontmatter; terminal records are historical evidence.

## Epic Verification Plan

Verify each current story against the epic outcome and retain bounded proof at story/task closeout.

## Exceptions And Follow-Ups

No new exception or follow-up is authorized here.

## Risks

Relationship drift or terminal ancestry must be resolved by the parent manifest before apply.

## Notes

### Source evidence

### Scope

- Profile page redesign with view/edit mode separation (inline expansion pattern).
- Initials-based avatar display with placeholder for future upload feature.
- Personal info editing (first name, last name, display name, locale).
- Email change flow (validated against current email).
- Password change flow (current password, new password with confirmation).
- Brutalist design following HuleEdu design tokens (navy, burgundy, canvas).
- Mobile-responsive layout.

### Out of Scope

- Avatar upload (deferred to ST-15-02).
- App-wide settings page (locale remains on profile for now).
- Two-factor authentication / security settings page.
- Profile visibility / privacy settings.

### Stories

- [ST-15-01: User Profile Page Redesign](../stories/story-15-01-user-profile-redesign.md)
- [ST-15-02: Avatar Upload](../stories/story-15-02-avatar-upload.md) (planned)

### Risks

- None identified for current scope.

### Dependencies

- ADR-0040 (Profile View/Edit Mode Separation)
- ADR-0037 (Toast and System Messages)
- Existing `useProfile()` composable and API endpoints (no backend changes needed)

## Decision And Assumption Ledger

| ID | Type | Status | Question/Assumption | Recommendation/Decision | Source |
| --- | --- | --- | --- | --- | --- |
| MIG-EPIC-SKRIPT-15 | migration | closed | How is source meaning preserved? | Preserve the source outcome and current contract while changing identity only. | ST-SKILL-08-06; TASK-SKRIPT-REP-0003 |

## Plan Document Review

No specialist approval is asserted; parent review remains required.

## Epic Closeout Review

No closeout evidence is asserted in this candidate.
