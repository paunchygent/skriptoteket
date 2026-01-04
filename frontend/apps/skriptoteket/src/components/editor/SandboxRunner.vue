<script setup lang="ts">
import { computed, ref, toRef } from "vue";

import type { components } from "../../api/openapi";
import { useEditorSandboxActions } from "../../composables/editor/useEditorSandboxActions";
import { useEditorSandboxRunExecution } from "../../composables/editor/useEditorSandboxRunExecution";
import { useEditorSandboxSessionFiles } from "../../composables/editor/useEditorSandboxSessionFiles";
import { useSandboxSettings } from "../../composables/editor/useSandboxSettings";
import { useToolInputs, type ToolInputFormValues } from "../../composables/tools/useToolInputs";
import SessionFilesPanel from "../tool-run/SessionFilesPanel.vue";
import SystemMessage from "../ui/SystemMessage.vue";
import SandboxInputPanel from "./SandboxInputPanel.vue";
import SandboxSettingsCard from "./SandboxSettingsCard.vue";
import SandboxRunnerActions from "./SandboxRunnerActions.vue";

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
  inputSchema: ToolInputSchema;
  inputSchemaError: string | null;
  settingsSchema: ToolSettingsSchema | null;
  settingsSchemaError: string | null;
  hasBlockingSchemaIssues: boolean;
  schemaValidationError: string | null;
  validateSchemasNow: () => Promise<boolean>;
}>();

const selectedFiles = ref<File[]>([]);
const toolInputs = useToolInputs({ schema: toRef(props, "inputSchema"), selectedFiles });

const inputValues = toolInputs.values;
const inputFields = toolInputs.nonFileFields;
const inputFieldErrors = toolInputs.fieldErrors;
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

const isRunning = ref(false);
const isSubmitting = ref(false);

const {
  sessionFiles,
  sessionFilesMode,
  sessionFilesSnapshotId,
  effectiveSessionFilesMode,
  effectiveFileError,
  canReuseSessionFiles,
  canClearSessionFiles,
  helperText: sessionFilesHelperText,
  fetchSessionFiles,
} = useEditorSandboxSessionFiles({
  versionId: toRef(props, "versionId"),
  isReadOnly: toRef(props, "isReadOnly"),
  isRunning,
  isSubmitting,
  selectedFiles,
  fileError,
  fileField: toolInputs.fileField,
});

const runExec = useEditorSandboxRunExecution({
  versionId: toRef(props, "versionId"),
  isReadOnly: toRef(props, "isReadOnly"),
  isRunning,
  entrypoint: toRef(props, "entrypoint"),
  sourceCode: toRef(props, "sourceCode"),
  usageInstructions: toRef(props, "usageInstructions"),
  settingsSchema: toRef(props, "settingsSchema"),
  inputSchema: toRef(props, "inputSchema"),
  inputSchemaError: toRef(props, "inputSchemaError"),
  settingsSchemaError: toRef(props, "settingsSchemaError"),
  hasBlockingSchemaIssues: toRef(props, "hasBlockingSchemaIssues"),
  schemaValidationError: toRef(props, "schemaValidationError"),
  validateSchemasNow: props.validateSchemasNow,
  buildApiInputs: () => toolInputs.buildApiValues(),
  selectedFiles,
  effectiveSessionFilesMode,
  sessionFilesSnapshotId,
  sessionFilesMode,
  fetchSessionFiles,
});

const actions = useEditorSandboxActions({
  versionId: toRef(props, "versionId"),
  isReadOnly: toRef(props, "isReadOnly"),
  runResult: runExec.runResult,
  snapshotId: runExec.snapshotId,
  isRunning,
  isSubmitting,
  stateRev: runExec.stateRev,
  startPolling: runExec.startPolling,
  stopPolling: runExec.stopPolling,
});

const runResult = runExec.runResult;
const errorMessage = runExec.errorMessage;
const inputsPreview = computed(() => runExec.lastSentInputsJson.value);
const hasResults = computed(() => runResult.value !== null || errorMessage.value !== null);

const actionErrorMessage = actions.actionErrorMessage;
const completedSteps = actions.completedSteps;
const selectedStepIndex = actions.selectedStepIndex;
const canSubmitActions = actions.canSubmitActions;

const inputsValid = computed(() => {
  return (
    effectiveFileError.value === null &&
    Object.keys(inputFieldErrors.value).length === 0
  );
});

const canRun = computed(() => {
  if (props.isReadOnly || isRunning.value) return false;
  if (props.inputSchemaError || props.settingsSchemaError) return false;
  if (props.hasBlockingSchemaIssues) return false;
  return inputsValid.value;
});

function updateInputValues(values: ToolInputFormValues): void {
  inputValues.value = values;
}

function updateSelectedFiles(files: File[]): void {
  selectedFiles.value = files;
}

async function runSandbox(): Promise<void> {
  actions.resetActions();
  await runExec.runSandbox();
}

function clearResult(): void {
  runExec.clearResult();
  actions.resetActions();
}

const onSubmitAction = actions.onSubmitAction;

</script>

<template>
  <div class="space-y-4">
    <SandboxInputPanel
      :id-base="`sandbox-${versionId}`"
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
      :file-error="effectiveFileError"
      :is-running="isRunning"
      :is-read-only="isReadOnly"
      :has-results="hasResults"
      :can-run="canRun"
      @update:input-values="updateInputValues"
      @update:selected-files="updateSelectedFiles"
      @run="runSandbox"
      @clear="clearResult"
    />

    <SessionFilesPanel
      v-model:mode="sessionFilesMode"
      :files="sessionFiles"
      :can-reuse="canReuseSessionFiles"
      :can-clear="canClearSessionFiles"
      :helper-text="sessionFilesHelperText"
    />

    <SandboxSettingsCard
      :version-id="versionId"
      :is-read-only="isReadOnly"
      :has-settings-schema="hasSettingsSchema"
      :settings-schema="settingsSchema"
      :settings-schema-error="settingsSchemaError"
      :settings-values="settingsValues"
      :settings-error-message="settingsErrorMessage"
      :is-loading-settings="isLoadingSettings"
      :is-saving-settings="isSavingSettings"
      :save-settings="sandboxSettings.saveSettings"
      @update:settings-values="settingsValues = $event"
      @update:settings-error-message="settingsErrorMessage = $event"
    />

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
