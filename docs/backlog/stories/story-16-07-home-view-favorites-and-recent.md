---
type: story
id: ST-16-07
title: "Home view favorites and recently used sections"
status: ready
owners: "agents"
created: 2025-12-26
epic: EPIC-16
acceptance_criteria:
  - "Given user has favorites, when visiting home, then 'Dina favoriter' section shows up to 5 tools"
  - "Given user has run tools, when visiting home, then 'Senast använda' section shows up to 5 tools"
  - "Given user has no favorites, when visiting home, then 'Dina favoriter' section is hidden (not empty state)"
  - "Given user has no recent tools, when visiting home, then 'Senast använda' section is hidden"
  - "Given sections rendered, when user clicks tool card, then navigates to /tool-run/{slug}"
  - "Given sections rendered, when user toggles favorite star, then favorite state updates"
  - "Given 'Visa alla' link in favorites section, when clicked, then navigates to /favorites (or /browse with favorite filter)"
---

## Context

This story adds personalized sections to the home page, giving teachers quick access to their most-used and bookmarked tools without navigating to the catalog.

## UI layout

```
┌─────────────────────────────────────────────────────────────┐
│ Välkommen till Skriptoteket                                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ DINA FAVORITER                              [Visa alla →]   │
│ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐       │
│ │ Ordlista   ★  │ │ Textanalys ★  │ │ Mattetest  ★  │       │
│ │ [Välj →]      │ │ [Välj →]      │ │ [Välj →]      │       │
│ └───────────────┘ └───────────────┘ └───────────────┘       │
│                                                             │
│ SENAST ANVÄNDA                                              │
│ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐       │
│ │ Ordlista   ★  │ │ Bokrecension☆ │ │ Läslogg    ☆  │       │
│ │ [Välj →]      │ │ [Välj →]      │ │ [Välj →]      │       │
│ └───────────────┘ └───────────────┘ └───────────────┘       │
│                                                             │
│ [Bläddra i katalogen →]                                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Implementation notes

### Section components

Create `frontend/apps/skriptoteket/src/components/home/FavoritesSection.vue`:

```vue
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { apiGet } from '@/api/client'
import ToolCard from '@/components/catalog/ToolCard.vue'

const tools = ref<Tool[]>([])
const isLoading = ref(true)

onMounted(async () => {
  const response = await apiGet<{ tools: Tool[] }>('/api/v1/favorites?limit=5')
  tools.value = response.tools
  isLoading.value = false
})
</script>

<template>
  <section v-if="tools.length > 0" class="home-section">
    <div class="home-section__header">
      <h2>Dina favoriter</h2>
      <RouterLink to="/browse?favorites=true">Visa alla →</RouterLink>
    </div>
    <div class="home-section__grid">
      <ToolCard v-for="tool in tools" :key="tool.id" :tool="tool" />
    </div>
  </section>
</template>
```

Create `frontend/apps/skriptoteket/src/components/home/RecentToolsSection.vue`:

Similar structure, calls `GET /api/v1/me/recent-tools?limit=5`.

### HomeView integration

Modify `frontend/apps/skriptoteket/src/views/HomeView.vue`:

```vue
<template>
  <div class="home">
    <h1>Välkommen till Skriptoteket</h1>

    <FavoritesSection />
    <RecentToolsSection />

    <RouterLink to="/browse" class="btn-primary">
      Bläddra i katalogen →
    </RouterLink>
  </div>
</template>
```

### Loading states

Each section manages its own loading state. Sections are hidden (not shown with empty state) when the user has no data.

## Files to create

- `frontend/apps/skriptoteket/src/components/home/FavoritesSection.vue`
- `frontend/apps/skriptoteket/src/components/home/RecentToolsSection.vue`

## Files to modify

- `frontend/apps/skriptoteket/src/views/HomeView.vue`

## Styling

```css
.home-section {
  margin-bottom: 2rem;
}

.home-section__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.home-section__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem;
}
```

## API calls

On home page load:

1. `GET /api/v1/favorites?limit=5` — user's favorites
2. `GET /api/v1/me/recent-tools?limit=5` — recently used

These can be fetched in parallel.
