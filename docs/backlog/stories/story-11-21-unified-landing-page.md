---
type: story
id: ST-11-21
title: "Unified landing page (auth-adaptive home view)"
status: done
owners: "agents"
created: 2025-12-22
epic: "EPIC-11"
acceptance_criteria:
  - "Given an unauthenticated visitor, when visiting /, then the SPA displays a hero section with headline, tagline, and login CTA"
  - "Given an unauthenticated visitor, when viewing /, then three feature cards explain the value proposition (dela och återanvänd, enkel uppladdning, tryggt och lokalt)"
  - "Given an authenticated user, when visiting /, then the SPA displays a personalized greeting and quick navigation cards"
  - "Given an authenticated contributor+, when visiting /, then additional navigation cards for /my-tools and /suggestions/new are visible"
  - "All copy is in Swedish following the teacher-first, pedagogically sound tone"
ui_impact: "Replaces the minimal HomeView placeholder with a proper landing page that adapts based on auth state."
dependencies: ["ST-11-05"]
---

## Context

The original `HomeView.vue` was a placeholder with a single card linking to `/browse`. A proper landing page is needed to:

1. Explain what Skriptoteket is to unauthenticated visitors
2. Provide quick navigation for authenticated users
3. Adapt content based on role (contributor+ sees additional options)

## Implementation (2025-12-22)

### Design Decisions

1. **Single unified view**: One `HomeView.vue` with `v-if`/`v-else` based on `auth.isAuthenticated`
2. **No component extraction**: View is ~140 lines, kept self-contained
3. **Swedish copy**: All text in Swedish, teacher-focused, no generic sales language
4. **Brutalist styling**: HuleEdu design tokens via Tailwind (navy, burgundy, canvas, hard shadows)

### Pre-login State

Hero section:

- Headline: "Verktyg för lärare" (serif font, 4xl/5xl)
- Tagline: "Ladda upp en fil, välj ett verktyg, ladda ned resultatet."
- CTA: Navy "Logga in" button with brutalist shadow (hover burgundy)

Features (3 columns on md+, numbered cards with left border accent):

1. **Dela och återanvänd** - "Slipp skriva samma skript om och om igen. Hitta färdiga verktyg eller bidra med egna idéer."
2. **Enkel uppladdning** - "Ladda upp en fil, kör, ladda ner resultatet. Ingen IDE, ingen terminal, ingen installation."
3. **Tryggt och lokalt** - "Alla filer behandlas säkert på vår server. Verktyg granskas innan publicering."

Design: Burgundy number badges (-top-3 -left-2), 2px navy left border, no box shadow (cleaner look).

### Post-login State

Greeting: "Välkommen, [username]" (extracted from email prefix)

Quick navigation (2-column grid, clickable cards):

- **Hitta verktyg** -> `/browse` (all users)
- **Mina körningar** -> `/my-runs` (all users)
- **Mina verktyg** -> `/my-tools` (contributor+)
- **Föreslå verktyg** -> `/suggestions/new` (contributor+)

Design: Entire card is RouterLink, hover lifts card (translate + shadow-brutal), arrow indicator top-right, title turns burgundy on hover. Base card uses shadow-brutal-sm.

### Files Modified

- `frontend/apps/skriptoteket/src/views/HomeView.vue` - Auth-adaptive landing page
- `frontend/apps/skriptoteket/src/App.vue` - Global login modal, header login hidden on home
- `frontend/apps/skriptoteket/src/composables/useLoginModal.ts` - Shared login modal state
- `frontend/apps/skriptoteket/src/router/index.ts` - Protected routes trigger modal instead of redirect
- `src/skriptoteket/web/static/css/huleedu-design-tokens.css` - Canvas color adjusted (#F9F8F2 -> #FAFAF6)

### Auth State Logic

```typescript
const auth = useAuthStore();
const isAuthenticated = computed(() => auth.isAuthenticated);
const canSeeContributor = computed(() => auth.hasAtLeastRole("contributor"));
const userName = computed(() => auth.user?.email.split("@")[0] ?? null);
```

### Verification

- `pdm run fe-build` - Build successful
- `pnpm vue-tsc --noEmit` - TypeScript checks passed
