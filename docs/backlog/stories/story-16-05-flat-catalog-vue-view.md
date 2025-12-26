---
type: story
id: ST-16-05
title: "Flat catalog Vue view with filter sidebar and search"
status: ready
owners: "agents"
created: 2025-12-26
epic: EPIC-16
acceptance_criteria:
  - "Given /browse route, when loaded, then shows all published tools in flat list"
  - "Given filter sidebar, when user checks 'Svenska' category, then API is called with categories=svenska and tools are filtered"
  - "Given multiple categories checked, when filtering, then uses OR logic (shows tools matching any)"
  - "Given search input, when user types 'ord', then after 300ms debounce API is called with q=ord"
  - "Given active filters, when user views URL, then filters are reflected in query params (?categories=svenska&q=ord)"
  - "Given URL with ?categories=svenska, when page loads, then 'Svenska' checkbox is pre-selected"
  - "Given 'Rensa filter' button clicked, when actioned, then all filters are cleared and URL is reset"
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
import { useCatalogFilters } from '@/composables/useCatalogFilters'
import ToolCard from '@/components/catalog/ToolCard.vue'

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
  component: () => import('@/views/BrowseFlatView.vue'),
  meta: { requiresAuth: true },
}
```

Old hierarchical routes (`/browse/:profession`, `/browse/:profession/:category`) can remain as alternative paths.

## Files to create

- `frontend/apps/skriptoteket/src/views/BrowseFlatView.vue`
- `frontend/apps/skriptoteket/src/composables/useCatalogFilters.ts`

## Files to modify

- `frontend/apps/skriptoteket/src/router/routes.ts` (update /browse route)

## Styling

Follow existing brutalist design patterns:

- Border boxes with `border-navy`
- No hover effects on checkboxes
- Neutral color palette
- Clear visual hierarchy
