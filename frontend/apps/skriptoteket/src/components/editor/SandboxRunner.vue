<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from "vue";

import { apiFetch, apiGet, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";
import { UiOutputRenderer } from "../ui-outputs";
import ToolRunActions from "../tool-run/ToolRunActions.vue";
import ToolRunArtifacts from "../tool-run/ToolRunArtifacts.vue";
import SystemMessage from "../ui/SystemMessage.vue";

type SandboxRunResponse = components["schemas"]["SandboxRunResponse"];
type StartSandboxActionResponse = components["schemas"]["StartSandboxActionResponse"];
type EditorRunDetails = components["schemas"]["EditorRunDetails"];
type RunStatus = components["schemas"]["RunStatus"];
type UiOutput = NonNullable<components["schemas"]["UiPayloadV2"]["outputs"]>[number];
type UiFormAction = NonNullable<components["schemas"]["UiPayloadV2"]["next_actions"]>[number];
type UiPayloadV2 = components["schemas"]["UiPayloadV2"];
type JsonValue = components["schemas"]["JsonValue"];

const props = defineProps<{
  versionId: string;
  toolId: string;
  isReadOnly: boolean;
}>();

const selectedFiles = ref<File[]>([]);
const isRunning = ref(false);
const runResult = ref<EditorRunDetails | null>(null);
const errorMessage = ref<string | null>(null);
const pollingIntervalId = ref<number | null>(null);

// Multi-step action state (ADR-0038)
const stateRev = ref<number | null>(null);
const isSubmitting = ref(false);
const actionErrorMessage = ref<string | null>(null);
const completedSteps = ref<EditorRunDetails[]>([]);
const selectedStepIndex = ref<number | null>(null);

const inputValues = ref<Record<string, JsonValue>>({});
const lastSentInputsJson = ref<string>("{}");

const hasFiles = computed(() => selectedFiles.value.length > 0);
const inputsPreview = computed(() => lastSentInputsJson.value);

// Displayed run: current or selected past step
const displayedRun = computed<EditorRunDetails | null>(() => {
  if (selectedStepIndex.value !== null) {
    return completedSteps.value[selectedStepIndex.value] ?? null;
  }
  return runResult.value;
});

const outputs = computed<UiOutput[]>(() => {
  const payload = displayedRun.value?.ui_payload as UiPayloadV2 | null;
  return payload?.outputs ?? [];
});
const artifacts = computed(() => displayedRun.value?.artifacts ?? []);
const hasResults = computed(() => runResult.value !== null || errorMessage.value !== null);

// Multi-step action computed properties
const nextActions = computed<UiFormAction[]>(() => {
  const payload = runResult.value?.ui_payload as UiPayloadV2 | null;
  return payload?.next_actions ?? [];
});
const canSubmitActions = computed(() => {
  return (
    stateRev.value !== null &&
    !isRunning.value &&
    !isSubmitting.value &&
    !props.isReadOnly
  );
});

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
  // Clear multi-step state
  stateRev.value = null;
  actionErrorMessage.value = null;
  completedSteps.value = [];
  selectedStepIndex.value = null;
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
  if (isRunning.value) return;
  if (props.isReadOnly) {
    errorMessage.value = "Du saknar redigeringslåset. Testkörning är spärrad.";
    return;
  }

  isRunning.value = true;
  errorMessage.value = null;
  runResult.value = null;
  stopPolling();

  // Reset multi-step state for fresh run
  stateRev.value = null;
  actionErrorMessage.value = null;
  completedSteps.value = [];
  selectedStepIndex.value = null;

  const formData = new FormData();
  for (const file of selectedFiles.value) {
    formData.append("files", file);
  }
  formData.append("inputs", JSON.stringify(inputValues.value));
  lastSentInputsJson.value = JSON.stringify(inputValues.value, null, 2);

  try {
    const response = await apiFetch<SandboxRunResponse>(
      `/api/v1/editor/tool-versions/${encodeURIComponent(props.versionId)}/run-sandbox`,
      {
        method: "POST",
        body: formData,
      },
    );

    // Capture state_rev if present (multi-step tools)
    if (response.state_rev !== null && response.state_rev !== undefined) {
      stateRev.value = response.state_rev;
    }

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

async function onSubmitAction(payload: {
  actionId: string;
  input: Record<string, JsonValue>;
}): Promise<void> {
  if (!canSubmitActions.value || !runResult.value) return;
  if (props.isReadOnly) {
    actionErrorMessage.value = "Du saknar redigeringslåset. Åtgärden kan inte köras.";
    return;
  }

  isSubmitting.value = true;
  actionErrorMessage.value = null;
  stopPolling();

  // Save current run to history before starting new action
  completedSteps.value.push(runResult.value);
  selectedStepIndex.value = null;

  try {
    const response = await apiFetch<StartSandboxActionResponse>(
      `/api/v1/editor/tool-versions/${encodeURIComponent(props.versionId)}/start-action`,
      {
        method: "POST",
        body: JSON.stringify({
          action_id: payload.actionId,
          input: payload.input,
          expected_state_rev: stateRev.value,
        }),
        headers: { "Content-Type": "application/json" },
      },
    );

    // Update state_rev from response
    stateRev.value = response.state_rev;

    // Create placeholder and start polling
    runResult.value = {
      run_id: response.run_id,
      version_id: props.versionId,
      status: "running",
      started_at: new Date().toISOString(),
      finished_at: null,
      error_summary: null,
      ui_payload: null,
      artifacts: [],
    };

    isRunning.value = true;
    pollingIntervalId.value = window.setInterval(() => {
      void pollRunStatus(response.run_id);
    }, 1500);
  } catch (error: unknown) {
    // Revert step history on error
    completedSteps.value.pop();

    if (isApiError(error) && error.status === 409) {
      actionErrorMessage.value = "Din session har ändrats. Uppdatera och försök igen.";
    } else if (error instanceof Error) {
      actionErrorMessage.value = error.message;
    } else {
      actionErrorMessage.value = "Det gick inte att köra åtgärden just nu.";
    }
  } finally {
    isSubmitting.value = false;
  }
}

onBeforeUnmount(() => {
  stopPolling();
});
</script>

<template>
  <div class="space-y-4">
    <div class="space-y-2">
      <!-- Label row -->
      <label class="block text-xs font-semibold uppercase tracking-wide text-navy/70">
        Testfiler
      </label>

      <!-- Input + buttons row (same height via items-stretch) -->
      <div class="flex flex-col gap-3 sm:flex-row sm:items-stretch">
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-3 w-full border border-navy bg-white px-3 py-2 shadow-brutal-sm overflow-hidden h-full">
            <label
              class="btn-cta shrink-0 px-3 py-1 text-xs font-semibold tracking-wide"
              :class="{ 'opacity-60 pointer-events-none': isReadOnly }"
            >
              Välj filer
              <input
                type="file"
                multiple
                class="sr-only"
                :disabled="isReadOnly"
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
          :disabled="isRunning || isReadOnly"
          class="btn-cta min-w-[120px]"
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
          class="btn-ghost"
          @click="clearResult"
        >
          Rensa
        </button>
      </div>
    </div>

    <details class="border border-navy bg-white shadow-brutal-sm">
      <summary class="px-3 py-2 cursor-pointer text-xs font-semibold uppercase tracking-wide text-navy/70">
        Indata (JSON)
      </summary>
      <div class="px-3 py-2 border-t border-navy/20 bg-canvas/30 space-y-2">
        <p class="text-xs text-navy/60">
          Skickas som <span class="font-mono">SKRIPTOTEKET_INPUTS</span>.
        </p>
        <pre class="whitespace-pre-wrap font-mono text-xs text-navy">{{ inputsPreview }}</pre>
      </div>
    </details>

    <SystemMessage
      v-model="errorMessage"
      variant="error"
    />

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
      <!-- Step history indicator -->
      <div
        v-if="completedSteps.length > 0"
        class="flex flex-wrap gap-2"
      >
        <button
          v-for="(step, index) in completedSteps"
          :key="step.run_id"
          type="button"
          class="btn-ghost btn-sm text-xs"
          :class="{ 'ring-2 ring-navy': selectedStepIndex === index }"
          @click="selectedStepIndex = index"
        >
          Steg {{ index + 1 }}
        </button>
        <button
          type="button"
          class="btn-ghost btn-sm text-xs"
          :class="{ 'ring-2 ring-navy': selectedStepIndex === null }"
          @click="selectedStepIndex = null"
        >
          Aktuellt
        </button>
      </div>

      <!-- Status row (uses displayedRun for viewing past steps) -->
      <div
        v-if="displayedRun"
        class="flex items-center gap-2 text-sm"
      >
        <span
          class="px-2 py-1 border font-semibold uppercase tracking-wide text-xs"
          :class="{
            'border-success bg-success/10 text-success': displayedRun.status === 'succeeded',
            'border-burgundy bg-burgundy/10 text-burgundy': displayedRun.status === 'failed',
            'border-warning bg-warning/10 text-warning': displayedRun.status === 'timed_out',
          }"
        >
          {{ statusLabel(displayedRun.status) }}
        </span>
        <span class="font-mono text-xs text-navy/50">
          {{ displayedRun.run_id.slice(0, 8) }}
        </span>
      </div>

      <!-- Error summary -->
      <div
        v-if="displayedRun?.error_summary"
        class="text-sm text-burgundy"
      >
        <p class="font-semibold">Ett fel uppstod</p>
        <pre class="mt-1 whitespace-pre-wrap font-mono text-xs">{{ displayedRun.error_summary }}</pre>
      </div>

      <!-- Outputs -->
      <div
        v-if="outputs.length > 0"
        class="space-y-3"
      >
        <UiOutputRenderer
          v-for="(output, index) in outputs"
          :key="index"
          :output="output"
        />
      </div>

      <!-- Artifacts -->
      <ToolRunArtifacts :artifacts="artifacts" />

      <!-- Action error message -->
      <SystemMessage
        v-model="actionErrorMessage"
        variant="error"
      />

      <!-- Next Actions (multi-step tools) - only show for current run -->
      <ToolRunActions
        v-if="nextActions.length > 0 && selectedStepIndex === null"
        :actions="nextActions"
        :id-base="`sandbox-${versionId}-${runResult?.run_id ?? 'pending'}`"
        :disabled="!canSubmitActions"
        @submit="onSubmitAction"
      />
    </template>
  </div>
</template>
