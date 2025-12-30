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

function formatDuration(startedAt: string, finishedAt: string | null): string | null {
  if (!finishedAt) return null;

  const start = new Date(startedAt);
  const end = new Date(finishedAt);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
    return null;
  }

  const diffMs = end.getTime() - start.getTime();
  const diffSec = Math.floor(diffMs / 1000);

  if (diffSec < 60) {
    return `${diffSec} sek`;
  }

  const min = Math.floor(diffSec / 60);
  const sec = diffSec % 60;
  return sec > 0 ? `${min} min ${sec} sek` : `${min} min`;
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
  <div class="page">
    <header class="page-header">
      <div>
        <h1 class="page-title">Mina körningar</h1>
        <p class="page-description">
          Se tidigare resultat, ladda ner filer och fortsätt med nästa steg.
        </p>
      </div>
    </header>

    <section class="panel">
      <div
        v-if="isLoading"
        class="panel-state"
      >
        Laddar körningar…
      </div>
      <div
        v-else-if="errorMessage"
        class="panel-state text-error"
      >
        {{ errorMessage }}
      </div>
      <div
        v-else-if="!hasRuns"
        class="panel-state"
      >
        Du har inga körningar än.
      </div>
      <div
        v-else
        class="table-wrapper"
      >
        <table class="panel-table">
          <thead>
            <tr>
              <th>Verktyg</th>
              <th>Status</th>
              <th class="hidden md:table-cell">Historik</th>
              <th class="hidden sm:table-cell">Input</th>
              <th>Artefakt</th>
              <th />
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="run in runs"
              :key="run.run_id"
            >
              <td>
                <div class="font-semibold text-navy">
                  {{ run.tool_title }}
                </div>
              </td>
              <td>
                <span
                  class="status-pill"
                  :class="statusClass(run.status)"
                >
                  {{ statusLabel(run.status) }}
                </span>
              </td>
              <td class="hidden md:table-cell">
                <div class="text-xs text-navy/70">
                  {{ formatDateTime(run.started_at) }}
                </div>
                <div
                  v-if="formatDuration(run.started_at, run.finished_at)"
                  class="text-xs text-navy/50"
                >
                  ({{ formatDuration(run.started_at, run.finished_at) }})
                </div>
              </td>
              <td class="hidden sm:table-cell">
                <template v-if="run.input_files.length === 0">
                  <span class="text-navy/40">—</span>
                </template>
                <template v-else-if="run.input_files.length === 1">
                  <span class="text-xs text-navy/70 truncate max-w-32 block">
                    {{ run.input_files[0].filename }}
                  </span>
                </template>
                <template v-else>
                  <span class="text-xs text-navy/70">
                    {{ run.input_files.length }} filer
                  </span>
                </template>
              </td>
              <td>
                <template v-if="run.output_files.length === 0">
                  <span class="text-navy/40">—</span>
                </template>
                <template v-else>
                  <div class="flex flex-col gap-0.5">
                    <a
                      v-for="file in run.output_files"
                      :key="file.artifact_id"
                      :href="file.download_url"
                      download
                      class="download-link"
                    >
                      ↓ {{ file.filename }}
                    </a>
                  </div>
                </template>
              </td>
              <td class="text-right whitespace-nowrap">
                <RouterLink
                  :to="{ name: 'my-runs-detail', params: { runId: run.run_id } }"
                  class="action-link"
                >
                  till körning →
                </RouterLink>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: var(--huleedu-space-6);
}

.page-header {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: var(--huleedu-space-4);
}

.panel {
  border: var(--huleedu-border-width) solid var(--huleedu-navy);
  background-color: white;
  box-shadow: var(--huleedu-shadow-brutal-sm);
}

.panel-state {
  padding: var(--huleedu-space-4);
  font-size: var(--huleedu-text-sm);
  color: var(--huleedu-navy-70);
}

.table-wrapper {
  overflow-x: auto;
}

.panel-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--huleedu-text-sm);
}

.panel-table th,
.panel-table td {
  padding: var(--huleedu-space-3) var(--huleedu-space-4);
  text-align: left;
  border-bottom: var(--huleedu-border-width) solid var(--huleedu-navy-10);
  vertical-align: top;
}

.panel-table th {
  text-transform: uppercase;
  letter-spacing: var(--huleedu-tracking-label);
  font-size: var(--huleedu-text-xs);
  color: var(--huleedu-navy-60);
}

.download-link {
  display: inline-block;
  font-size: var(--huleedu-text-xs);
  color: var(--huleedu-navy);
  text-decoration: underline;
  transition: color var(--huleedu-duration-default) var(--huleedu-ease-default);
}

.download-link:hover {
  color: var(--huleedu-burgundy);
}

.action-link {
  font-size: var(--huleedu-text-xs);
  color: var(--huleedu-navy);
  text-decoration: none;
  transition: color var(--huleedu-duration-default) var(--huleedu-ease-default);
}

.action-link:hover {
  color: var(--huleedu-burgundy);
}
</style>
