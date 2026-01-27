import { computed, ref, watch, type Ref } from "vue";

import { apiFetch, apiGet, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";
import { useAuthStore } from "../../stores/auth";
import { useToolInputs } from "./useToolInputs";
import { getFileRefSource } from "./fileRefHelpers";
import { useToolFileRefs } from "./useToolFileRefs";
import { useToolRunPolling } from "./useToolRunPolling";

type ToolMetadataResponse = components["schemas"]["ToolMetadataResponse"];
type GetRunResult = components["schemas"]["GetRunResult"];
type StartToolRunResponse = components["schemas"]["StartToolRunResponse"];
type StartActionResult = components["schemas"]["StartActionResult"];
type GetSessionStateResult = components["schemas"]["GetSessionStateResult"];
type RunDetails = components["schemas"]["RunDetails"];
type RunStatus = components["schemas"]["RunStatus"];
type JsonValue = components["schemas"]["JsonValue"];

export interface StepResult {
  id: string;
  stepNumber: number;
  label: string;
  status: "completed" | "current" | "pending";
  run: RunDetails;
}

type UseToolRunOptions = {
  slug: Readonly<Ref<string>>;
};

export function useToolRun({ slug }: UseToolRunOptions) {
  const auth = useAuthStore();
  const tool = ref<ToolMetadataResponse | null>(null);
  const currentRun = ref<RunDetails | null>(null);
  const completedSteps = ref<StepResult[]>([]);
  const stateRev = ref<number | null>(null);

  const inputSchema = computed(() => tool.value?.input_schema ?? []);
  const toolInputs = useToolInputs({ schema: inputSchema });
  const toolFileRefs = useToolFileRefs();

  const isLoadingTool = ref(true);
  const isSubmitting = ref(false);
  const errorMessage = ref<string | null>(null);
  const actionErrorMessage = ref<string | null>(null);

  const hasResults = computed(() => currentRun.value !== null);
  const isRunning = computed(() => {
    return currentRun.value?.status === "running" || currentRun.value?.status === "queued";
  });
  const hasNextActions = computed(() => {
    return (currentRun.value?.ui_payload?.next_actions ?? []).length > 0;
  });
  const canSubmitActions = computed(() => stateRev.value !== null && hasNextActions.value);

  const inputsValid = computed(() => {
    const fileErrors = toolInputs.fileErrors.value;
    const hasFileErrors = Object.values(fileErrors).some((value) => value !== null);
    return !hasFileErrors && Object.keys(toolInputs.fieldErrors.value).length === 0;
  });
  const firstFileError = computed(() => {
    return Object.values(toolInputs.fileErrors.value).find((value) => value !== null) ?? null;
  });
  const canSubmitRun = computed(() => {
    if (!tool.value) return false;
    return inputsValid.value;
  });

  function isTerminalStatus(status: RunStatus): boolean {
    return status !== "running" && status !== "queued";
  }

  async function refreshToolFiles(): Promise<void> {
    const toolId = tool.value?.id ?? null;
    if (!toolId) {
      toolFileRefs.reset();
      return;
    }
    if (!auth.bootstrapped) {
      return;
    }
    if (!auth.isAuthenticated) {
      toolFileRefs.reset();
      return;
    }
    await toolFileRefs.fetchFileRefs(toolId);
  }

  async function deleteFileRefs(payload: { field: string; refs: string[] }): Promise<void> {
    const toolId = tool.value?.id ?? null;
    if (!toolId) return;
    const sessionRefs = payload.refs.filter((ref) => getFileRefSource(ref) === "session");
    if (sessionRefs.length === 0) return;
    const names = sessionRefs
      .map((ref) => toolFileRefs.fileRefs.value.find((item) => item.ref === ref)?.name)
      .filter((name): name is string => typeof name === "string" && name.length > 0);
    if (names.length === 0) return;
    try {
      await apiFetch(
        `/api/v1/tools/${encodeURIComponent(toolId)}/session-files/delete?context=default`,
        {
          method: "POST",
          body: { names },
        },
      );
      await toolFileRefs.fetchFileRefs(toolId);
    } catch (error: unknown) {
      if (isApiError(error)) {
        errorMessage.value = error.message;
      } else if (error instanceof Error) {
        errorMessage.value = error.message;
      } else {
        errorMessage.value = "Det gick inte att ta bort filer.";
      }
    }
  }

  async function loadTool(): Promise<void> {
    if (!slug.value) {
      tool.value = null;
      return;
    }

    isLoadingTool.value = true;
    errorMessage.value = null;

    try {
      tool.value = await apiGet<ToolMetadataResponse>(
        `/api/v1/tools/${encodeURIComponent(slug.value)}`,
      );
    } catch (error: unknown) {
      tool.value = null;
      if (isApiError(error)) {
        errorMessage.value = error.message;
      } else if (error instanceof Error) {
        errorMessage.value = error.message;
      } else {
        errorMessage.value = "Det gick inte att ladda verktyget.";
      }
    } finally {
      isLoadingTool.value = false;
    }
  }

  async function fetchRun(runId: string): Promise<void> {
    const response = await apiGet<GetRunResult>(
      `/api/v1/runs/${encodeURIComponent(runId)}`,
    );
    currentRun.value = response.run;
  }

  async function fetchSessionState(toolId: string): Promise<void> {
    const response = await apiGet<GetSessionStateResult>(
      `/api/v1/tools/${encodeURIComponent(toolId)}/sessions/default`,
    );
    stateRev.value = response.session_state.state_rev;
  }

  const { isPolling, startPolling, stopPolling } = useToolRunPolling({
    poll: (runId) => fetchRun(runId),
  });

  async function submitRun(): Promise<void> {
    if (!slug.value || !tool.value) {
      errorMessage.value = "Verktyget är inte laddat.";
      return;
    }
    if (!inputsValid.value) {
      errorMessage.value =
        firstFileError.value ??
        Object.values(toolInputs.fieldErrors.value)[0] ??
        "Kontrollera indata.";
      return;
    }
    if (isSubmitting.value) return;

    isSubmitting.value = true;
    errorMessage.value = null;
    actionErrorMessage.value = null;
    stopPolling();

    const formData = new FormData();
    const fileFields: string[] = [];
    const fileRefsByField: Record<string, string[]> = {};
    for (const field of toolInputs.fileFields.value) {
      const selection = toolInputs.fileSelections.value[field.name];
      if (!selection) continue;
      if (selection.mode === "upload") {
        for (const file of selection.uploads) {
          formData.append("files", file);
          fileFields.push(field.name);
        }
      } else if (selection.refs.length > 0) {
        fileRefsByField[field.name] = [...selection.refs];
      }
    }
    if (fileFields.length > 0) {
      formData.append("file_fields", JSON.stringify(fileFields));
    }
    if (Object.keys(fileRefsByField).length > 0) {
      formData.append("file_refs_by_field", JSON.stringify(fileRefsByField));
    }

    let inputValues: Record<string, JsonValue> = {};
    try {
      inputValues = toolInputs.buildApiValues();
    } catch (error: unknown) {
      if (error instanceof Error) {
        errorMessage.value = error.message;
      } else {
        errorMessage.value = "Indata är ogiltig.";
      }
      isSubmitting.value = false;
      return;
    }
    formData.append("inputs", JSON.stringify(inputValues));

    try {
      const response = await apiFetch<StartToolRunResponse>(
        `/api/v1/tools/${encodeURIComponent(slug.value)}/run`,
        {
          method: "POST",
          body: formData,
        },
      );

      // Set placeholder run while waiting for full data
      currentRun.value = {
        run_id: response.run_id,
        tool_id: tool.value.id,
        tool_title: tool.value.title,
        status: "queued",
      };

      // Fetch full run details
      await fetchRun(response.run_id);

      // Start polling if still running
      if (currentRun.value?.status === "running" || currentRun.value?.status === "queued") {
        startPolling(response.run_id);
      }

      // Fetch session state for multi-step tools
      if (hasNextActions.value && currentRun.value) {
        try {
          await fetchSessionState(currentRun.value.tool_id);
        } catch {
          stateRev.value = null;
        }
      }
    } catch (error: unknown) {
      if (isApiError(error)) {
        errorMessage.value = error.message;
      } else if (error instanceof Error) {
        errorMessage.value = error.message;
      } else {
        errorMessage.value = "Körning misslyckades.";
      }
    } finally {
      isSubmitting.value = false;
    }
  }

  async function submitAction(payload: {
    actionId: string;
    input: Record<string, components["schemas"]["JsonValue"]>;
    fileRefsByField?: Record<string, string[]>;
  }): Promise<void> {
    if (!currentRun.value) return;
    if (stateRev.value === null) {
      actionErrorMessage.value = "Sessionen är inte redo än. Försök igen.";
      return;
    }
    if (isSubmitting.value) return;

    isSubmitting.value = true;
    actionErrorMessage.value = null;
    stopPolling();

    try {
      // Save current run as completed step before starting new action
      const previousRun = currentRun.value;
      const stepNumber = completedSteps.value.length + 1;

      const response = await apiFetch<StartActionResult>("/api/v1/start_action", {
        method: "POST",
        body: JSON.stringify({
          tool_id: previousRun.tool_id,
          context: "default",
          action_id: payload.actionId,
          input: payload.input,
          file_refs_by_field: payload.fileRefsByField ?? {},
          expected_state_rev: stateRev.value,
        }),
        headers: {
          "Content-Type": "application/json",
        },
      });

      // Add previous run to completed steps
      completedSteps.value = [
        ...completedSteps.value,
        {
          id: previousRun.run_id,
          stepNumber,
          label: `Steg ${stepNumber}`,
          status: "completed",
          run: previousRun,
        },
      ];

      stateRev.value = response.state_rev;

      // Set placeholder for new run
      currentRun.value = {
        run_id: response.run_id,
        tool_id: previousRun.tool_id,
        tool_title: previousRun.tool_title,
        status: "running",
      };

      // Fetch full run details
      await fetchRun(response.run_id);

      // Start polling if still running
      if (currentRun.value?.status === "running" || currentRun.value?.status === "queued") {
        startPolling(response.run_id);
      }
    } catch (error: unknown) {
      if (isApiError(error)) {
        actionErrorMessage.value =
          error.status === 409
            ? "Din session har ändrats i en annan flik. Uppdatera och försök igen."
            : error.message;
      } else if (error instanceof Error) {
        actionErrorMessage.value = error.message;
      } else {
        actionErrorMessage.value = "Det gick inte att köra åtgärden just nu.";
      }
    } finally {
      isSubmitting.value = false;
    }
  }

  function clearRun(): void {
    stopPolling();
    currentRun.value = null;
    completedSteps.value = [];
    stateRev.value = null;
    errorMessage.value = null;
    actionErrorMessage.value = null;
  }

  watch(
    () => slug.value,
    () => {
      toolInputs.resetValues();
      toolInputs.resetFileSelections();
      toolFileRefs.reset();
    },
  );

  watch(
    () => [tool.value?.id ?? null, auth.bootstrapped, auth.isAuthenticated],
    ([toolId, bootstrapped, isAuthenticated]) => {
      if (!toolId) {
        toolFileRefs.reset();
        return;
      }
      if (!bootstrapped) return;
      if (!isAuthenticated) {
        toolFileRefs.reset();
        return;
      }
      void refreshToolFiles();
    },
  );

  // Watch for status changes to manage polling
  watch(
    () => currentRun.value?.status,
    (status) => {
      if (status && isTerminalStatus(status)) {
        stopPolling();
        // Fetch session state when run completes for multi-step tools
        if (hasNextActions.value && currentRun.value) {
          void fetchSessionState(currentRun.value.tool_id).catch(() => {
            stateRev.value = null;
          });
        }
        if (currentRun.value) {
          void refreshToolFiles();
        }
      }
    },
  );

  return {
    // State
    tool,
    fileFields: toolInputs.fileFields,
    fileSelections: toolInputs.fileSelections,
    inputSchema,
    inputValues: toolInputs.values,
    inputFields: toolInputs.nonFileFields,
    inputFieldErrors: toolInputs.fieldErrors,
    fileAcceptByField: toolInputs.fileAcceptByField,
    fileErrors: toolInputs.fileErrors,
    availableFileRefs: toolFileRefs.fileRefs,
    currentRun,
    completedSteps,
    stateRev,

    // Loading states
    isLoadingTool,
    isSubmitting,
    isPolling,

    // Error messages
    errorMessage,
    actionErrorMessage,

    // Computed
    canSubmitRun,
    hasResults,
    isRunning,
    hasNextActions,
    canSubmitActions,

    // Actions
    loadTool,
    submitRun,
    submitAction,
    clearRun,
    setFileMode: toolInputs.setFileMode,
    setFileUploads: toolInputs.setFileUploads,
    setFileRefs: toolInputs.setFileRefs,
    deleteFileRefs,
  };
}
