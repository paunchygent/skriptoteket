---
type: story
id: ST-08-03
title: "Email verification frontend route"
status: ready
owners: "agents"
created: 2025-12-30
epic: "EPIC-08"
acceptance_criteria:
  - "Frontend route /verify-email?token=xxx exists"
  - "Route calls POST /api/v1/auth/verify-email with token"
  - "Success: shows confirmation message and redirects to login"
  - "Expired token: shows error with link to request new verification email"
  - "Invalid token: shows generic error message"
  - "Loading state while verification is in progress"
---

## Problem

When users click the verification link in their email, they are directed to `/verify-email?token=xxx`. Currently there is no frontend route to handle this - the user sees a 404 or blank page.

## Current Behavior

1. User clicks verification link in email
2. Browser navigates to `https://skriptoteket.hule.education/verify-email?token=xxx`
3. No route exists - user sees error/blank page

## Required Changes

### 1. Add Frontend Route

Create `/verify-email` route in Vue Router that:
- Extracts `token` from query parameters
- Calls backend verification endpoint
- Handles all response states

### 2. Create VerifyEmailView Component

```
frontend/apps/skriptoteket/src/views/VerifyEmailView.vue
```

States to handle:
- **Loading**: "Verifierar din e-postadress..."
- **Success**: "Din e-postadress har verifierats! Du kan nu logga in."
- **Expired**: "Verifieringslänken har gått ut. [Begär ny länk]"
- **Invalid**: "Ogiltig verifieringslänk."

### 3. API Integration

Call existing endpoint:
```
POST /api/v1/auth/verify-email
Body: { "token": "xxx" }
```

Response codes:
- 200: Success
- 400 (VERIFICATION_TOKEN_EXPIRED): Token expired
- 400 (INVALID_VERIFICATION_TOKEN): Token invalid/used

## Technical Notes

- Use same brutalist styling as other auth pages
- Swedish copy throughout
- Consider auto-redirect to login after 3-5 seconds on success

## References

- Backend handler: `src/skriptoteket/application/identity/handlers/verify_email.py`
- API endpoint: `src/skriptoteket/web/api/v1/auth.py`
- Verification URL format: `/verify-email?token={token}`
