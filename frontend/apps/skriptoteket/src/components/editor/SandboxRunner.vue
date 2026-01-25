<script setup lang="ts">
import { computed, ref, toRef, watch } from "vue";

import type { components } from "../../api/openapi";
import { useEditorSandboxActions } from "../../composables/editor/useEditorSandboxActions";
import { useEditorSandboxRunExecution } from "../../composables/editor/useEditorSandboxRunExecution";
import { useEditorSandboxSessionFiles } from "../../composables/editor/useEditorSandboxSessionFiles";
import { useSandboxFileRefs } from "../../composables/editor/useSandboxFileRefs";
import { useSandboxSettings } from "../../composables/editor/useSandboxSettings";
import { useToolInputs, type ToolInputFormValues } from "../../composables/tools/useToolInputs";
import type { FileSelectionMode } from "../../composables/tools/useToolInputs";
import { getFileRefSource } from "../../composables/tools/fileRefHelpers";
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

const toolInputs = useToolInputs({ schema: toRef(props, "inputSchema") });

const inputValues = toolInputs.values;
const inputFields = toolInputs.nonFileFields;
const inputFieldErrors = toolInputs.fieldErrors;
const fileFields = toolInputs.fileFields;
const fileSelections = toolInputs.fileSelections;
const fileAcceptByField = toolInputs.fileAcceptByField;
const fileErrors = toolInputs.fileErrors;

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
  effectiveFileErrors,
  canReuseSessionFiles,
  canClearSessionFiles,
  helperText: sessionFilesHelperText,
  fetchSessionFiles,
  deleteSessionFiles,
} = useEditorSandboxSessionFiles({
  versionId: toRef(props, "versionId"),
  isReadOnly: toRef(props, "isReadOnly"),
  isRunning,
  isSubmitting,
  fileFields,
  fileSelections,
  fileErrors,
});

const sandboxFileRefs = useSandboxFileRefs({ versionId: toRef(props, "versionId") });
const availableFileRefs = sandboxFileRefs.fileRefs;

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
  fileFields,
  fileSelections,
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
const showSessionFilesPanel = computed(() => fileFields.value.length === 0);

const actionErrorMessage = actions.actionErrorMessage;
const completedSteps = actions.completedSteps;
const selectedStepIndex = actions.selectedStepIndex;
const canSubmitActions = actions.canSubmitActions;

const inputsValid = computed(() => {
  const fileErrorsByField = effectiveFileErrors.value;
  const hasFileErrors = Object.values(fileErrorsByField).some((value) => value !== null);
  return !hasFileErrors && Object.keys(inputFieldErrors.value).length === 0;
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

function updateFileMode(payload: { field: string; mode: FileSelectionMode }): void {
  toolInputs.setFileMode(payload.field, payload.mode);
}

function updateFileUploads(payload: { field: string; files: File[] }): void {
  toolInputs.setFileUploads(payload.field, payload.files);
}

function updateFileRefs(payload: { field: string; refs: string[] }): void {
  toolInputs.setFileRefs(payload.field, payload.refs);
}

async function deleteFileRefs(payload: { field: string; refs: string[] }): Promise<void> {
  const snapshotId = sessionFilesSnapshotId.value;
  if (!snapshotId) return;
  const sessionRefs = payload.refs.filter((ref) => getFileRefSource(ref) === "session");
  if (sessionRefs.length === 0) return;
  const names = availableFileRefs.value
    .filter((ref) => sessionRefs.includes(ref.ref))
    .map((ref) => ref.name);
  if (names.length === 0) return;
  try {
    await deleteSessionFiles(snapshotId, names);
    await sandboxFileRefs.fetchFileRefs(snapshotId);
  } catch (error: unknown) {
    if (error instanceof Error) {
      runExec.errorMessage.value = error.message;
    } else {
      runExec.errorMessage.value = "Det gick inte att ta bort filer.";
    }
  }
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

watch(
  () => runExec.snapshotId.value,
  (snapshotId) => {
    if (!snapshotId) {
      sandboxFileRefs.reset();
      return;
    }
    void sandboxFileRefs.fetchFileRefs(snapshotId);
  },
);

watch(
  () => props.versionId,
  () => {
    sandboxFileRefs.reset();
  },
);
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
      :file-fields="fileFields"
      :file-selections="fileSelections"
      :file-accept-by-field="fileAcceptByField"
      :file-errors="effectiveFileErrors"
      :available-file-refs="availableFileRefs"
      :is-running="isRunning"
      :is-read-only="isReadOnly"
      :has-results="hasResults"
      :can-run="canRun"
      @update:input-values="updateInputValues"
      @update:file-mode="updateFileMode"
      @update:file-uploads="updateFileUploads"
      @update:file-refs="updateFileRefs"
      @delete:file-refs="deleteFileRefs"
      @run="runSandbox"
      @clear="clearResult"
    />

    <SessionFilesPanel
      v-if="showSessionFilesPanel"
      v-model:mode="sessionFilesMode"
      :files="sessionFiles"
      density="compact"
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
      :available-file-refs="availableFileRefs"
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
      :available-file-refs="availableFileRefs"
      @select-step="selectedStepIndex = $event"
      @submit-action="onSubmitAction"
    />
  </div>
</template>
