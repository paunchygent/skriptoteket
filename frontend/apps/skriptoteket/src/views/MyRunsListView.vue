<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { apiGet, isApiError } from "../api/client";
import type { components } from "../api/openapi";
import { IconArrow } from "../components/icons";

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

function statusClass(status: RunStatus): string {
  switch (status) {
    case "succeeded":
      return "bg-canvas text-navy/70 border border-navy/30";
    case "failed":
    case "timed_out":
      return "bg-error/10 text-error border border-error/30";
    case "running":
      return "bg-burgundy/10 text-burgundy border border-burgundy/40";
    default:
      return "bg-canvas text-navy/70 border border-navy/30";
  }
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
      >
        <RouterLink
          :to="{ name: 'my-runs-detail', params: { runId: run.run_id } }"
          class="run-row"
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
            <span
              class="status-pill"
              :class="statusClass(run.status)"
            >
              {{ statusLabel(run.status) }}
            </span>
            <span class="run-link">
              Öppna
              <IconArrow
                :size="14"
                class="run-arrow"
              />
            </span>
          </div>
        </RouterLink>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.run-row {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 1rem;
  text-decoration: none;
  transition: background-color var(--huleedu-duration-default) var(--huleedu-ease-default);
}

@media (min-width: 640px) {
  .run-row {
    flex-direction: row;
    align-items: flex-start;
    justify-content: space-between;
  }
}

.run-row:hover {
  background-color: var(--huleedu-navy-02);
}

.run-link {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  font-size: var(--huleedu-text-sm);
  color: var(--huleedu-navy);
  transition: color var(--huleedu-duration-default) var(--huleedu-ease-default);
}

.run-row:hover .run-link {
  color: var(--huleedu-burgundy);
}

.run-arrow {
  color: var(--huleedu-navy);
  flex-shrink: 0;
  transition: transform var(--huleedu-duration-default) var(--huleedu-ease-default),
              color var(--huleedu-duration-default) var(--huleedu-ease-default);
}

.run-row:hover .run-arrow {
  transform: translateX(2px);
  color: var(--huleedu-burgundy);
}

</style>
