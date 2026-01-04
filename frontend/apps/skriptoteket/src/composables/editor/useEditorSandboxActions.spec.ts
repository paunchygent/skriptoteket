import { beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, nextTick, ref } from "vue";
import { mount } from "@vue/test-utils";

import { useEditorSandboxActions } from "./useEditorSandboxActions";

const clientMocks = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  isApiError: vi.fn(),
}));

vi.mock("../../api/client", () => ({
  apiFetch: clientMocks.apiFetch,
  isApiError: clientMocks.isApiError,
}));

async function flushPromises(): Promise<void> {
  await nextTick();
  await Promise.resolve();
}

type EditorRunDetails = {
  run_id: string;
  version_id: string | null;
  snapshot_id: string | null;
  status: "running" | "succeeded" | "failed" | "timed_out";
  started_at: string;
  finished_at: string | null;
  error_summary: string | null;
  ui_payload: Record<string, unknown> | null;
  artifacts: unknown[];
};

function createRun(
  runId: string,
  versionId: string | null = "ver-1",
  snapshotId: string | null = "snap-1",
): EditorRunDetails {
  return {
    run_id: runId,
    version_id: versionId,
    snapshot_id: snapshotId,
    status: "succeeded",
    started_at: "2030-01-01T00:00:00Z",
    finished_at: "2030-01-01T00:00:01Z",
    error_summary: null,
    ui_payload: null,
    artifacts: [],
  };
}

function mountActions({
  versionIdValue = "ver-1",
  isReadOnlyValue = false,
  stateRevValue = 2,
  snapshotIdValue = "snap-1",
  isRunningValue = false,
}: {
  versionIdValue?: string;
  isReadOnlyValue?: boolean;
  stateRevValue?: number | null;
  snapshotIdValue?: string | null;
  isRunningValue?: boolean;
} = {}) {
  const versionId = ref(versionIdValue);
  const isReadOnly = ref(isReadOnlyValue);
  const runResult = ref<EditorRunDetails | null>(createRun("run-1", versionIdValue, snapshotIdValue));
  const snapshotId = ref<string | null>(snapshotIdValue);
  const isRunning = ref(isRunningValue);
  const isSubmitting = ref(false);
  const stateRev = ref<number | null>(stateRevValue);
  const startPolling = vi.fn();
  const stopPolling = vi.fn();
  let actions!: ReturnType<typeof useEditorSandboxActions>;

  const TestComponent = defineComponent({
    name: "TestEditorSandboxActions",
    setup() {
      actions = useEditorSandboxActions({
        versionId,
        isReadOnly,
        runResult: runResult as never,
        snapshotId,
        isRunning,
        isSubmitting,
        stateRev,
        startPolling,
        stopPolling,
      });
      return actions;
    },
    template: "<div />",
  });

  const wrapper = mount(TestComponent);

  return {
    wrapper,
    actions,
    versionId,
    isReadOnly,
    runResult,
    snapshotId,
    isRunning,
    isSubmitting,
    stateRev,
    startPolling,
    stopPolling,
  };
}

beforeEach(() => {
  clientMocks.apiFetch.mockReset();
  clientMocks.isApiError.mockReset();
});

describe("useEditorSandboxActions", () => {
  it("resets multi-step state", async () => {
    const { actions, stateRev, wrapper } = mountActions();

    actions.completedSteps.value = [createRun("old-1") as never];
    actions.selectedStepIndex.value = 0;
    actions.actionErrorMessage.value = "boom";
    stateRev.value = 9;

    actions.resetActions();

    expect(stateRev.value).toBeNull();
    expect(actions.completedSteps.value).toEqual([]);
    expect(actions.selectedStepIndex.value).toBeNull();
    expect(actions.actionErrorMessage.value).toBeNull();

    wrapper.unmount();
  });

  it("requires a snapshot id to submit actions", async () => {
    const { actions, snapshotId, startPolling, wrapper } = mountActions({ snapshotIdValue: null });

    snapshotId.value = null;
    await actions.onSubmitAction({ actionId: "do", input: {} });

    expect(actions.actionErrorMessage.value).toBe("Ingen snapshot tillgänglig. Testkör igen.");
    expect(startPolling).not.toHaveBeenCalled();

    wrapper.unmount();
  });

  it("starts polling and updates state_rev on success", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2030-01-01T00:00:00Z"));

    clientMocks.apiFetch.mockResolvedValueOnce({ run_id: "run-2", state_rev: 3 });

    const { actions, runResult, stateRev, startPolling, stopPolling, isSubmitting, wrapper } =
      mountActions();

    expect(isSubmitting.value).toBe(false);

    await actions.onSubmitAction({ actionId: "step", input: { foo: "bar" } as never });
    await flushPromises();

    expect(stopPolling).toHaveBeenCalled();
    expect(stateRev.value).toBe(3);
    expect(actions.completedSteps.value).toHaveLength(1);
    expect(actions.completedSteps.value[0]?.run_id).toBe("run-1");
    expect(runResult.value?.run_id).toBe("run-2");
    expect(runResult.value?.status).toBe("running");
    expect(runResult.value?.started_at).toBe("2030-01-01T00:00:00.000Z");
    expect(startPolling).toHaveBeenCalledWith("run-2");
    expect(isSubmitting.value).toBe(false);

    wrapper.unmount();
    vi.useRealTimers();
  });

  it("shows a conflict message on optimistic lock conflicts", async () => {
    clientMocks.apiFetch.mockRejectedValueOnce({ status: 409, message: "Conflict" });
    clientMocks.isApiError.mockReturnValue(true);

    const { actions, startPolling, wrapper } = mountActions();

    await actions.onSubmitAction({ actionId: "step", input: {} });
    await flushPromises();

    expect(actions.actionErrorMessage.value).toBe(
      "Din session har ändrats. Uppdatera och försök igen.",
    );
    expect(actions.completedSteps.value).toEqual([]);
    expect(startPolling).not.toHaveBeenCalled();

    wrapper.unmount();
  });
});
