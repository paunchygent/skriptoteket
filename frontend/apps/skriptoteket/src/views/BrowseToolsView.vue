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
  <div class="max-w-2xl">
    <nav class="flex items-center flex-wrap gap-2 mb-4 text-xs uppercase tracking-wide text-navy/60">
      <RouterLink
        to="/browse"
        class="text-navy/70 border-b border-navy/40 pb-0.5 hover:text-burgundy hover:border-burgundy transition-colors"
      >
        Yrkesgrupper
      </RouterLink>
      <span class="text-navy/30">/</span>
      <RouterLink
        v-if="profession"
        :to="`/browse/${professionSlug}`"
        class="text-navy/70 border-b border-navy/40 pb-0.5 hover:text-burgundy hover:border-burgundy transition-colors"
      >
        {{ profession.label }}
      </RouterLink>
      <span v-else>...</span>
      <span class="text-navy/30">/</span>
      <span v-if="category">{{ category.label }}</span>
      <span v-else>...</span>
    </nav>

    <h2 class="text-2xl font-semibold text-navy mb-2">
      {{ category?.label ?? "Laddar..." }}
    </h2>
    <p
      v-if="profession"
      class="text-sm text-navy/60 mb-6"
    >
      Verktyg foer {{ profession.label.toLowerCase() }}
    </p>

    <div
      v-if="isLoading"
      class="flex items-center gap-3 p-4 text-navy/60"
    >
      <span class="inline-block w-4 h-4 border-2 border-navy/20 border-t-navy rounded-full animate-spin" />
      <span>Laddar...</span>
    </div>

    <div
      v-else-if="errorMessage"
      class="p-3 border border-burgundy text-burgundy bg-canvas"
    >
      {{ errorMessage }}
    </div>

    <div
      v-else-if="!hasContent"
      class="p-4 text-navy/60 italic"
    >
      Inga verktyg finns i denna kategori.
    </div>

    <template v-else>
      <!-- Dynamic Tools -->
      <section
        v-if="tools.length > 0"
        class="mb-8 last:mb-0"
      >
        <h3 class="text-xs font-semibold uppercase tracking-wide text-navy/60 mb-3">Verktyg</h3>
        <ul class="list-none m-0 p-0 border border-navy bg-white">
          <li
            v-for="tool in tools"
            :key="tool.id"
            class="border-b border-navy/20 last:border-b-0"
          >
            <div class="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-3 sm:gap-4 p-4">
              <div class="flex flex-col gap-1 min-w-0">
                <span class="font-medium text-navy">{{ tool.title }}</span>
                <span
                  v-if="tool.summary"
                  class="text-sm text-navy/60 break-words"
                >{{ tool.summary }}</span>
              </div>
              <RouterLink
                :to="{ name: 'tool-run', params: { slug: tool.slug } }"
                class="shrink-0 w-full sm:w-auto text-center px-4 py-2 text-sm font-semibold uppercase tracking-wide text-canvas bg-burgundy rounded-sm hover:bg-navy transition-colors"
              >
                Koer
              </RouterLink>
            </div>
          </li>
        </ul>
      </section>

      <!-- Curated Apps -->
      <section
        v-if="curatedApps.length > 0"
        class="mb-8 last:mb-0"
      >
        <h3 class="text-xs font-semibold uppercase tracking-wide text-navy/60 mb-3">Kurerade appar</h3>
        <ul class="list-none m-0 p-0 border border-navy bg-white">
          <li
            v-for="app in curatedApps"
            :key="app.app_id"
            class="border-b border-navy/20 last:border-b-0"
          >
            <div class="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-3 sm:gap-4 p-4">
              <div class="flex flex-col gap-1 min-w-0">
                <span class="font-medium text-navy">{{ app.title }}</span>
                <span
                  v-if="app.summary"
                  class="text-sm text-navy/60 break-words"
                >{{ app.summary }}</span>
              </div>
              <a
                :href="`/apps/${app.app_id}`"
                class="shrink-0 w-full sm:w-auto text-center px-4 py-2 text-sm font-semibold uppercase tracking-wide text-canvas bg-burgundy rounded-sm hover:bg-navy transition-colors"
              >
                Oeppna
              </a>
            </div>
          </li>
        </ul>
      </section>
    </template>
  </div>
</template>
