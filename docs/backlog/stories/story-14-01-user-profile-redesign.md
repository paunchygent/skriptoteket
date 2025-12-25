---
type: story
id: ST-14-01
title: User Profile Page Redesign
status: ready
owners: [frontend-lead]
created: 2025-12-26
epic: EPIC-14
acceptance_criteria:
  - View mode displays all user info in clean, scannable layout
  - Edit actions are clearly discoverable but not intrusive
  - Each edit operation (personal, email, password) is isolated
  - Success feedback via toast, errors via inline or SystemMessage
  - Follows HuleEdu design tokens (canvas, navy, burgundy)
  - Brutalist aesthetic (hard shadows, high contrast)
  - Mobile-responsive layout
  - ProfileView.vue reduced to <200 LOC (orchestration only)
  - Each sub-component <150 LOC
---

# ST-14-01: User Profile Page Redesign

## Session Scope

**Objective**: Redesign the user profile page to separate presentation from editing, following Skriptoteket's brutalist design language and HuleEdu design tokens.

**Current State**: `ProfileView.vue` (398 lines) is a single-mode form with three sections (personal info, email, password) that feels cluttered and doesn't follow good UX separation principles.

**Target State**: A clean profile page with:
1. **View Mode**: Read-only presentation of user data
2. **Edit Mode**: Focused editing experience (one section at a time or drawer-based)
3. **Visual hierarchy** following brutalist design principles

---

## Required Reading (Before Starting)

### Architecture & Rules
1. **`.agent/rules/000-rule-index.md`** - Master index of all project rules
2. **`.agent/rules/011-frontend-architecture.md`** - Vue 3 SPA architecture patterns
3. **`.agent/rules/012-frontend-components.md`** - Component conventions
4. **`docs/adr/adr-0027-full-vue-vite-spa.md`** - SPA migration decision

### Design System
5. **`frontend/apps/skriptoteket/src/assets/main.css`** - Design tokens and Tailwind 4 `@theme inline` configuration
6. **`frontend/apps/skriptoteket/src/components/ui/`** - Existing UI primitives

### Current Implementation
7. **`frontend/apps/skriptoteket/src/views/ProfileView.vue`** - Current profile page (398 lines)
8. **`frontend/apps/skriptoteket/src/stores/user.ts`** - User state management

---

## Design System Overview

### HuleEdu Color Palette

```css
/* Primary colors - use these */
--color-canvas: #f5f2eb;      /* Background (warm off-white) */
--color-navy: #1a2a3a;        /* Primary text, headers */
--color-burgundy: #8b2942;    /* Accent, CTAs */

/* Semantic colors */
--color-success: #2d5a27;     /* Green for success states */
--color-warning: #c4841d;     /* Amber for warnings */
--color-error: #b91c1c;       /* Red for errors */
```

### Brutalist Design Principles

1. **Hard shadows** - No blur, no soft gradients
   ```css
   box-shadow: 4px 4px 0 var(--color-navy);
   ```

2. **High contrast** - Navy on canvas, clear visual hierarchy

3. **Grid-based layouts** - Systematic spacing using `gap-4`, `gap-6`

4. **Typography hierarchy**:
   - `text-2xl font-bold` for page titles
   - `text-lg font-semibold` for section headers
   - `text-base` for body text
   - `text-sm text-navy/70` for labels and helper text

### Button Primitives

```html
<!-- Primary action (form submits) -->
<button class="btn-primary">Save Changes</button>

<!-- Call-to-action (prominent actions) -->
<button class="btn-cta">Edit Profile</button>

<!-- Ghost/secondary (cancel, back) -->
<button class="btn-ghost">Cancel</button>
```

### Form Input Pattern

```html
<div class="space-y-1">
  <label class="block text-sm font-medium text-navy/70">Display Name</label>
  <input
    type="text"
    v-model="displayName"
    class="w-full px-3 py-2 border border-navy/20 rounded-md
           focus:ring-2 focus:ring-burgundy focus:border-burgundy"
  />
</div>
```

---

## Feedback Patterns

### Toast (Transient Success/Info)
Use for non-blocking confirmations:
```typescript
import { useToast } from '@/composables/useToast'

const { showSuccess, showError } = useToast()
showSuccess('Profile updated successfully')
```

### SystemMessage (Blocking Errors)
Use for errors requiring user attention:
```vue
<SystemMessage
  v-if="error"
  type="error"
  :message="error.message"
/>
```

---

## Recommended Architecture

### Component Structure

```
src/views/ProfileView.vue          # Main view (orchestrates modes)
src/components/profile/
├── ProfileDisplay.vue             # View mode - read-only presentation
├── ProfileEditPersonal.vue        # Edit personal info (name, display name)
├── ProfileEditEmail.vue           # Edit email (separate flow)
└── ProfileEditPassword.vue        # Change password (separate flow)
```

### View Mode Design

```
┌─────────────────────────────────────────────────┐
│  User Profile                                   │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌─────────┐  Olof Sjödin                      │
│  │  Avatar │  olof@example.com                 │
│  │   (O)   │  Member since Jan 2024            │
│  └─────────┘                                   │
│                                                 │
│  ─────────────────────────────────────────────  │
│                                                 │
│  Personal Information          [Edit →]        │
│  ├─ First name: Olof                           │
│  ├─ Last name: Sjödin                          │
│  └─ Display name: @olof                        │
│                                                 │
│  Account Settings              [Edit →]        │
│  ├─ Email: olof@example.com                    │
│  └─ Password: ••••••••         [Change →]     │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Edit Mode Options

**Option A: Inline Expansion**
- Click "Edit" expands section to form
- Other sections collapse/dim
- Focused, single-task editing

**Option B: Drawer Pattern**
- Click "Edit" opens right-side drawer (like `InstructionsDrawer.vue`)
- Main view stays visible but dimmed
- Consistent with script editor UX

**Discuss with user which pattern to use.**

---

## State Management

### User Store (`stores/user.ts`)

The user store already provides:
```typescript
const userStore = useUserStore()

// Read user data
userStore.user?.email
userStore.user?.profile?.displayName

// Actions
await userStore.fetchCurrentUser()
await userStore.updateProfile(profileData)
```

### Local Form State

Use `ref()` for form state, not direct store mutation:
```typescript
const formData = ref({
  firstName: userStore.user?.profile?.firstName ?? '',
  lastName: userStore.user?.profile?.lastName ?? '',
  displayName: userStore.user?.profile?.displayName ?? '',
})

async function savePersonalInfo() {
  await userStore.updateProfile(formData.value)
  showSuccess('Profile updated')
  isEditing.value = false
}
```

---

## API Endpoints

Current backend endpoints (no changes needed):

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/me` | Fetch current user + profile |
| PATCH | `/api/v1/me/profile` | Update profile fields |
| POST | `/api/v1/me/email` | Request email change |
| POST | `/api/v1/me/password` | Change password |

---

## Key Decisions Requiring User Input

Before implementing, discuss with user:

1. **Edit Pattern**: Inline expansion vs. drawer-based editing?
2. **Avatar**: Add avatar upload or keep initials-based?
3. **Email Change**: Keep current flow (verify new email) or simplify?
4. **Password Section**: Same page or separate security settings page?
5. **Locale/Language**: Add language preference toggle?

---

## Handoff Requirements

Upon completion, update:
1. **`.agent/handoff.md`** - Add profile redesign to completed work
2. **Create PR** with before/after screenshots
3. **Update this story** with implementation notes

---

## References

- Current implementation: `frontend/apps/skriptoteket/src/views/ProfileView.vue`
- Toast composable: `frontend/apps/skriptoteket/src/composables/useToast.ts`
- Drawer example: `frontend/apps/skriptoteket/src/components/script-editor/InstructionsDrawer.vue`
- Button primitives: `frontend/apps/skriptoteket/src/assets/main.css` (search for `.btn-`)
