---
type: story
id: ST-16-05
title: "Flat catalog Vue view with filter sidebar and search"
status: done
owners: "agents"
created: 2025-12-26
updated: 2025-12-28
epic: EPIC-16
acceptance_criteria:
  - "Given /browse route, when loaded, then shows all published tools in flat list"
  - "Given filter sidebar, when user checks 'Svenska' category, then API is called with categories=svenska and tools are filtered"
  - "Given multiple categories checked, when filtering, then uses OR logic (shows tools matching any)"
  - "Given multiple professions checked, when filtering, then uses OR logic (shows tools matching any)"
  - "Given search input, when user types 'ord', then after 300ms debounce API is called with q=ord"
  - "Given active filters, when user views URL, then filters are reflected in query params (?categories=svenska&q=ord)"
  - "Given URL with ?categories=svenska, when page loads, then 'Svenska' checkbox is pre-selected"
  - "Given URL with ?favorites=true, when page loads, then only favorited tools are shown (frontend-only filter)"
  - "Given 'Rensa filter' button clicked, when actioned, then all filters are cleared and URL is reset"
  - "Given user clicks 'Bläddra efter yrkesgrupp', when actioned, then navigates to /browse/professions"
  - "Given loading state, when API is fetching, then loading indicator is shown"
---

## Context

This story implements the new flat catalog Vue view that replaces the hierarchical browse as the primary discovery experience. It enables filtering across all labels and text search.

## UI layout

```
┌─────────────────────────────────────────────────────────────┐
│ Katalog                                                     │
├─────────────────────────────────────────────────────────────┤
│ [Sök verktyg... ____________________________]               │
├─────────────────┬───────────────────────────────────────────┤
│ YRKESGRUPPER    │                                           │
│ ☐ Lärare        │  ┌─────────────────────────────────┐      │
│ ☐ Skolkuratorer │  │ Ordlistegenerator          ★    │      │
│                 │  │ Skapar ordlistor från text      │      │
│ KATEGORIER      │  │ [Välj →]                        │      │
│ ☑ Svenska       │  └─────────────────────────────────┘      │
│ ☐ Matematik     │                                           │
│ ☐ Engelska      │  ┌─────────────────────────────────┐      │
│                 │  │ Textanalys                 ☆    │      │
│ [Rensa filter]  │  │ Analyserar text                 │      │
│                 │  │ [Välj →]                        │      │
│                 │  └─────────────────────────────────┘      │
│                 │                                           │
│                 │  Visar 12 verktyg                         │
└─────────────────┴───────────────────────────────────────────┘
```

## Implementation notes

### View component

Create `frontend/apps/skriptoteket/src/views/BrowseFlatView.vue`:

```vue
<script setup lang="ts">
import { useCatalogFilters } from "../composables/useCatalogFilters";
import ToolCard from "../components/catalog/ToolCard.vue";

const {
  tools,
  professions,
  categories,
  selectedProfessions,
  selectedCategories,
  searchTerm,
  isLoading,
  toggleProfession,
  toggleCategory,
  clearFilters,
} = useCatalogFilters()
</script>
```

### Composable

Create `frontend/apps/skriptoteket/src/composables/useCatalogFilters.ts`:

- Manages filter state
- Syncs with URL query params (vue-router)
- Debounces search input (300ms)
- Calls `GET /api/v1/catalog/tools` with current filters
- Supports `favorites=true` as a frontend-only filter (client-side filter on `is_favorite`, not an API parameter)

### URL sync

Use Vue Router's `useRoute` and `router.push` to:

1. Read initial state from URL on mount
2. Update URL when filters change
3. Watch route changes to update state (browser back/forward)

### Routing

Modify `frontend/apps/skriptoteket/src/router/routes.ts`:

```typescript
{
  path: '/browse',
  name: 'browse',
  component: () => import('../views/BrowseFlatView.vue'),
  meta: { requiresAuth: true },
}
```

To preserve the hierarchical browse flow without conflicting with the new flat `/browse` route, introduce a clear
hierarchical entrypoint:

- `/browse/professions` -> `BrowseProfessionsView.vue`
- `/browse/professions/:profession` -> `BrowseCategoriesView.vue`
- `/browse/professions/:profession/:category` -> `BrowseToolsView.vue`

Update breadcrumb links inside the hierarchical views so “Yrkesgrupper” points to `/browse/professions`.

## Files to create

- `frontend/apps/skriptoteket/src/views/BrowseFlatView.vue`
- `frontend/apps/skriptoteket/src/composables/useCatalogFilters.ts`

## Files to modify

- `frontend/apps/skriptoteket/src/router/routes.ts` (update /browse route)
- `frontend/apps/skriptoteket/src/views/BrowseProfessionsView.vue` (update links to `/browse/professions/:profession`)
- `frontend/apps/skriptoteket/src/views/BrowseCategoriesView.vue` (breadcrumb back-link to `/browse/professions`)
- `frontend/apps/skriptoteket/src/views/BrowseToolsView.vue` (breadcrumb back-link to `/browse/professions`)

## Styling

Follow existing brutalist design patterns:

- Border boxes with `border-navy`
- No hover effects on checkboxes
- Neutral color palette
- Clear visual hierarchy
