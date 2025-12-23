<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";

import { apiGet, isApiError } from "../api/client";
import type { components } from "../api/openapi";

type ListCategoriesResponse = components["schemas"]["ListCategoriesResponse"];
type ProfessionItem = components["schemas"]["ProfessionItem"];
type CategoryItem = components["schemas"]["CategoryItem"];

const route = useRoute();

const profession = ref<ProfessionItem | null>(null);
const categories = ref<CategoryItem[]>([]);
const isLoading = ref(true);
const errorMessage = ref<string | null>(null);

const professionSlug = computed(() => {
  const param = route.params.profession;
  return typeof param === "string" ? param : "";
});

async function fetchCategories(): Promise<void> {
  if (!professionSlug.value) {
    return;
  }

  isLoading.value = true;
  errorMessage.value = null;

  try {
    const response = await apiGet<ListCategoriesResponse>(
      `/api/v1/catalog/professions/${encodeURIComponent(professionSlug.value)}/categories`,
    );
    profession.value = response.profession;
    categories.value = response.categories;
  } catch (error: unknown) {
    if (isApiError(error)) {
      errorMessage.value = error.message;
    } else if (error instanceof Error) {
      errorMessage.value = error.message;
    } else {
      errorMessage.value = "Det gick inte att ladda kategorier.";
    }
  } finally {
    isLoading.value = false;
  }
}

onMounted(() => {
  void fetchCategories();
});

watch(professionSlug, () => {
  void fetchCategories();
});
</script>

<template>
  <div class="max-w-2xl">
    <nav class="flex items-center flex-wrap gap-2 mb-4 text-xs uppercase tracking-wide text-navy/60">
      <RouterLink
        to="/browse"
        class="text-navy/70 border-b border-navy/40 pb-0.5 hover:text-burgundy hover:border-burgundy transition-colors"
      >
        Yrkesgrupper
      </RouterLink>
      <span class="text-navy/30">/</span>
      <span v-if="profession">{{ profession.label }}</span>
      <span v-else>...</span>
    </nav>

    <h2 class="text-2xl font-semibold text-navy mb-2">
      {{ profession?.label ?? "Laddar..." }}
    </h2>
    <p class="text-sm text-navy/60 mb-6">Välj en kategori för att se verktyg.</p>

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
      v-else-if="categories.length === 0"
      class="p-4 text-navy/60 italic"
    >
      Inga kategorier finns för denna yrkesgrupp.
    </div>

    <ul
      v-else
      class="list-none m-0 p-0 border border-navy bg-white"
    >
      <li
        v-for="category in categories"
        :key="category.id"
        class="border-b border-navy/20 last:border-b-0"
      >
        <RouterLink
          :to="`/browse/${professionSlug}/${category.slug}`"
          class="group flex justify-between items-center p-4 no-underline text-inherit hover:bg-canvas transition-colors"
        >
          <span class="font-medium">{{ category.label }}</span>
          <span class="text-navy/40 group-hover:text-burgundy transition-colors">→</span>
        </RouterLink>
      </li>
    </ul>
  </div>
</template>
