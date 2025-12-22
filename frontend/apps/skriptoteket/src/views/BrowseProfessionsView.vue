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
      errorMessage.value = "Failed to load professions";
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
  <div class="browse-professions">
    <h2 class="browse-professions__title">Blaeddra verktyg</h2>
    <p class="browse-professions__subtitle">Vaelj en yrkesgrupp foer att se kategorier och verktyg.</p>

    <div
      v-if="isLoading"
      class="browse-professions__loading"
    >
      <span class="browse-professions__spinner" />
      <span>Laddar...</span>
    </div>

    <div
      v-else-if="errorMessage"
      class="browse-professions__error"
    >
      {{ errorMessage }}
    </div>

    <ul
      v-else
      class="browse-professions__list"
    >
      <li
        v-for="profession in professions"
        :key="profession.id"
        class="browse-professions__item"
      >
        <RouterLink :to="`/browse/${profession.slug}`">
          <span class="browse-professions__label">{{ profession.label }}</span>
        </RouterLink>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.browse-professions {
  max-width: 600px;
}

.browse-professions__title {
  margin: 0 0 0.5rem 0;
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--huleedu-navy, #1C2E4A);
}

.browse-professions__subtitle {
  margin: 0 0 1.5rem 0;
  font-size: 0.875rem;
  color: rgba(28, 46, 74, 0.6);
}

.browse-professions__loading {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  color: rgba(28, 46, 74, 0.6);
}

.browse-professions__spinner {
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

.browse-professions__error {
  padding: 0.75rem 1rem;
  border: 1px solid var(--huleedu-burgundy, #6B1C2E);
  color: var(--huleedu-burgundy, #6B1C2E);
  background-color: var(--huleedu-canvas, #F9F8F2);
}

.browse-professions__list {
  list-style: none;
  margin: 0;
  padding: 0;
  border: 1px solid var(--huleedu-navy, #1C2E4A);
  background-color: #fff;
}

.browse-professions__item {
  border-bottom: 1px solid rgba(28, 46, 74, 0.2);
}

.browse-professions__item:last-child {
  border-bottom: none;
}

.browse-professions__item a {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  text-decoration: none;
  color: inherit;
  transition: background-color 0.15s ease;
}

.browse-professions__item a::after {
  content: "\2192";
  color: rgba(28, 46, 74, 0.4);
  transition: color 0.15s ease;
}

.browse-professions__item a:hover {
  background-color: rgba(28, 46, 74, 0.02);
}

.browse-professions__item a:hover::after {
  color: var(--huleedu-burgundy, #6B1C2E);
}

.browse-professions__label {
  font-weight: 500;
}
</style>
