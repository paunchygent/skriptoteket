<script setup lang="ts">
import { computed, onBeforeUnmount, ref, toRef, watch } from "vue";

import { apiFetch, apiGet, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";
import { useSandboxSettings } from "../../composables/editor/useSandboxSettings";
import { useToolInputs, type ToolInputFormValues } from "../../composables/tools/useToolInputs";
import type { SettingsFormValues } from "../../composables/tools/toolSettingsHelpers";
import ToolRunSettingsPanel from "../tool-run/ToolRunSettingsPanel.vue";
import SystemMessage from "../ui/SystemMessage.vue";
import SandboxInputPanel from "./SandboxInputPanel.vue";
import SandboxRunnerActions from "./SandboxRunnerActions.vue";

type SandboxRunResponse = components["schemas"]["SandboxRunResponse"];
type StartSandboxActionResponse = components["schemas"]["StartSandboxActionResponse"];
type EditorRunDetails = components["schemas"]["EditorRunDetails"];
type RunStatus = components["schemas"]["RunStatus"];
type JsonValue = components["schemas"]["JsonValue"];

type CreateDraftVersionRequest = components["schemas"]["CreateDraftVersionRequest"];
type ToolInputSchema = NonNullable<CreateDraftVersionRequest["input_schema"]>;
type ToolSettingsSchema = NonNullable<CreateDraftVersionRequest["settings_schema"]>;

const props = defineProps<{
  versionId: string;
  toolId: string;
  isReadOnly: boolean;
  entrypoint: string;
  sourceCode: string;
  usageInstructions: string;
  inputSchema: ToolInputSchema | null;
  inputSchemaError: string | null;
  settingsSchema: ToolSettingsSchema | null;
  settingsSchemaError: string | null;
}>();

const selectedFiles = ref<File[]>([]);
const toolInputs = useToolInputs({ schema: toRef(props, "inputSchema"), selectedFiles });

const inputValues = toolInputs.values;
const inputFields = toolInputs.nonFileFields;
const inputFieldErrors = toolInputs.fieldErrors;
const hasSchema = toolInputs.hasSchema;
const fileAccept = toolInputs.fileAccept;
const fileLabel = toolInputs.fileLabel;
const fileMultiple = toolInputs.fileMultiple;
const fileError = toolInputs.fileError;
const showFilePicker = toolInputs.showFilePicker;

const sandboxSettings = useSandboxSettings({
  versionId: toRef(props, "versionId"),
  settingsSchema: toRef(props, "settingsSchema"),
});

const settingsValues = sandboxSettings.values;
const settingsErrorMessage = sandboxSettings.errorMessage;
const isLoadingSettings = sandboxSettings.isLoading;
const isSavingSettings = sandboxSettings.isSaving;
const hasSettingsSchema = sandboxSettings.hasSchema;

const isSettingsOpen = ref(false);
const isSettingsSaveDisabled = computed(
  () => props.isReadOnly || Boolean(props.settingsSchemaError),
);

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

const snapshotId = ref<string | null>(null);
const lastSentInputsJson = ref<string>("{}");

const hasFiles = computed(() => selectedFiles.value.length > 0);
const inputsPreview = computed(() => lastSentInputsJson.value);
const hasResults = computed(() => runResult.value !== null || errorMessage.value !== null);

const canSubmitActions = computed(() => {
  return (
    stateRev.value !== null &&
    !isRunning.value &&
    !isSubmitting.value &&
    !props.isReadOnly
  );
});

const canRun = computed(() => {
  if (props.isReadOnly || isRunning.value) return false;
  if (props.inputSchemaError || props.settingsSchemaError) return false;
  if (hasSchema.value) {
    return toolInputs.isValid.value;
  }
  return hasFiles.value;
});

function updateInputValues(values: ToolInputFormValues): void {
  inputValues.value = values;
}

function updateSelectedFiles(files: File[]): void {
  selectedFiles.value = files;
}

function updateSettingsValues(values: SettingsFormValues): void {
  settingsValues.value = values;
}

function toggleSettings(): void {
  isSettingsOpen.value = !isSettingsOpen.value;
}

function clearResult(): void {
  runResult.value = null;
  errorMessage.value = null;
  snapshotId.value = null;
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
    if (result.snapshot_id) {
      snapshotId.value = result.snapshot_id;
    }

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
  if (!canRun.value) return;
  if (props.isReadOnly) {
    errorMessage.value = "Du saknar redigeringslåset. Testkörning är spärrad.";
    return;
  }

  const entrypoint = props.entrypoint.trim();
  if (!entrypoint) {
    errorMessage.value = "Entrypoint saknas. Ange en giltig entrypoint.";
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
  snapshotId.value = null;

  let apiInputs: Record<string, JsonValue> = {};
  if (hasSchema.value) {
    try {
      apiInputs = toolInputs.buildApiValues();
    } catch (error: unknown) {
      isRunning.value = false;
      if (error instanceof Error) {
        errorMessage.value = error.message;
      } else {
        errorMessage.value = "Ogiltiga indata. Kontrollera fälten.";
      }
      return;
    }
  }

  const usageInstructions = props.usageInstructions.trim();
  const snapshotPayload = {
    entrypoint,
    source_code: props.sourceCode,
    settings_schema: props.settingsSchema ?? null,
    input_schema: props.inputSchema ?? null,
    usage_instructions: usageInstructions ? usageInstructions : null,
  };

  const formData = new FormData();
  for (const file of selectedFiles.value) {
    formData.append("files", file);
  }
  formData.append("inputs", JSON.stringify(apiInputs));
  formData.append("snapshot", JSON.stringify(snapshotPayload));
  lastSentInputsJson.value = JSON.stringify(apiInputs, null, 2);

  try {
    const response = await apiFetch<SandboxRunResponse>(
      `/api/v1/editor/tool-versions/${encodeURIComponent(props.versionId)}/run-sandbox`,
      {
        method: "POST",
        body: formData,
      },
    );

    snapshotId.value = response.snapshot_id;

    // Capture state_rev if present (multi-step tools)
    if (response.state_rev !== null && response.state_rev !== undefined) {
      stateRev.value = response.state_rev;
    }

    runResult.value = {
      run_id: response.run_id,
      version_id: props.versionId,
      snapshot_id: response.snapshot_id,
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
  if (!snapshotId.value) {
    actionErrorMessage.value = "Ingen snapshot tillgänglig. Testkör igen.";
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
          snapshot_id: snapshotId.value,
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
      snapshot_id: snapshotId.value,
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

watch(hasSettingsSchema, (next) => {
  if (!next) {
    isSettingsOpen.value = false;
  }
});

watch(
  () => props.settingsSchemaError,
  (next) => {
    if (next) {
      isSettingsOpen.value = false;
    }
  },
);
</script>

<template>
  <div class="space-y-4">
    <SandboxInputPanel
      :id-base="`sandbox-${versionId}`"
      :has-schema="hasSchema"
      :input-fields="inputFields"
      :input-values="inputValues"
      :input-field-errors="inputFieldErrors"
      :input-schema-error="inputSchemaError"
      :inputs-preview="inputsPreview"
      :selected-files="selectedFiles"
      :show-file-picker="showFilePicker"
      :file-label="fileLabel"
      :file-accept="fileAccept"
      :file-multiple="fileMultiple"
      :file-error="fileError"
      :is-running="isRunning"
      :is-read-only="isReadOnly"
      :has-results="hasResults"
      :can-run="canRun"
      @update:input-values="updateInputValues"
      @update:selected-files="updateSelectedFiles"
      @run="runSandbox"
      @clear="clearResult"
    />

    <div
      v-if="hasSettingsSchema || settingsSchemaError"
      class="border border-navy bg-white shadow-brutal-sm"
    >
      <div class="flex items-center justify-between gap-3 px-3 py-2 border-b border-navy/20">
        <div>
          <h2 class="text-xs font-semibold uppercase tracking-wide text-navy/70">
            Inställningar
          </h2>
          <p class="text-xs text-navy/60">
            Sparas för din sandbox.
          </p>
        </div>

        <button
          type="button"
          class="btn-ghost px-3 py-2 text-xs font-semibold tracking-wide"
          :disabled="!hasSettingsSchema"
          @click="toggleSettings"
        >
          {{ isSettingsOpen ? "Dölj" : "Visa" }}
        </button>
      </div>

      <p
        v-if="settingsSchemaError"
        class="px-3 py-2 text-xs font-semibold text-burgundy"
      >
        {{ settingsSchemaError }}
      </p>

      <div
        v-if="isSettingsOpen && hasSettingsSchema && settingsSchema"
        class="px-3 py-4 border-t border-navy/20 bg-canvas/30"
      >
        <ToolRunSettingsPanel
          v-model:error-message="settingsErrorMessage"
          :id-base="`sandbox-${versionId}`"
          :schema="settingsSchema"
          :model-value="settingsValues"
          :is-loading="isLoadingSettings"
          :is-saving="isSavingSettings"
          :is-save-disabled="isSettingsSaveDisabled"
          @update:model-value="updateSettingsValues"
          @save="sandboxSettings.saveSettings"
        />
      </div>
    </div>

    <SystemMessage
      v-model="errorMessage"
      variant="error"
    />

    <SandboxRunnerActions
      v-model:action-error-message="actionErrorMessage"
      :run-result="runResult"
      :completed-steps="completedSteps"
      :selected-step-index="selectedStepIndex"
      :is-running="isRunning"
      :version-id="versionId"
      :can-submit-actions="canSubmitActions"
      @select-step="selectedStepIndex = $event"
      @submit-action="onSubmitAction"
    />
  </div>
</template>
