import { computed, onBeforeUnmount, ref, watch, type Ref } from "vue";

import { apiFetch, apiGet, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";

type ToolMetadataResponse = components["schemas"]["ToolMetadataResponse"];
type GetRunResult = components["schemas"]["GetRunResult"];
type StartToolRunResponse = components["schemas"]["StartToolRunResponse"];
type StartActionResult = components["schemas"]["StartActionResult"];
type GetSessionStateResult = components["schemas"]["GetSessionStateResult"];
type RunDetails = components["schemas"]["RunDetails"];

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
  const tool = ref<ToolMetadataResponse | null>(null);
  const selectedFiles = ref<File[]>([]);
  const currentRun = ref<RunDetails | null>(null);
  const completedSteps = ref<StepResult[]>([]);
  const stateRev = ref<number | null>(null);

  const isLoadingTool = ref(true);
  const isSubmitting = ref(false);
  const isPolling = ref(false);
  const errorMessage = ref<string | null>(null);
  const actionErrorMessage = ref<string | null>(null);

  let pollIntervalId: number | null = null;

  const hasFiles = computed(() => selectedFiles.value.length > 0);
  const hasResults = computed(() => currentRun.value !== null);
  const isRunning = computed(() => currentRun.value?.status === "running");
  const hasNextActions = computed(() => (currentRun.value?.ui_payload?.next_actions ?? []).length > 0);
  const canSubmitActions = computed(() => stateRev.value !== null && hasNextActions.value);

  function isTerminalStatus(status: string): boolean {
    return status !== "running";
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

  function stopPolling(): void {
    if (pollIntervalId !== null) {
      window.clearInterval(pollIntervalId);
      pollIntervalId = null;
      isPolling.value = false;
    }
  }

  function startPolling(runId: string): void {
    if (pollIntervalId !== null) return;

    isPolling.value = true;
    pollIntervalId = window.setInterval(() => {
      void fetchRun(runId).catch(() => {
        // Silent polling failure; main error handling happens elsewhere.
      });
    }, 2000);
  }

  async function submitRun(): Promise<void> {
    if (!slug.value || !tool.value) {
      errorMessage.value = "Verktyget är inte laddat.";
      return;
    }
    if (!hasFiles.value) {
      errorMessage.value = "Välj minst en fil.";
      return;
    }
    if (isSubmitting.value) return;

    isSubmitting.value = true;
    errorMessage.value = null;
    actionErrorMessage.value = null;
    stopPolling();

    const formData = new FormData();
    for (const file of selectedFiles.value) {
      formData.append("files", file);
    }

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
        status: "running",
      };

      // Fetch full run details
      await fetchRun(response.run_id);

      // Start polling if still running
      if (currentRun.value?.status === "running") {
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
      if (currentRun.value?.status === "running") {
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

  function selectFiles(files: File[]): void {
    selectedFiles.value = files;
  }

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
      }
    },
  );

  onBeforeUnmount(() => {
    stopPolling();
  });

  return {
    // State
    tool,
    selectedFiles,
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
    hasFiles,
    hasResults,
    isRunning,
    hasNextActions,
    canSubmitActions,

    // Actions
    loadTool,
    submitRun,
    submitAction,
    clearRun,
    selectFiles,
  };
}
