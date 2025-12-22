<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";

import { apiGet, isApiError } from "../api/client";
import type { components } from "../api/openapi";

type ListToolsResponse = components["schemas"]["ListToolsResponse"];
type ProfessionItem = components["schemas"]["ProfessionItem"];
type CategoryItem = components["schemas"]["CategoryItem"];
type ToolItem = components["schemas"]["ToolItem"];
type CuratedAppItem = components["schemas"]["CuratedAppItem"];

const route = useRoute();

const profession = ref<ProfessionItem | null>(null);
const category = ref<CategoryItem | null>(null);
const tools = ref<ToolItem[]>([]);
const curatedApps = ref<CuratedAppItem[]>([]);
const isLoading = ref(true);
const errorMessage = ref<string | null>(null);

const professionSlug = computed(() => {
  const param = route.params.profession;
  return typeof param === "string" ? param : "";
});

const categorySlug = computed(() => {
  const param = route.params.category;
  return typeof param === "string" ? param : "";
});

async function fetchTools(): Promise<void> {
  if (!professionSlug.value || !categorySlug.value) {
    return;
  }

  isLoading.value = true;
  errorMessage.value = null;

  try {
    const response = await apiGet<ListToolsResponse>(
      `/api/v1/catalog/professions/${encodeURIComponent(professionSlug.value)}/categories/${encodeURIComponent(categorySlug.value)}/tools`,
    );
    profession.value = response.profession;
    category.value = response.category;
    tools.value = response.tools;
    curatedApps.value = response.curated_apps;
  } catch (error: unknown) {
    if (isApiError(error)) {
      errorMessage.value = error.message;
    } else if (error instanceof Error) {
      errorMessage.value = error.message;
    } else {
      errorMessage.value = "Failed to load tools";
    }
  } finally {
    isLoading.value = false;
  }
}

onMounted(() => {
  void fetchTools();
});

watch([professionSlug, categorySlug], () => {
  void fetchTools();
});

const hasContent = computed(() => tools.value.length > 0 || curatedApps.value.length > 0);
</script>

<template>
  <div class="browse-tools">
    <nav class="browse-tools__breadcrumb">
      <RouterLink to="/browse">Yrkesgrupper</RouterLink>
      <span class="browse-tools__separator">/</span>
      <RouterLink
        v-if="profession"
        :to="`/browse/${professionSlug}`"
      >
        {{ profession.label }}
      </RouterLink>
      <span v-else>...</span>
      <span class="browse-tools__separator">/</span>
      <span v-if="category">{{ category.label }}</span>
      <span v-else>...</span>
    </nav>

    <h2 class="browse-tools__title">
      {{ category?.label ?? "Laddar..." }}
    </h2>
    <p
      v-if="profession"
      class="browse-tools__subtitle"
    >
      Verktyg foer {{ profession.label.toLowerCase() }}
    </p>

    <div
      v-if="isLoading"
      class="browse-tools__loading"
    >
      <span class="browse-tools__spinner" />
      <span>Laddar...</span>
    </div>

    <div
      v-else-if="errorMessage"
      class="browse-tools__error"
    >
      {{ errorMessage }}
    </div>

    <div
      v-else-if="!hasContent"
      class="browse-tools__empty"
    >
      Inga verktyg finns i denna kategori.
    </div>

    <template v-else>
      <!-- Dynamic Tools -->
      <section
        v-if="tools.length > 0"
        class="browse-tools__section"
      >
        <h3 class="browse-tools__section-title">Verktyg</h3>
        <ul class="browse-tools__list">
          <li
            v-for="tool in tools"
            :key="tool.id"
            class="browse-tools__item"
          >
            <div class="browse-tools__item-content">
              <div class="browse-tools__item-info">
                <span class="browse-tools__item-title">{{ tool.title }}</span>
                <span
                  v-if="tool.summary"
                  class="browse-tools__item-summary"
                >{{ tool.summary }}</span>
              </div>
              <a
                :href="`/tools/${tool.slug}/run`"
                class="browse-tools__item-action"
              >Koer</a>
            </div>
          </li>
        </ul>
      </section>

      <!-- Curated Apps -->
      <section
        v-if="curatedApps.length > 0"
        class="browse-tools__section"
      >
        <h3 class="browse-tools__section-title">Kurerade appar</h3>
        <ul class="browse-tools__list">
          <li
            v-for="app in curatedApps"
            :key="app.app_id"
            class="browse-tools__item"
          >
            <div class="browse-tools__item-content">
              <div class="browse-tools__item-info">
                <span class="browse-tools__item-title">{{ app.title }}</span>
                <span
                  v-if="app.summary"
                  class="browse-tools__item-summary"
                >{{ app.summary }}</span>
              </div>
              <a
                :href="`/apps/${app.app_id}`"
                class="browse-tools__item-action"
              >Oeppna</a>
            </div>
          </li>
        </ul>
      </section>
    </template>
  </div>
</template>

<style scoped>
.browse-tools {
  max-width: 700px;
}

.browse-tools__breadcrumb {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: rgba(28, 46, 74, 0.6);
}

.browse-tools__breadcrumb a {
  color: rgba(28, 46, 74, 0.7);
  text-decoration: none;
  border-bottom: 1px solid rgba(28, 46, 74, 0.4);
  padding-bottom: 2px;
  transition:
    color 0.15s ease,
    border-color 0.15s ease;
}

.browse-tools__breadcrumb a:hover {
  color: var(--huleedu-burgundy, #6B1C2E);
  border-color: var(--huleedu-burgundy, #6B1C2E);
}

.browse-tools__separator {
  color: rgba(28, 46, 74, 0.3);
}

.browse-tools__title {
  margin: 0 0 0.5rem 0;
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--huleedu-navy, #1C2E4A);
}

.browse-tools__subtitle {
  margin: 0 0 1.5rem 0;
  font-size: 0.875rem;
  color: rgba(28, 46, 74, 0.6);
}

.browse-tools__loading {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  color: rgba(28, 46, 74, 0.6);
}

.browse-tools__spinner {
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

.browse-tools__error {
  padding: 0.75rem 1rem;
  border: 1px solid var(--huleedu-burgundy, #6B1C2E);
  color: var(--huleedu-burgundy, #6B1C2E);
  background-color: var(--huleedu-canvas, #F9F8F2);
}

.browse-tools__empty {
  padding: 1rem;
  color: rgba(28, 46, 74, 0.6);
  font-style: italic;
}

.browse-tools__section {
  margin-bottom: 2rem;
}

.browse-tools__section:last-child {
  margin-bottom: 0;
}

.browse-tools__section-title {
  margin: 0 0 0.75rem 0;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: rgba(28, 46, 74, 0.6);
}

.browse-tools__list {
  list-style: none;
  margin: 0;
  padding: 0;
  border: 1px solid var(--huleedu-navy, #1C2E4A);
  background-color: #fff;
}

.browse-tools__item {
  border-bottom: 1px solid rgba(28, 46, 74, 0.2);
}

.browse-tools__item:last-child {
  border-bottom: none;
}

.browse-tools__item-content {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  padding: 1rem;
}

.browse-tools__item-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-width: 0;
}

.browse-tools__item-title {
  font-weight: 500;
  color: var(--huleedu-navy, #1C2E4A);
}

.browse-tools__item-summary {
  font-size: 0.875rem;
  color: rgba(28, 46, 74, 0.6);
  overflow-wrap: anywhere;
}

.browse-tools__item-action {
  display: inline-block;
  flex-shrink: 0;
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  text-decoration: none;
  color: var(--huleedu-canvas, #F9F8F2);
  background-color: var(--huleedu-burgundy, #6B1C2E);
  border-radius: 2px;
  transition: background-color 0.15s ease;
}

.browse-tools__item-action:hover {
  background-color: var(--huleedu-navy, #1C2E4A);
}

@media (max-width: 640px) {
  .browse-tools__item-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.75rem;
  }

  .browse-tools__item-action {
    width: 100%;
    text-align: center;
  }
}
</style>
