<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";

import { apiGet, isApiError } from "../api/client";
import type { components } from "../api/openapi";
import ToolListRow from "../components/tools/ToolListRow.vue";

type ListMyToolsResponse = components["schemas"]["ListMyToolsResponse"];
type MyToolItem = components["schemas"]["MyToolItem"];

const tools = ref<MyToolItem[]>([]);
const isLoading = ref(true);
const errorMessage = ref<string | null>(null);

const hasTools = computed(() => tools.value.length > 0);

async function loadTools(): Promise<void> {
  isLoading.value = true;
  errorMessage.value = null;

  try {
    const response = await apiGet<ListMyToolsResponse>("/api/v1/my-tools");
    tools.value = response.tools;
  } catch (error: unknown) {
    if (isApiError(error)) {
      errorMessage.value = error.message;
    } else if (error instanceof Error) {
      errorMessage.value = error.message;
    } else {
      errorMessage.value = "Det gick inte att ladda verktyg.";
    }
  } finally {
    isLoading.value = false;
  }
}

onMounted(() => {
  void loadTools();
});
</script>

<template>
  <div class="max-w-4xl space-y-6">
    <div class="space-y-2">
      <h1 class="text-2xl font-semibold text-navy">
        Mina verktyg
      </h1>
      <p class="text-sm text-navy/60">
        Verktyg som du ansvarar för att underhålla.
      </p>
    </div>

    <div
      v-if="isLoading"
      class="p-4 border border-navy bg-white shadow-brutal-sm text-sm text-navy/70"
    >
      Laddar...
    </div>

    <div
      v-else-if="errorMessage"
      class="p-4 border border-error bg-white shadow-brutal-sm text-sm text-error"
    >
      {{ errorMessage }}
    </div>

    <div
      v-else-if="!hasTools"
      class="p-4 border border-navy bg-white shadow-brutal-sm text-sm text-navy/70"
    >
      Du har inga verktyg att underhålla ännu.
    </div>

    <ul
      v-else
      class="border border-navy bg-white shadow-brutal-sm divide-y divide-navy/15"
    >
      <ToolListRow
        v-for="tool in tools"
        :key="tool.id"
        grid-class="sm:grid-cols-[1fr_9rem_auto]"
        status-class="justify-self-start"
      >
        <template #main>
          <div class="text-base font-semibold text-navy truncate">
            {{ tool.title }}
          </div>
          <div
            v-if="tool.summary"
            class="text-xs text-navy/70"
          >
            {{ tool.summary }}
          </div>
        </template>

        <template #status>
          <span
            class="text-xs whitespace-nowrap"
            :class="tool.is_published ? 'text-success font-medium' : 'text-navy/50'"
          >
            {{ tool.is_published ? "Publicerad" : "Ej publicerad" }}
          </span>
        </template>

        <template #actions>
          <RouterLink
            :to="`/admin/tools/${tool.id}`"
            class="px-4 py-2 text-xs font-bold uppercase tracking-widest bg-white text-navy border border-navy shadow-brutal-sm hover:bg-canvas btn-secondary-hover transition-colors active:translate-x-1 active:translate-y-1 active:shadow-none"
          >
            Redigera
          </RouterLink>
        </template>
      </ToolListRow>
    </ul>
  </div>
</template>
