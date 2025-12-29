<script setup lang="ts">
import { computed } from "vue";

import CatalogItemCard from "../components/catalog/CatalogItemCard.vue";
import { useCatalogFilters } from "../composables/useCatalogFilters";
import { useFavorites } from "../composables/useFavorites";

const {
  items,
  professions,
  categories,
  selectedProfessions,
  selectedCategories,
  searchInput,
  favoritesOnly,
  curatedOnly,
  isLoading,
  errorMessage,
  toggleProfession,
  toggleCategory,
  setFavoritesOnly,
  setCuratedOnly,
  clearFilters,
} = useCatalogFilters();

const { toggleFavorite, isToggling } = useFavorites();

const hasItems = computed(() => items.value.length > 0);

async function handleFavoriteToggled(payload: { id: string; isFavorite: boolean }): Promise<void> {
  if (isToggling(payload.id)) {
    return;
  }

  const previousItems = items.value;
  const nextIsFavorite = !payload.isFavorite;
  const hasTarget = previousItems.some((item) => item.id === payload.id);

  if (!hasTarget) {
    return;
  }

  items.value = previousItems.flatMap((item) => {
    if (item.id !== payload.id) {
      return item;
    }

    const updated = { ...item, is_favorite: nextIsFavorite };
    if (favoritesOnly.value && !nextIsFavorite) {
      return [];
    }
    return updated;
  });

  const finalIsFavorite = await toggleFavorite(payload.id, payload.isFavorite);
  if (finalIsFavorite !== nextIsFavorite) {
    items.value = previousItems;
  }
}
</script>

<template>
  <div class="max-w-6xl space-y-6">
    <header class="space-y-4">
      <div>
        <h2 class="page-title">Katalog</h2>
        <p class="page-description">Alla publicerade verktyg och kurerade appar.</p>
      </div>

      <div class="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div class="w-full lg:max-w-md space-y-1">
          <label class="text-xs font-semibold uppercase tracking-wide text-navy/70">
            Sök
          </label>
          <input
            v-model="searchInput"
            type="text"
            placeholder="Sök verktyg..."
            class="w-full border border-navy bg-white px-3 py-2 text-sm text-navy shadow-brutal-sm"
          >
        </div>
        <div class="w-full lg:w-auto">
          <div class="flex flex-col gap-3 border border-navy bg-white px-4 py-3 shadow-brutal-sm lg:min-w-[320px]">
            <label class="flex items-start gap-3 text-sm text-navy cursor-pointer">
              <input
                type="checkbox"
                class="mt-0.5 h-4 w-4 accent-burgundy"
                :checked="curatedOnly"
                @change="setCuratedOnly(($event.target as HTMLInputElement).checked)"
              >
              <span class="space-y-1">
                <span class="block text-xs font-semibold uppercase tracking-wide text-navy/70">
                  Enbart kurerade appar
                </span>
                <span class="block text-xs text-navy/60">
                  Visar enbart kurerade appar.
                </span>
              </span>
            </label>

            <label class="flex items-start gap-3 text-sm text-navy cursor-pointer">
              <input
                type="checkbox"
                class="mt-0.5 h-4 w-4 accent-burgundy"
                :checked="favoritesOnly"
                @change="setFavoritesOnly(($event.target as HTMLInputElement).checked)"
              >
              <span class="space-y-1">
                <span class="block text-xs font-semibold uppercase tracking-wide text-navy/70">
                  Enbart favoriter
                </span>
                <span class="block text-xs text-navy/60">
                  Visar bara bokmärkta verktyg och appar.
                </span>
              </span>
            </label>
          </div>
        </div>
      </div>
    </header>

    <div class="grid gap-6 lg:grid-cols-[260px_1fr]">
      <aside class="space-y-6">
        <section class="space-y-3">
          <h3 class="text-xs font-semibold uppercase tracking-wide text-navy/70">
            Yrkesgrupper
          </h3>
          <div class="p-4 border border-navy bg-white shadow-brutal-sm">
            <div
              v-if="professions.length === 0 && isLoading"
              class="flex items-center gap-2 text-sm text-navy/60"
            >
              <span
                class="inline-block w-3 h-3 border-2 border-navy/20 border-t-navy rounded-full animate-spin"
              />
              <span>Laddar...</span>
            </div>
            <div
              v-else
              class="grid gap-2"
            >
              <label
                v-for="profession in professions"
                :key="profession.id"
                class="flex items-center gap-2 text-sm text-navy cursor-pointer"
              >
                <input
                  :value="profession.slug"
                  type="checkbox"
                  class="h-4 w-4 accent-burgundy"
                  :checked="selectedProfessions.includes(profession.slug)"
                  @change="toggleProfession(profession.slug)"
                >
                <span>{{ profession.label }}</span>
              </label>
            </div>
          </div>
        </section>

        <section class="space-y-3">
          <h3 class="text-xs font-semibold uppercase tracking-wide text-navy/70">
            Kategorier
          </h3>
          <div class="p-4 border border-navy bg-white shadow-brutal-sm">
            <div
              v-if="categories.length === 0 && isLoading"
              class="flex items-center gap-2 text-sm text-navy/60"
            >
              <span
                class="inline-block w-3 h-3 border-2 border-navy/20 border-t-navy rounded-full animate-spin"
              />
              <span>Laddar...</span>
            </div>
            <div
              v-else
              class="grid gap-2"
            >
              <label
                v-for="category in categories"
                :key="category.id"
                class="flex items-center gap-2 text-sm text-navy cursor-pointer"
              >
                <input
                  :value="category.slug"
                  type="checkbox"
                  class="h-4 w-4 accent-burgundy"
                  :checked="selectedCategories.includes(category.slug)"
                  @change="toggleCategory(category.slug)"
                >
                <span>{{ category.label }}</span>
              </label>
            </div>
          </div>
        </section>

        <button
          type="button"
          class="btn-ghost w-full"
          @click="clearFilters"
        >
          Rensa filter
        </button>
      </aside>

      <section class="space-y-4">
        <div
          v-if="isLoading"
          class="flex items-center gap-3 p-4 text-navy/60"
        >
          <span class="inline-block w-4 h-4 border-2 border-navy/20 border-t-navy rounded-full animate-spin" />
          <span>Laddar...</span>
        </div>

        <div
          v-else-if="errorMessage"
          class="p-4 border border-burgundy bg-white shadow-brutal-sm text-sm text-burgundy"
        >
          {{ errorMessage }}
        </div>

        <div
          v-else-if="!hasItems"
          class="p-4 text-navy/60 italic"
        >
          Inga verktyg matchar filtren.
        </div>

        <div
          v-else
          class="space-y-4"
        >
          <div class="text-xs uppercase tracking-wide text-navy/60">
            Visar {{ items.length }} objekt
          </div>
          <div class="space-y-4">
            <CatalogItemCard
              v-for="item in items"
              :key="`${item.kind}-${item.id}`"
              :item="item"
              :is-toggling="isToggling(item.id)"
              @favorite-toggled="handleFavoriteToggled"
            />
          </div>
        </div>
      </section>
    </div>
  </div>
</template>
