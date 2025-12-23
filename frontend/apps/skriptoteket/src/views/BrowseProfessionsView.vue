<script setup lang="ts">
import { onMounted, ref } from "vue";

import { apiGet, isApiError } from "../api/client";
import type { components } from "../api/openapi";

type ListProfessionsResponse = components["schemas"]["ListProfessionsResponse"];
type ProfessionItem = components["schemas"]["ProfessionItem"];

const professions = ref<ProfessionItem[]>([]);
const isLoading = ref(true);
const errorMessage = ref<string | null>(null);

async function fetchProfessions(): Promise<void> {
  isLoading.value = true;
  errorMessage.value = null;

  try {
    const response = await apiGet<ListProfessionsResponse>(
      "/api/v1/catalog/professions",
    );
    professions.value = response.professions;
  } catch (error: unknown) {
    if (isApiError(error)) {
      errorMessage.value = error.message;
    } else if (error instanceof Error) {
      errorMessage.value = error.message;
    } else {
      errorMessage.value = "Det gick inte att ladda yrkesgrupper.";
    }
  } finally {
    isLoading.value = false;
  }
}

onMounted(() => {
  void fetchProfessions();
});
</script>

<template>
  <div class="max-w-2xl">
    <h2 class="text-2xl font-semibold text-navy mb-2">Bläddra verktyg</h2>
    <p class="text-sm text-navy/60 mb-6">Välj en yrkesgrupp för att se kategorier och verktyg.</p>

    <div v-if="isLoading" class="flex items-center gap-3 p-4 text-navy/60">
      <span class="inline-block w-4 h-4 border-2 border-navy/20 border-t-navy rounded-full animate-spin" />
      <span>Laddar...</span>
    </div>

    <div
      v-else-if="errorMessage"
      class="p-4 border border-burgundy bg-white shadow-brutal-sm text-sm text-burgundy"
    >
      {{ errorMessage }}
    </div>

    <ul v-else class="list-none m-0 p-0 border border-navy bg-white">
      <li
        v-for="profession in professions"
        :key="profession.id"
        class="border-b border-navy/20 last:border-b-0"
      >
        <RouterLink
          :to="`/browse/${profession.slug}`"
          class="group flex justify-between items-center p-4 no-underline text-inherit hover:bg-canvas transition-colors"
        >
          <span class="font-medium">{{ profession.label }}</span>
          <span class="text-navy/40 group-hover:text-burgundy transition-colors">→</span>
        </RouterLink>
      </li>
    </ul>
  </div>
</template>
