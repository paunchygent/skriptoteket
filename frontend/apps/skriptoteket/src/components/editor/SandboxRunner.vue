<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from "vue";

import { apiFetch, apiGet, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";
import ToolRunArtifacts from "../tool-run/ToolRunArtifacts.vue";
import ToolRunOutputs from "../tool-run/ToolRunOutputs.vue";

type SandboxRunResponse = components["schemas"]["SandboxRunResponse"];
type EditorRunDetails = components["schemas"]["EditorRunDetails"];
type RunStatus = components["schemas"]["RunStatus"];
type UiOutput = NonNullable<components["schemas"]["UiPayloadV2"]["outputs"]>[number];
type UiPayloadV2 = components["schemas"]["UiPayloadV2"];

const props = defineProps<{
  versionId: string;
  toolId: string;
}>();

const selectedFiles = ref<File[]>([]);
const isRunning = ref(false);
const runResult = ref<EditorRunDetails | null>(null);
const errorMessage = ref<string | null>(null);
const pollingIntervalId = ref<number | null>(null);

const hasFiles = computed(() => selectedFiles.value.length > 0);

const outputs = computed<UiOutput[]>(() => {
  const payload = runResult.value?.ui_payload as UiPayloadV2 | null;
  return payload?.outputs ?? [];
});
const artifacts = computed(() => runResult.value?.artifacts ?? []);
const hasResults = computed(() => runResult.value !== null || errorMessage.value !== null);

function selectFiles(event: Event): void {
  const target = event.target as HTMLInputElement;
  if (target.files) {
    selectedFiles.value = Array.from(target.files);
  }
}

function statusLabel(status: RunStatus): string {
  const labels: Record<RunStatus, string> = {
    running: "Kör...",
    succeeded: "Lyckades",
    failed: "Misslyckades",
    timed_out: "Tidsgräns",
  };
  return labels[status];
}

function clearResult(): void {
  runResult.value = null;
  errorMessage.value = null;
}

function stopPolling(): void {
  if (pollingIntervalId.value !== null) {
    window.clearInterval(pollingIntervalId.value);
    pollingIntervalId.value = null;
  }
}

function isTerminalStatus(status: RunStatus): boolean {
  return status !== "running";
}

async function pollRunStatus(runId: string): Promise<void> {
  try {
    const result = await apiGet<EditorRunDetails>(
      `/api/v1/editor/tool-runs/${encodeURIComponent(runId)}`,
    );
    runResult.value = result;

    if (isTerminalStatus(result.status)) {
      stopPolling();
      isRunning.value = false;
    }
  } catch (error: unknown) {
    stopPolling();
    isRunning.value = false;
    if (isApiError(error)) {
      errorMessage.value = error.message;
    } else if (error instanceof Error) {
      errorMessage.value = error.message;
    } else {
      errorMessage.value = "Det gick inte att hämta körningsresultatet.";
    }
  }
}

async function runSandbox(): Promise<void> {
  if (!hasFiles.value || isRunning.value) return;

  isRunning.value = true;
  errorMessage.value = null;
  runResult.value = null;
  stopPolling();

  const formData = new FormData();
  for (const file of selectedFiles.value) {
    formData.append("files", file);
  }

  try {
    const response = await apiFetch<SandboxRunResponse>(
      `/api/v1/editor/tool-versions/${encodeURIComponent(props.versionId)}/run-sandbox`,
      {
        method: "POST",
        body: formData,
      },
    );

    runResult.value = {
      run_id: response.run_id,
      version_id: props.versionId,
      status: response.status,
      started_at: response.started_at,
      finished_at: null,
      error_summary: null,
      ui_payload: null,
      artifacts: [],
    };

    if (isTerminalStatus(response.status)) {
      await pollRunStatus(response.run_id);
    } else {
      pollingIntervalId.value = window.setInterval(() => {
        void pollRunStatus(response.run_id);
      }, 1500);
    }
  } catch (error: unknown) {
    isRunning.value = false;
    if (isApiError(error)) {
      errorMessage.value = error.message;
    } else if (error instanceof Error) {
      errorMessage.value = error.message;
    } else {
      errorMessage.value = "Det gick inte att starta testkörningen.";
    }
  }
}

onBeforeUnmount(() => {
  stopPolling();
});
</script>

<template>
  <div class="space-y-4">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-end">
      <div class="flex-1 space-y-1 min-w-0">
        <label class="text-xs font-semibold uppercase tracking-wide text-navy/70">
          Testfiler
        </label>
        <div class="flex items-center gap-3 w-full border border-navy bg-white px-3 py-2 shadow-brutal-sm overflow-hidden">
          <label
            class="shrink-0 px-3 py-1 text-xs font-semibold uppercase tracking-wide bg-burgundy text-canvas border border-navy cursor-pointer btn-secondary-hover transition-colors active:translate-x-0.5 active:translate-y-0.5"
          >
            Välj filer
            <input
              type="file"
              multiple
              class="sr-only"
              @change="selectFiles"
            >
          </label>
          <span class="text-sm text-navy/60 truncate">
            {{ hasFiles ? `${selectedFiles.length} fil(er) valda` : 'Inga filer valda' }}
          </span>
        </div>
      </div>

      <button
        type="button"
        :disabled="!hasFiles || isRunning"
        class="min-w-[120px] px-4 py-2 text-xs font-bold uppercase tracking-widest bg-burgundy text-canvas border border-navy shadow-brutal-sm btn-secondary-hover transition-colors active:translate-x-1 active:translate-y-1 active:shadow-none disabled:opacity-50 disabled:cursor-not-allowed"
        @click="runSandbox"
      >
        <span
          v-if="isRunning"
          class="inline-block w-3 h-3 border-2 border-canvas/30 border-t-canvas rounded-full animate-spin"
        />
        <span v-else>Testkör kod</span>
      </button>

      <button
        v-if="hasResults"
        type="button"
        class="px-4 py-2 text-xs font-bold uppercase tracking-widest bg-white text-navy border border-navy shadow-brutal-sm hover:bg-canvas btn-secondary-hover transition-colors active:translate-x-1 active:translate-y-1 active:shadow-none"
        @click="clearResult"
      >
        Rensa
      </button>
    </div>

    <!-- Error message -->
    <div
      v-if="errorMessage"
      class="p-3 border border-burgundy bg-white text-sm text-burgundy"
    >
      {{ errorMessage }}
    </div>

    <!-- Running state -->
    <div
      v-if="isRunning && runResult?.status === 'running'"
      class="flex items-center gap-2 text-sm text-navy/70"
    >
      <span class="inline-block w-4 h-4 border-2 border-navy/20 border-t-navy rounded-full animate-spin" />
      <span>Kör skriptet...</span>
    </div>

    <!-- Results -->
    <template v-if="runResult && runResult.status !== 'running'">
      <!-- Status row -->
      <div class="flex items-center gap-2 text-sm">
        <span
          class="px-2 py-1 border font-semibold uppercase tracking-wide text-xs"
          :class="{
            'border-success bg-success/10 text-success': runResult.status === 'succeeded',
            'border-burgundy bg-burgundy/10 text-burgundy': runResult.status === 'failed',
            'border-warning bg-warning/10 text-warning': runResult.status === 'timed_out',
          }"
        >
          {{ statusLabel(runResult.status) }}
        </span>
        <span class="font-mono text-xs text-navy/50">
          {{ runResult.run_id.slice(0, 8) }}
        </span>
      </div>

      <!-- Error summary -->
      <div
        v-if="runResult.error_summary"
        class="text-sm text-burgundy"
      >
        <p class="font-semibold">Ett fel uppstod</p>
        <pre class="mt-1 whitespace-pre-wrap font-mono text-xs">{{ runResult.error_summary }}</pre>
      </div>

      <!-- Outputs -->
      <ToolRunOutputs :outputs="outputs" />

      <!-- Artifacts -->
      <ToolRunArtifacts :artifacts="artifacts" />
    </template>
  </div>
</template>
