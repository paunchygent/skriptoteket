<script setup lang="ts">
import { onMounted, ref } from "vue";
import { RouterLink } from "vue-router";

import { apiGet, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";
import ToolListRow from "../../components/tools/ToolListRow.vue";
import { SystemMessage, UiDenseStatusPill } from "../../components/ui";

type ListSuggestionsResponse = components["schemas"]["ListSuggestionsResponse"];
type SuggestionSummary = components["schemas"]["SuggestionSummary"];
type SuggestionStatus = components["schemas"]["SuggestionStatus"];

const suggestions = ref<SuggestionSummary[]>([]);
const isLoading = ref(true);
const errorMessage = ref<string | null>(null);

function statusLabel(status: SuggestionStatus): string {
  const labels: Record<SuggestionStatus, string> = {
    pending_review: "Väntar",
    accepted: "Godkänd",
    denied: "Avslagen",
  };
  return labels[status];
}

function statusTone(status: SuggestionStatus): "warning" | "success" | "neutral" {
  if (status === "pending_review") return "warning";
  if (status === "accepted") return "success";
  return "neutral";
}

function actionClass(status: SuggestionStatus): string {
  if (status === "pending_review") {
    return "btn-cta w-full";
  }
  return "btn-ghost w-full";
}

function actionLabel(status: SuggestionStatus): string {
  return status === "pending_review" ? "Granska" : "Visa";
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
      <h1 class="page-title">Förslag (granskning)</h1>
      <p class="page-description">Lista över inkomna förslag som väntar på beslut.</p>
    </div>

    <div
      v-if="isLoading"
      class="p-4 rounded-[var(--huleedu-panel-radius)] border border-[var(--huleedu-panel-border)] bg-panel text-sm text-navy/70"
    >
      Laddar...
    </div>

    <SystemMessage
      v-else-if="errorMessage"
      :model-value="errorMessage"
      tone="failure"
    />

    <div
      v-else-if="suggestions.length === 0"
      class="p-4 rounded-[var(--huleedu-panel-radius)] border border-[var(--huleedu-panel-border)] bg-panel text-sm text-navy/70"
    >
      Inga förslag väntar på granskning.
    </div>

    <ul
      v-else
      class="rounded-[var(--huleedu-panel-radius)] border border-[var(--huleedu-panel-border)] bg-panel divide-y divide-[var(--huleedu-surface-divider)]"
    >
      <ToolListRow
        v-for="suggestion in suggestions"
        :key="suggestion.id"
        grid-class="sm:grid-cols-[minmax(0,1fr)_8rem_7rem]"
        status-class="justify-self-start"
        actions-class="justify-self-start sm:justify-self-stretch"
      >
        <template #main>
          <div class="text-base font-semibold text-navy truncate">
            {{ suggestion.title }}
          </div>
          <div class="text-xs text-navy/60">
            Inskickat {{ formatDateTime(suggestion.created_at) }}
          </div>
        </template>

        <template #status>
          <UiDenseStatusPill
            :label="statusLabel(suggestion.status)"
            :tone="statusTone(suggestion.status)"
          />
        </template>

        <template #actions>
          <RouterLink
            :to="{ name: 'admin-suggestion-detail', params: { id: suggestion.id } }"
            :class="actionClass(suggestion.status)"
          >
            {{ actionLabel(suggestion.status) }}
          </RouterLink>
        </template>
      </ToolListRow>
    </ul>
  </div>
</template>
