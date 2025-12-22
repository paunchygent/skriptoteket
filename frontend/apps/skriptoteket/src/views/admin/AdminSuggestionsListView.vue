<script setup lang="ts">
import { onMounted, ref } from "vue";
import { apiGet, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";

type ListSuggestionsResponse = components["schemas"]["ListSuggestionsResponse"];
type SuggestionSummary = components["schemas"]["SuggestionSummary"];
type SuggestionStatus = components["schemas"]["SuggestionStatus"];

const suggestions = ref<SuggestionSummary[]>([]);
const isLoading = ref(true);
const errorMessage = ref<string | null>(null);

function statusLabel(status: SuggestionStatus): string {
  const labels: Record<SuggestionStatus, string> = {
    pending_review: "Väntar på granskning",
    accepted: "Godkänd",
    denied: "Avslagen",
  };
  return labels[status];
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("sv-SE", { dateStyle: "medium", timeStyle: "short" });
}

async function load(): Promise<void> {
  isLoading.value = true;
  errorMessage.value = null;

  try {
    const response = await apiGet<ListSuggestionsResponse>("/api/v1/admin/suggestions");
    suggestions.value = response.suggestions;
  } catch (error: unknown) {
    if (isApiError(error)) {
      errorMessage.value = error.message;
    } else if (error instanceof Error) {
      errorMessage.value = error.message;
    } else {
      errorMessage.value = "Det gick inte att ladda förslag.";
    }
  } finally {
    isLoading.value = false;
  }
}

onMounted(() => {
  void load();
});
</script>

<template>
  <div class="space-y-6">
    <div class="space-y-2">
      <h1 class="text-2xl font-semibold text-navy">Förslag (granskning)</h1>
      <p class="text-sm text-navy/70">Lista över inkomna förslag som väntar på beslut.</p>
    </div>

    <div
      v-if="isLoading"
      class="p-4 border border-navy bg-white shadow-brutal-sm text-sm text-navy/70"
    >
      Laddar...
    </div>

    <div
      v-else-if="errorMessage"
      class="p-4 border border-burgundy bg-white shadow-brutal-sm text-sm text-burgundy"
    >
      {{ errorMessage }}
    </div>

    <div
      v-else-if="suggestions.length === 0"
      class="p-4 border border-navy bg-white shadow-brutal-sm text-sm text-navy/70"
    >
      Inga förslag väntar på granskning.
    </div>

    <ul
      v-else
      class="border border-navy bg-white shadow-brutal-sm divide-y divide-navy/15"
    >
      <li
        v-for="suggestion in suggestions"
        :key="suggestion.id"
        class="p-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between"
      >
        <div class="space-y-1 min-w-0">
          <div class="text-base font-semibold text-navy truncate">{{ suggestion.title }}</div>
          <div class="text-xs text-navy/60">
            Inskickat {{ formatDateTime(suggestion.created_at) }} ·
            <span class="font-mono">{{ suggestion.submitted_by_user_id }}</span>
          </div>
          <div class="text-xs text-navy/70">
            Yrken: {{ suggestion.profession_slugs.join(", ") }} · Kategorier: {{ suggestion.category_slugs.join(", ") }}
          </div>
        </div>

        <div class="flex items-center gap-3">
          <span class="px-2 py-1 border border-navy bg-canvas shadow-brutal-sm text-xs font-semibold uppercase tracking-wide text-navy/70">
            {{ statusLabel(suggestion.status) }}
          </span>
          <RouterLink
            :to="{ name: 'admin-suggestion-detail', params: { id: suggestion.id } }"
            class="text-sm underline text-burgundy hover:text-navy"
          >
            Öppna →
          </RouterLink>
        </div>
      </li>
    </ul>
  </div>
</template>
