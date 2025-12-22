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
      errorMessage.value = "Failed to load categories";
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
  <div class="browse-categories">
    <nav class="browse-categories__breadcrumb">
      <RouterLink to="/browse">Yrkesgrupper</RouterLink>
      <span class="browse-categories__separator">/</span>
      <span v-if="profession">{{ profession.label }}</span>
      <span v-else>...</span>
    </nav>

    <h2 class="browse-categories__title">
      {{ profession?.label ?? "Laddar..." }}
    </h2>
    <p class="browse-categories__subtitle">Vaelj en kategori foer att se verktyg.</p>

    <div
      v-if="isLoading"
      class="browse-categories__loading"
    >
      <span class="browse-categories__spinner" />
      <span>Laddar...</span>
    </div>

    <div
      v-else-if="errorMessage"
      class="browse-categories__error"
    >
      {{ errorMessage }}
    </div>

    <div
      v-else-if="categories.length === 0"
      class="browse-categories__empty"
    >
      Inga kategorier finns foer denna yrkesgrupp.
    </div>

    <ul
      v-else
      class="browse-categories__list"
    >
      <li
        v-for="category in categories"
        :key="category.id"
        class="browse-categories__item"
      >
        <RouterLink :to="`/browse/${professionSlug}/${category.slug}`">
          <span class="browse-categories__label">{{ category.label }}</span>
        </RouterLink>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.browse-categories {
  max-width: 600px;
}

.browse-categories__breadcrumb {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: rgba(28, 46, 74, 0.6);
}

.browse-categories__breadcrumb a {
  color: rgba(28, 46, 74, 0.7);
  text-decoration: none;
  border-bottom: 1px solid rgba(28, 46, 74, 0.4);
  padding-bottom: 2px;
  transition:
    color 0.15s ease,
    border-color 0.15s ease;
}

.browse-categories__breadcrumb a:hover {
  color: var(--huleedu-burgundy, #6B1C2E);
  border-color: var(--huleedu-burgundy, #6B1C2E);
}

.browse-categories__separator {
  color: rgba(28, 46, 74, 0.3);
}

.browse-categories__title {
  margin: 0 0 0.5rem 0;
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--huleedu-navy, #1C2E4A);
}

.browse-categories__subtitle {
  margin: 0 0 1.5rem 0;
  font-size: 0.875rem;
  color: rgba(28, 46, 74, 0.6);
}

.browse-categories__loading {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  color: rgba(28, 46, 74, 0.6);
}

.browse-categories__spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(28, 46, 74, 0.2);
  border-top-color: var(--huleedu-navy, #1C2E4A);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.browse-categories__error {
  padding: 0.75rem 1rem;
  border: 1px solid var(--huleedu-burgundy, #6B1C2E);
  color: var(--huleedu-burgundy, #6B1C2E);
  background-color: var(--huleedu-canvas, #F9F8F2);
}

.browse-categories__empty {
  padding: 1rem;
  color: rgba(28, 46, 74, 0.6);
  font-style: italic;
}

.browse-categories__list {
  list-style: none;
  margin: 0;
  padding: 0;
  border: 1px solid var(--huleedu-navy, #1C2E4A);
  background-color: #fff;
}

.browse-categories__item {
  border-bottom: 1px solid rgba(28, 46, 74, 0.2);
}

.browse-categories__item:last-child {
  border-bottom: none;
}

.browse-categories__item a {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  text-decoration: none;
  color: inherit;
  transition: background-color 0.15s ease;
}

.browse-categories__item a::after {
  content: "\2192";
  color: rgba(28, 46, 74, 0.4);
  transition: color 0.15s ease;
}

.browse-categories__item a:hover {
  background-color: rgba(28, 46, 74, 0.02);
}

.browse-categories__item a:hover::after {
  color: var(--huleedu-burgundy, #6B1C2E);
}

.browse-categories__label {
  font-weight: 500;
}
</style>
