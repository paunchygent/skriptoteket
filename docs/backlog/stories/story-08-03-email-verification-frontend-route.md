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
  - "Success: shows confirmation message and auto-redirects to / after 5 seconds"
  - "Expired token: shows error with direct button to resend verification email"
  - "Invalid token: shows error with link back to homepage"
  - "Loading state while verification is in progress"
---

## Problem

When users click the verification link in their email, they are directed to `/verify-email?token=xxx`. Currently there is no frontend route to handle this - the user sees a 404 or blank page.

## Current Behavior

1. User clicks verification link in email
2. Browser navigates to `https://skriptoteket.hule.education/verify-email?token=xxx`
3. No route exists - user sees error/blank page

## Design

### Visual Theme

Uses existing HuleEdu design tokens and Tailwind theme:

- Card: `.huleedu-card` (white bg, navy border, brutal shadow)
- Button: `.huleedu-btn` (burgundy, uppercase)
- Link: `.huleedu-link` (navy with underline)
- Colors: `text-navy`, `text-burgundy`, `bg-canvas`
- Shadows: `shadow-brutal`

### States

| State   | Trigger                            | Action                      |
| ------- | ---------------------------------- | --------------------------- |
| Loading | Page loads, API called             | Show spinner                |
| Success | 200 OK                             | Show message, auto-redirect |
| Expired | 400 + VERIFICATION_TOKEN_EXPIRED   | Show resend button          |
| Invalid | 400 + INVALID_VERIFICATION_TOKEN   | Show back link              |

### Mockups

#### LOADING

```text
┌─────────────────────────────────────────┐
│                                         │░░
│                  ◐                      │░░
│                                         │░░
│      Verifierar din e-postadress...     │░░
│                                         │░░
└─────────────────────────────────────────┘░░
  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
```

#### SUCCESS

```text
┌─────────────────────────────────────────┐
│                                         │░░
│                  ✓                      │░░
│                                         │░░
│       Ditt konto är verifierat.         │░░
│       Välkommen att [logga in].         │░░
│                    ↑                    │░░
│              länk till /                │░░
│                                         │░░
│       Omdirigeras om 5 sekunder...      │░░
│                                         │░░
└─────────────────────────────────────────┘░░
  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
```

#### EXPIRED

```text
┌─────────────────────────────────────────┐
│                                         │░░
│                  ⚠                      │░░
│                                         │░░
│    Verifieringslänken har gått ut       │░░
│                                         │░░
│    Länken är giltig i 24 timmar.        │░░
│                                         │░░
│      ┌───────────────────────┐          │░░
│      │    SKICKA NY LÄNK     │          │░░
│      └───────────────────────┘          │░░
│                                         │░░
└─────────────────────────────────────────┘░░
  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
```

Note: "Skicka ny länk" calls resend-verification API directly.
Backend must return user email from expired token lookup.

#### INVALID

```text
┌─────────────────────────────────────────┐
│                                         │░░
│                  ✕                      │░░
│                                         │░░
│        Ogiltig verifieringslänk         │░░
│                                         │░░
│    Länken kan redan ha använts          │░░
│    eller vara felaktig.                 │░░
│                                         │░░
│    [Ta mig tillbaka till startsidan]    │░░
│                 ↑                       │░░
│           länk till /                   │░░
│                                         │░░
└─────────────────────────────────────────┘░░
  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
```

### Element Styling (Tailwind Classes)

#### Card Container

```html
<div class="huleedu-card max-w-md mx-auto text-center p-12">
  <!-- content -->
</div>
```

Uses existing `.huleedu-card` from design tokens.

#### Status Icons

Use Tailwind with theme colors:

- Success: `text-navy text-5xl` (✓)
- Warning: `text-burgundy text-5xl` (⚠)
- Error: `text-burgundy text-5xl` (✕)
- Loading: `text-navy animate-spin` (spinner SVG)

#### Typography

```html
<!-- Heading -->
<h1 class="font-sans text-xl font-semibold text-navy mb-4">
  Ditt konto är verifierat.
</h1>

<!-- Body text -->
<p class="font-sans text-base text-navy leading-relaxed">
  Välkommen att <a href="/" class="huleedu-link">logga in</a>.
</p>

<!-- Subtext (countdown) -->
<p class="text-sm text-navy/60 mt-6">
  Omdirigeras om 5 sekunder...
</p>
```

#### Primary Button

```html
<button class="huleedu-btn">
  SKICKA NY LÄNK
</button>
```

Uses existing `.huleedu-btn` from design tokens.

#### Text Link

```html
<a href="/" class="huleedu-link">
  Ta mig tillbaka till startsidan
</a>
```

Uses existing `.huleedu-link` from design tokens.

### Missing Design Elements

**To be added to `huleedu-design-tokens.css` if needed:**

1. **Spinner animation** - Currently has `.huleedu-pulse`, may need a spin animation
2. **Icon sizes** - No icon size tokens, using Tailwind `text-5xl` (48px)

## Required Changes

### 1. Add Frontend Route

Create `/verify-email` route in Vue Router:

```ts
{
  path: '/verify-email',
  component: () => import('@/views/VerifyEmailView.vue'),
  meta: { requiresAuth: false }
}
```

### 2. Create VerifyEmailView Component

Location: `frontend/apps/skriptoteket/src/views/VerifyEmailView.vue`

### 3. API Integration

Verify token:

```text
POST /api/v1/auth/verify-email
Body: { "token": "xxx" }
```

Resend (for expired):

```text
POST /api/v1/auth/resend-verification
Body: { "email": "xxx" }
```

### 4. Backend Change Required

For "Skicka ny länk" to work on expired tokens, backend must:

- Return user email in the expired token error response, OR
- Add endpoint to get email from token without verifying

## Technical Notes

- Auto-redirect uses `setTimeout` + `router.push('/')`
- Show countdown: "Omdirigeras om X sekunder..."
- Cancel redirect if user clicks link manually

## References

- Backend handler: `src/skriptoteket/application/identity/handlers/verify_email.py`
- API endpoint: `src/skriptoteket/web/api/v1/auth.py`
- Verification URL format: `/verify-email?token={token}`
- Design tokens: `src/skriptoteket/web/static/css/huleedu-design-tokens.css`
- Tailwind theme: `frontend/apps/skriptoteket/src/styles/tailwind-theme.css`
