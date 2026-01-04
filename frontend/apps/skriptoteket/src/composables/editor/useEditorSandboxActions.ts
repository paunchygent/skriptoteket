import { computed, ref, type Ref } from "vue";

import { apiFetch, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";

type StartSandboxActionResponse = components["schemas"]["StartSandboxActionResponse"];
type EditorRunDetails = components["schemas"]["EditorRunDetails"];
type JsonValue = components["schemas"]["JsonValue"];

type UseEditorSandboxActionsOptions = {
  versionId: Readonly<Ref<string>>;
  isReadOnly: Readonly<Ref<boolean>>;
  runResult: Ref<EditorRunDetails | null>;
  snapshotId: Readonly<Ref<string | null>>;
  isRunning: Ref<boolean>;
  isSubmitting: Ref<boolean>;
  stateRev: Ref<number | null>;
  startPolling: (runId: string) => void;
  stopPolling: () => void;
};

export function useEditorSandboxActions({
  versionId,
  isReadOnly,
  runResult,
  snapshotId,
  isRunning,
  isSubmitting,
  stateRev,
  startPolling,
  stopPolling,
}: UseEditorSandboxActionsOptions) {
  const actionErrorMessage = ref<string | null>(null);
  const completedSteps = ref<EditorRunDetails[]>([]);
  const selectedStepIndex = ref<number | null>(null);

  const canSubmitActions = computed(() => {
    return stateRev.value !== null && !isRunning.value && !isSubmitting.value && !isReadOnly.value;
  });

  function resetActions(): void {
    stateRev.value = null;
    actionErrorMessage.value = null;
    completedSteps.value = [];
    selectedStepIndex.value = null;
  }

  async function onSubmitAction(payload: {
    actionId: string;
    input: Record<string, JsonValue>;
  }): Promise<void> {
    if (!canSubmitActions.value || !runResult.value) return;

    if (isReadOnly.value) {
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

    completedSteps.value.push(runResult.value);
    selectedStepIndex.value = null;

    try {
      const response = await apiFetch<StartSandboxActionResponse>(
        `/api/v1/editor/tool-versions/${encodeURIComponent(versionId.value)}/start-action`,
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

      stateRev.value = response.state_rev;

      runResult.value = {
        run_id: response.run_id,
        version_id: versionId.value,
        snapshot_id: snapshotId.value,
        status: "running",
        started_at: new Date().toISOString(),
        finished_at: null,
        error_summary: null,
        ui_payload: null,
        artifacts: [],
      };

      isRunning.value = true;
      startPolling(response.run_id);
    } catch (error: unknown) {
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

  return {
    stateRev,
    isSubmitting,
    actionErrorMessage,
    completedSteps,
    selectedStepIndex,
    canSubmitActions,
    resetActions,
    onSubmitAction,
  };
}
