<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from "vue";

import { apiFetch, apiGet, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";
import { RunResultPanel } from "../run-results";

type SandboxRunResponse = components["schemas"]["SandboxRunResponse"];
type EditorRunDetails = components["schemas"]["EditorRunDetails"];
type RunStatus = components["schemas"]["RunStatus"];

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

function selectFiles(event: Event): void {
  const target = event.target as HTMLInputElement;
  if (target.files) {
    selectedFiles.value = Array.from(target.files);
  }
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
      <div class="flex-1 space-y-1">
        <label class="text-xs font-semibold uppercase tracking-wide text-navy/70">
          Testfiler
        </label>
        <input
          type="file"
          multiple
          class="w-full border border-navy bg-white px-3 py-2 text-sm text-navy shadow-brutal-sm file:mr-3 file:border-0 file:bg-burgundy file:px-3 file:py-1 file:text-xs file:font-semibold file:uppercase file:text-canvas"
          @change="selectFiles"
        >
      </div>

      <button
        type="button"
        :disabled="!hasFiles || isRunning"
        class="px-4 py-2 text-xs font-bold uppercase tracking-widest bg-burgundy text-canvas border border-navy shadow-brutal-sm hover:bg-navy transition-colors active:translate-x-1 active:translate-y-1 active:shadow-none disabled:opacity-50 disabled:cursor-not-allowed"
        @click="runSandbox"
      >
        {{ isRunning ? "Kör..." : "Kör i sandbox" }}
      </button>

      <button
        v-if="runResult || errorMessage"
        type="button"
        class="px-4 py-2 text-xs font-bold uppercase tracking-widest bg-canvas text-navy border border-navy shadow-brutal-sm hover:bg-white transition-colors active:translate-x-1 active:translate-y-1 active:shadow-none"
        @click="clearResult"
      >
        Rensa
      </button>
    </div>

    <p
      v-if="hasFiles && !isRunning && !runResult"
      class="text-xs text-navy/60"
    >
      {{ selectedFiles.length }} fil(er) valda
    </p>

    <div
      v-if="errorMessage"
      class="p-4 border border-burgundy bg-white shadow-brutal-sm text-sm text-burgundy"
    >
      {{ errorMessage }}
    </div>

    <div
      v-if="isRunning && runResult?.status === 'running'"
      class="p-4 border border-navy bg-white shadow-brutal-sm text-sm text-navy/70"
    >
      Kör skriptet...
    </div>

    <RunResultPanel
      v-if="runResult && runResult.status !== 'running'"
      :run="runResult"
      id-base="sandbox-run"
      :is-submitting-action="false"
      :can-submit-actions="false"
      :action-error-message="null"
    />
  </div>
</template>
