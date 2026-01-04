import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, nextTick, ref } from "vue";
import { mount } from "@vue/test-utils";

import { useEditorSandboxRunExecution } from "./useEditorSandboxRunExecution";

const clientMocks = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  apiGet: vi.fn(),
  isApiError: vi.fn(),
}));

vi.mock("../../api/client", () => ({
  apiFetch: clientMocks.apiFetch,
  apiGet: clientMocks.apiGet,
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

function createEditorRunDetails({
  runId,
  versionId = "ver-1",
  snapshotId = "snap-1",
  status = "running",
}: {
  runId: string;
  versionId?: string | null;
  snapshotId?: string | null;
  status?: EditorRunDetails["status"];
}): EditorRunDetails {
  return {
    run_id: runId,
    version_id: versionId,
    snapshot_id: snapshotId,
    status,
    started_at: "2030-01-01T00:00:00Z",
    finished_at: status === "running" ? null : "2030-01-01T00:00:01Z",
    error_summary: null,
    ui_payload: null,
    artifacts: [],
  };
}

function mountRunExecution({
  isReadOnlyValue = false,
  validateSchemasNowResult = true,
  schemaValidationErrorValue = null,
  effectiveSessionFilesModeValue = "none",
  sessionFilesSnapshotIdValue = null,
}: {
  isReadOnlyValue?: boolean;
  validateSchemasNowResult?: boolean;
  schemaValidationErrorValue?: string | null;
  effectiveSessionFilesModeValue?: "none" | "reuse" | "clear";
  sessionFilesSnapshotIdValue?: string | null;
} = {}) {
  const versionId = ref("ver-1");
  const isReadOnly = ref(isReadOnlyValue);
  const isRunning = ref(false);
  const entrypoint = ref("run_tool");
  const sourceCode = ref("print('hello')");
  const usageInstructions = ref("Use it.");
  const settingsSchema = ref(null);
  const inputSchema = ref([] as never);
  const inputSchemaError = ref<string | null>(null);
  const settingsSchemaError = ref<string | null>(null);
  const hasBlockingSchemaIssues = ref(false);
  const schemaValidationError = ref<string | null>(schemaValidationErrorValue);

  const selectedFiles = ref<File[]>([]);
  const effectiveSessionFilesMode = ref<"none" | "reuse" | "clear">(effectiveSessionFilesModeValue);
  const sessionFilesSnapshotId = ref<string | null>(sessionFilesSnapshotIdValue);
  const sessionFilesMode = ref<"none" | "reuse" | "clear">("none");
  const fetchSessionFiles = vi.fn().mockResolvedValue(undefined);

  const validateSchemasNow = vi.fn().mockResolvedValue(validateSchemasNowResult);
  const buildApiInputs = vi.fn().mockReturnValue({ foo: "bar" });
  let runExec!: ReturnType<typeof useEditorSandboxRunExecution>;

  const TestComponent = defineComponent({
    name: "TestEditorSandboxRunExecution",
    setup() {
      runExec = useEditorSandboxRunExecution({
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
      });
      return runExec;
    },
    template: "<div />",
  });

  const wrapper = mount(TestComponent);

  return {
    wrapper,
    runExec,
    isRunning,
    validateSchemasNow,
    buildApiInputs,
    fetchSessionFiles,
    sessionFilesSnapshotId,
    sessionFilesMode,
    effectiveSessionFilesMode,
  };
}

beforeEach(() => {
  clientMocks.apiFetch.mockReset();
  clientMocks.apiGet.mockReset();
  clientMocks.isApiError.mockReset();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("useEditorSandboxRunExecution", () => {
  it("blocks running when read-only", async () => {
    const { runExec, wrapper } = mountRunExecution({ isReadOnlyValue: true });

    await runExec.runSandbox();
    await flushPromises();

    expect(runExec.errorMessage.value).toBe("Du saknar redigeringslåset. Testkörning är spärrad.");
    expect(clientMocks.apiFetch).not.toHaveBeenCalled();

    wrapper.unmount();
  });

  it("blocks running when schema validation fails", async () => {
    const { runExec, validateSchemasNow, wrapper } = mountRunExecution({
      validateSchemasNowResult: false,
      schemaValidationErrorValue: "Fel i schema",
    });

    await runExec.runSandbox();
    await flushPromises();

    expect(validateSchemasNow).toHaveBeenCalled();
    expect(runExec.errorMessage.value).toBe("Fel i schema");
    expect(clientMocks.apiFetch).not.toHaveBeenCalled();

    wrapper.unmount();
  });

  it("starts polling when run begins and status is running", async () => {
    vi.useFakeTimers();

    clientMocks.apiFetch.mockResolvedValueOnce({
      run_id: "run-1",
      snapshot_id: "snap-1",
      started_at: "2030-01-01T00:00:00Z",
      status: "running",
      state_rev: 4,
    });
    clientMocks.apiGet.mockResolvedValueOnce(createEditorRunDetails({ runId: "run-1" }));

    const { runExec, isRunning, wrapper } = mountRunExecution();

    await runExec.runSandbox();
    await flushPromises();

    expect(runExec.snapshotId.value).toBe("snap-1");
    expect(runExec.stateRev.value).toBe(4);
    expect(isRunning.value).toBe(true);

    await vi.advanceTimersByTimeAsync(1500);
    await flushPromises();

    expect(clientMocks.apiGet).toHaveBeenCalledWith("/api/v1/editor/tool-runs/run-1");

    wrapper.unmount();
  });

  it("polls immediately and fetches session files when terminal", async () => {
    clientMocks.apiFetch.mockResolvedValueOnce({
      run_id: "run-1",
      snapshot_id: "snap-1",
      started_at: "2030-01-01T00:00:00Z",
      status: "succeeded",
      state_rev: 1,
    });
    clientMocks.apiGet.mockResolvedValueOnce(
      createEditorRunDetails({ runId: "run-1", status: "succeeded" }),
    );

    const { runExec, isRunning, fetchSessionFiles, sessionFilesSnapshotId, wrapper } =
      mountRunExecution();

    await runExec.runSandbox();
    await flushPromises();

    expect(isRunning.value).toBe(false);
    expect(runExec.runResult.value?.status).toBe("succeeded");
    expect(runExec.snapshotId.value).toBe("snap-1");
    expect(sessionFilesSnapshotId.value).toBe("snap-1");
    expect(fetchSessionFiles).toHaveBeenCalledWith("snap-1");

    wrapper.unmount();
  });
});
