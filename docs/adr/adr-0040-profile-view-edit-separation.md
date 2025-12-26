---
type: adr
id: ADR-0040
title: "Profile page view/edit mode separation"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-26
links:
  - ADR-0037
  - ADR-0027
  - EPIC-15
  - ST-15-01
---

## Context

The current profile page (`ProfileView.vue`, 398 LOC) is a monolithic component with three always-visible edit forms (personal info, email, password). This creates several UX and architectural issues:

1. **No view/edit separation**: Users are always in "edit mode" with all forms visible.
2. **Cluttered interface**: Three forms competing for attention on a single page.
3. **State explosion**: 11 distributed refs managing form state across three sections.
4. **Repeated patterns**: Same error handling and save logic duplicated three times.
5. **Poor mobile UX**: Three full forms on small screens creates excessive scrolling.

The redesign requires choosing an edit interaction pattern and making decisions about related features (avatar, locale).

## Decision

### 1) Inline Expansion Pattern (not Drawer)

When users click "Edit" on a profile section:
- The section expands in-place to show the edit form
- Other sections collapse or dim to reduce visual noise
- Only one section is editable at a time

**Rationale**: Inline expansion is simpler than a drawer pattern and keeps the user's context on the same page. Drawers work well for complex side panels (like the script editor's `InstructionsDrawer`), but profile editing is simple enough that inline expansion provides a better focused experience without the overhead of a slide-out panel.

### 2) Initials-Based Avatar (Upload Deferred)

Display user initials in a colored circle:
```
┌─────────┐
│   OS    │  (from "Olof Sjödin")
└─────────┘
```

Avatar upload is explicitly deferred to a follow-up story (ST-15-02) because:
- Requires new backend work (storage, image processing, new API endpoint)
- Adds complexity that would expand the current story scope
- Initials provide adequate visual identity for MVP

### 3) Locale Remains on Profile (App Settings Deferred)

Language preference (`locale`) stays on the profile page rather than moving to a dedicated "app settings" UI. This decision can be revisited when/if an app settings feature is implemented.

### 4) Password Change on Same Page

Password change remains as a section on the profile page (not a separate security settings page). This keeps the implementation focused and matches the existing API structure.

## Component Architecture

```
ProfileView.vue (<200 LOC)         # Orchestrator only
├── ProfileDisplay.vue (<150 LOC)  # Read-only view mode
├── ProfileEditPersonal.vue        # Personal info form
├── ProfileEditEmail.vue           # Email change form
└── ProfileEditPassword.vue        # Password change form
```

State management:
- Parent owns `editingSection: 'personal' | 'email' | 'password' | null`
- Each edit component owns its own form state
- Transitions use Vue's `<Transition>` with smooth opacity/transform

## Consequences

**Benefits**:
- Clear separation between viewing and editing
- Reduced cognitive load (one task at a time)
- Smaller, focused components (all under LOC limits)
- Mobile-friendly (collapsed sections reduce scrolling)
- Consistent with brutalist design (clear visual hierarchy)

**Tradeoffs**:
- More component files to maintain
- Slightly more complex state coordination in parent
- Transitions may feel slower than instant form display

**Follow-ups**:
- ST-15-02: Avatar upload implementation
- Future: Consider app settings page for locale and other preferences
