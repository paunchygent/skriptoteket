<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { apiGet, isApiError } from "../api/client";
import type { components } from "../api/openapi";

type ListMyRunsResponse = components["schemas"]["ListMyRunsResponse"];
type MyRunItem = components["schemas"]["MyRunItem"];
type RunStatus = components["schemas"]["RunStatus"];

const runs = ref<MyRunItem[]>([]);
const isLoading = ref(true);
const errorMessage = ref<string | null>(null);

function statusLabel(status: RunStatus): string {
  const labels: Record<RunStatus, string> = {
    running: "Pågår",
    succeeded: "Lyckades",
    failed: "Misslyckades",
    timed_out: "Tidsgräns",
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

const hasRuns = computed(() => runs.value.length > 0);

async function fetchRuns(): Promise<void> {
  isLoading.value = true;
  errorMessage.value = null;

  try {
    const response = await apiGet<ListMyRunsResponse>("/api/v1/my-runs");
    runs.value = response.runs;
  } catch (error: unknown) {
    if (isApiError(error)) {
      errorMessage.value = error.message;
    } else if (error instanceof Error) {
      errorMessage.value = error.message;
    } else {
      errorMessage.value = "Det gick inte att ladda körningar.";
    }
  } finally {
    isLoading.value = false;
  }
}

onMounted(() => {
  void fetchRuns();
});
</script>

<template>
  <div class="max-w-3xl space-y-6">
    <div class="space-y-2">
      <h1 class="page-title">Mina körningar</h1>
      <p class="page-description">Se tidigare resultat, ladda ner filer och fortsätt med nästa steg.</p>
    </div>

    <div
      v-if="isLoading"
      class="p-4 border border-navy bg-white shadow-brutal-sm text-navy/70 text-sm"
    >
      Laddar...
    </div>

    <div
      v-else-if="errorMessage"
      class="p-4 border border-error bg-white shadow-brutal-sm text-error text-sm"
    >
      {{ errorMessage }}
    </div>

    <div
      v-else-if="!hasRuns"
      class="p-4 border border-navy bg-white shadow-brutal-sm text-navy/70 text-sm"
    >
      Du har inga körningar än.
    </div>

    <ul
      v-else
      class="border border-navy bg-white shadow-brutal-sm divide-y divide-navy/20"
    >
      <li
        v-for="run in runs"
        :key="run.run_id"
        class="p-4 flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3"
      >
        <div class="min-w-0 space-y-1">
          <div class="font-semibold text-navy break-words">
            {{ run.tool_title }}
          </div>
          <div class="text-xs text-navy/60">
            <span class="font-mono">{{ run.run_id }}</span>
          </div>
          <div class="text-sm text-navy/70">
            Startade: {{ formatDateTime(run.started_at) }}
          </div>
        </div>

        <div class="shrink-0 flex flex-col sm:items-end gap-2">
          <span class="px-2 py-1 border border-navy bg-canvas shadow-brutal-sm text-xs font-semibold uppercase tracking-wide text-navy/70">
            {{ statusLabel(run.status) }}
          </span>
          <RouterLink
            :to="{ name: 'my-runs-detail', params: { runId: run.run_id } }"
            class="text-sm underline text-burgundy hover:text-navy"
          >
            Öppna →
          </RouterLink>
        </div>
      </li>
    </ul>
  </div>
</template>
