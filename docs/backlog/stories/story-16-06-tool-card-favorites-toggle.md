---
type: story
id: ST-16-06
title: "Tool card favorites toggle (star icon)"
status: ready
owners: "agents"
created: 2025-12-26
epic: EPIC-16
acceptance_criteria:
  - "Given tool card, when rendered, then shows star icon in top-right corner"
  - "Given tool is favorited, when rendered, then star is filled (★)"
  - "Given tool is not favorited, when rendered, then star is outline (☆)"
  - "Given user clicks star on non-favorite, when actioned, then POST /api/v1/favorites/{id} is called and star fills"
  - "Given user clicks star on favorite, when actioned, then DELETE /api/v1/favorites/{id} is called and star unfills"
  - "Given API call in progress, when star clicked, then button is disabled (prevent double-submit)"
  - "Given API call fails, when error occurs, then star reverts to previous state and toast shows error"
---

## Context

This story implements the favorite toggle on tool cards, allowing users to bookmark tools with a single click. The star icon provides immediate visual feedback.

## Component design

### ToolCard.vue

Create `frontend/apps/skriptoteket/src/components/catalog/ToolCard.vue`:

```vue
<script setup lang="ts">
import { useFavorites } from '@/composables/useFavorites'

const props = defineProps<{
  tool: {
    id: string
    slug: string
    title: string
    summary: string | null
    is_favorite: boolean
  }
}>()

const { toggleFavorite, isToggling } = useFavorites()

async function handleToggle() {
  await toggleFavorite(props.tool.id, props.tool.is_favorite)
}
</script>

<template>
  <div class="tool-card">
    <div class="tool-card__header">
      <h3>{{ tool.title }}</h3>
      <button
        @click.prevent="handleToggle"
        :disabled="isToggling"
        :aria-label="tool.is_favorite ? 'Ta bort favorit' : 'Lägg till favorit'"
        class="tool-card__favorite"
      >
        {{ tool.is_favorite ? '★' : '☆' }}
      </button>
    </div>
    <p v-if="tool.summary">{{ tool.summary }}</p>
    <RouterLink :to="{ name: 'tool-run', params: { slug: tool.slug } }">
      Välj →
    </RouterLink>
  </div>
</template>
```

### useFavorites composable

Create `frontend/apps/skriptoteket/src/composables/useFavorites.ts`:

```typescript
export function useFavorites() {
  const isToggling = ref(false)

  async function toggleFavorite(toolId: string, currentlyFavorite: boolean) {
    if (isToggling.value) return
    isToggling.value = true

    try {
      if (currentlyFavorite) {
        await apiFetch(`/api/v1/favorites/${toolId}`, { method: 'DELETE' })
      } else {
        await apiFetch(`/api/v1/favorites/${toolId}`, { method: 'POST' })
      }
      // Emit event or update local state
    } catch (error) {
      // Show toast error
      // Revert optimistic update if used
    } finally {
      isToggling.value = false
    }
  }

  return { toggleFavorite, isToggling }
}
```

## Optimistic updates

For better UX, consider:

1. Update star immediately on click (optimistic)
2. If API fails, revert to previous state
3. Show toast with error message

## Files to create

- `frontend/apps/skriptoteket/src/components/catalog/ToolCard.vue`
- `frontend/apps/skriptoteket/src/composables/useFavorites.ts`

## Styling

```css
.tool-card__favorite {
  font-size: 1.5rem;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--color-burgundy);
}

.tool-card__favorite:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
```

## Accessibility

- Use `aria-label` for screen readers
- Ensure button is focusable
- Show loading state during API call
