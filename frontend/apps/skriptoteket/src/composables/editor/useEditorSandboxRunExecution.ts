import { onBeforeUnmount, ref, type Ref } from "vue";

import { apiFetch, apiGet, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";
import type { SessionFilesMode } from "./useEditorSandboxSessionFiles";

type SandboxRunResponse = components["schemas"]["SandboxRunResponse"];
type EditorRunDetails = components["schemas"]["EditorRunDetails"];
type RunStatus = components["schemas"]["RunStatus"];
type JsonValue = components["schemas"]["JsonValue"];

type CreateDraftVersionRequest = components["schemas"]["CreateDraftVersionRequest"];
type ToolInputSchema = NonNullable<CreateDraftVersionRequest["input_schema"]>;
type ToolSettingsSchema = NonNullable<CreateDraftVersionRequest["settings_schema"]>;

type UseEditorSandboxRunExecutionOptions = {
  versionId: Readonly<Ref<string>>;
  isReadOnly: Readonly<Ref<boolean>>;
  isRunning: Ref<boolean>;
  entrypoint: Readonly<Ref<string>>;
  sourceCode: Readonly<Ref<string>>;
  usageInstructions: Readonly<Ref<string>>;
  settingsSchema: Readonly<Ref<ToolSettingsSchema | null>>;
  inputSchema: Readonly<Ref<ToolInputSchema>>;
  inputSchemaError: Readonly<Ref<string | null>>;
  settingsSchemaError: Readonly<Ref<string | null>>;
  hasBlockingSchemaIssues: Readonly<Ref<boolean>>;
  schemaValidationError: Readonly<Ref<string | null>>;
  validateSchemasNow: () => Promise<boolean>;
  buildApiInputs: () => Record<string, JsonValue>;
  selectedFiles: Readonly<Ref<File[]>>;
  effectiveSessionFilesMode: Readonly<Ref<SessionFilesMode>>;
  sessionFilesSnapshotId: Ref<string | null>;
  sessionFilesMode: Ref<SessionFilesMode>;
  fetchSessionFiles: (snapshotId: string) => Promise<void>;
};

const POLL_INTERVAL_MS = 1500;

export function useEditorSandboxRunExecution({
  versionId,
  isReadOnly,
  isRunning,
  entrypoint,
  sourceCode,
  usageInstructions,
  settingsSchema,
  inputSchema,
  inputSchemaError,
  settingsSchemaError,
  hasBlockingSchemaIssues,
  schemaValidationError,
  validateSchemasNow,
  buildApiInputs,
  selectedFiles,
  effectiveSessionFilesMode,
  sessionFilesSnapshotId,
  sessionFilesMode,
  fetchSessionFiles,
}: UseEditorSandboxRunExecutionOptions) {
  const runResult = ref<EditorRunDetails | null>(null);
  const errorMessage = ref<string | null>(null);
  const snapshotId = ref<string | null>(null);
  const lastSentInputsJson = ref<string>("{}");

  const stateRev = ref<number | null>(null);

  let pollingIntervalId: number | null = null;

  function stopPolling(): void {
    if (pollingIntervalId !== null) {
      window.clearInterval(pollingIntervalId);
      pollingIntervalId = null;
    }
  }

  function startPolling(runId: string): void {
    stopPolling();
    isRunning.value = true;
    pollingIntervalId = window.setInterval(() => {
      void pollRunStatus(runId);
    }, POLL_INTERVAL_MS);
  }

  function isTerminalStatus(status: RunStatus): boolean {
    return status !== "running" && status !== "queued";
  }

  async function pollRunStatus(runId: string): Promise<void> {
    try {
      const result = await apiGet<EditorRunDetails>(
        `/api/v1/editor/tool-runs/${encodeURIComponent(runId)}`,
      );
      runResult.value = result;
      if (result.snapshot_id) {
        snapshotId.value = result.snapshot_id;
        sessionFilesSnapshotId.value = result.snapshot_id;
      }

      if (isTerminalStatus(result.status)) {
        stopPolling();
        isRunning.value = false;
        if (result.snapshot_id) {
          void fetchSessionFiles(result.snapshot_id);
        }
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
    if (isReadOnly.value) {
      errorMessage.value = "Du saknar redigeringslåset. Testkörning är spärrad.";
      return;
    }
    if (inputSchemaError.value || settingsSchemaError.value) return;
    if (hasBlockingSchemaIssues.value) return;

    const resolvedEntrypoint = entrypoint.value.trim();
    if (!resolvedEntrypoint) {
      errorMessage.value = "Entrypoint saknas. Ange en giltig entrypoint.";
      return;
    }

    isRunning.value = true;
    errorMessage.value = null;
    runResult.value = null;
    stopPolling();

    stateRev.value = null;
    snapshotId.value = null;

    const schemasValid = await validateSchemasNow();
    if (!schemasValid) {
      isRunning.value = false;
      errorMessage.value =
        schemaValidationError.value ??
        "Schemat innehåller valideringsfel. Åtgärda felen innan du testkör.";
      return;
    }

    let apiInputs: Record<string, JsonValue> = {};
    try {
      apiInputs = buildApiInputs();
    } catch (error: unknown) {
      isRunning.value = false;
      if (error instanceof Error) {
        errorMessage.value = error.message;
      } else {
        errorMessage.value = "Ogiltiga indata. Kontrollera fälten.";
      }
      return;
    }

    const resolvedUsageInstructions = usageInstructions.value.trim();
    const snapshotPayload = {
      entrypoint: resolvedEntrypoint,
      source_code: sourceCode.value,
      settings_schema: settingsSchema.value ?? null,
      input_schema: inputSchema.value,
      usage_instructions: resolvedUsageInstructions ? resolvedUsageInstructions : null,
    };

    const formData = new FormData();
    for (const file of selectedFiles.value) {
      formData.append("files", file);
    }
    formData.append("inputs", JSON.stringify(apiInputs));
    formData.append("snapshot", JSON.stringify(snapshotPayload));
    lastSentInputsJson.value = JSON.stringify(apiInputs, null, 2);

    const resolvedSessionFilesMode = effectiveSessionFilesMode.value;
    if (resolvedSessionFilesMode !== "none" && sessionFilesSnapshotId.value) {
      formData.append("session_files_mode", resolvedSessionFilesMode);
      formData.append("session_context", `sandbox:${sessionFilesSnapshotId.value}`);
    }

    try {
      const response = await apiFetch<SandboxRunResponse>(
        `/api/v1/editor/tool-versions/${encodeURIComponent(versionId.value)}/run-sandbox`,
        {
          method: "POST",
          body: formData,
        },
      );

      snapshotId.value = response.snapshot_id;
      sessionFilesSnapshotId.value = response.snapshot_id;

      if (resolvedSessionFilesMode === "clear") {
        sessionFilesMode.value = "none";
      }

      if (response.state_rev !== null && response.state_rev !== undefined) {
        stateRev.value = response.state_rev;
      }

      runResult.value = {
        run_id: response.run_id,
        version_id: versionId.value,
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
        startPolling(response.run_id);
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

  function clearResult(): void {
    runResult.value = null;
    errorMessage.value = null;
    snapshotId.value = null;
    stateRev.value = null;
  }

  onBeforeUnmount(() => {
    stopPolling();
  });

  return {
    isRunning,
    runResult,
    errorMessage,
    snapshotId,
    lastSentInputsJson,
    stateRev,
    runSandbox,
    clearResult,
    startPolling,
    stopPolling,
  };
}
