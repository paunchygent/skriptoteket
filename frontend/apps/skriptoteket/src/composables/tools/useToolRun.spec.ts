import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, ref } from "vue";
import { mount } from "@vue/test-utils";

import type { components } from "../../api/openapi";
import { useToolRun } from "./useToolRun";

const clientMocks = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  apiGet: vi.fn(),
  isApiError: vi.fn(),
}));

const toolInputsState = vi.hoisted(() => {
  const state: { value: ToolInputsMock | null } = { value: null };
  return state;
});

const authState = vi.hoisted(() => ({
  bootstrapped: true,
  isAuthenticated: false,
}));

vi.mock("../../api/client", () => ({
  apiFetch: clientMocks.apiFetch,
  apiGet: clientMocks.apiGet,
  isApiError: clientMocks.isApiError,
}));

type ToolInputsMock = {
  fileFields: ReturnType<typeof ref<Array<{ name: string; label: string; min: number; max: number }>>>;
  fileSelections: ReturnType<typeof ref<Record<string, { mode: "upload" | "refs"; uploads: File[]; refs: string[] }>>>;
  fileAcceptByField: ReturnType<typeof ref<Record<string, string | undefined>>>;
  fileErrors: ReturnType<typeof ref<Record<string, string | null>>>;
  hasFileSelections: ReturnType<typeof ref<boolean>>;
  fieldErrors: ReturnType<typeof ref<Record<string, string>>>;
  values: ReturnType<typeof ref<Record<string, unknown>>>;
  nonFileFields: ReturnType<typeof ref<unknown[]>>;
  resetValues: ReturnType<typeof vi.fn>;
  resetFileSelections: ReturnType<typeof vi.fn>;
  setFileMode: ReturnType<typeof vi.fn>;
  setFileUploads: ReturnType<typeof vi.fn>;
  setFileRefs: ReturnType<typeof vi.fn>;
  buildApiValues: ReturnType<typeof vi.fn>;
};

type ToolMetadataResponse = components["schemas"]["ToolMetadataResponse"];
type UploadConstraints = components["schemas"]["UploadConstraints"];
type RunDetails = components["schemas"]["RunDetails"];

const baseUploadConstraints: UploadConstraints = {
  max_file_bytes: 10_000,
  max_files: 10,
  max_total_bytes: 50_000,
};

function makeTool(overrides: Partial<ToolMetadataResponse> = {}): ToolMetadataResponse {
  return {
    id: "tool-1",
    slug: "demo-tool",
    title: "Tool",
    summary: null,
    input_schema: [],
    upload_constraints: baseUploadConstraints,
    usage_instructions: null,
    usage_instructions_seen: false,
    ...overrides,
  };
}

function makeRunDetails(overrides: Partial<RunDetails> = {}): RunDetails {
  return {
    run_id: "run-1",
    tool_id: "tool-1",
    tool_title: "Tool",
    status: "succeeded",
    ...overrides,
  };
}

let toolInputs: ToolInputsMock;
const mountedWrappers: Array<ReturnType<typeof mount>> = [];

function createToolInputs(): ToolInputsMock {
  return {
    fileFields: ref([{ name: "files", label: "Filer", min: 1, max: 3 }]),
    fileSelections: ref({
      files: { mode: "upload", uploads: [], refs: [] },
    }),
    fileAcceptByField: ref({}),
    fileErrors: ref({ files: null }),
    hasFileSelections: ref(false),
    fieldErrors: ref({}),
    values: ref({}),
    nonFileFields: ref([]),
    resetValues: vi.fn(),
    resetFileSelections: vi.fn(),
    setFileMode: vi.fn(),
    setFileUploads: vi.fn(),
    setFileRefs: vi.fn(),
    buildApiValues: vi.fn().mockReturnValue({}),
  };
}

vi.mock("./useToolInputs", () => ({
  useToolInputs: () => toolInputsState.value,
}));

vi.mock("../../stores/auth", () => ({
  useAuthStore: () => authState,
}));

function mountToolRun(initialSlug = "demo-tool") {
  const slug = ref(initialSlug);
  let toolRun!: ReturnType<typeof useToolRun>;

  const TestComponent = defineComponent({
    name: "TestToolRun",
    setup() {
      toolRun = useToolRun({ slug });
      return toolRun;
    },
    template: "<div />",
  });

  const wrapper = mount(TestComponent);
  mountedWrappers.push(wrapper);

  return { toolRun, slug, wrapper };
}

beforeEach(() => {
  toolInputs = createToolInputs();
  toolInputsState.value = toolInputs;
  clientMocks.apiFetch.mockReset();
  clientMocks.apiGet.mockReset();
  clientMocks.isApiError.mockReset();
});

afterEach(() => {
  mountedWrappers.forEach((wrapper) => wrapper.unmount());
  mountedWrappers.length = 0;
});

describe("useToolRun", () => {
  it("sets an error when submitting without a loaded tool", async () => {
    const { toolRun } = mountToolRun();

    await toolRun.submitRun();

    expect(toolRun.errorMessage.value).toBe("Verktyget är inte laddat.");
    expect(clientMocks.apiFetch).not.toHaveBeenCalled();
  });

  it("surfaces validation errors from tool inputs when schema exists", async () => {
    const { toolRun } = mountToolRun();

    toolRun.tool.value = makeTool({ id: "tool-1", title: "Tool", input_schema: [] });
    toolInputs.fileErrors.value = { files: "File error" };

    await toolRun.submitRun();

    expect(toolRun.errorMessage.value).toBe("File error");
    expect(clientMocks.apiFetch).not.toHaveBeenCalled();
  });

  it("submits a run with FormData and stores the resolved run", async () => {
    const { toolRun } = mountToolRun();

    toolRun.tool.value = makeTool({ id: "tool-1", title: "Tool", input_schema: [] });
    toolInputs.fileSelections.value = {
      files: { mode: "upload", uploads: [new File(["test"], "test.txt")], refs: [] },
    };

    clientMocks.apiFetch.mockResolvedValue({ run_id: "run-1" });
    clientMocks.apiGet.mockResolvedValue({
      run: {
        run_id: "run-1",
        tool_id: "tool-1",
        tool_title: "Tool",
        status: "completed",
      },
    });

    await toolRun.submitRun();

    expect(clientMocks.apiFetch).toHaveBeenCalledWith(
      "/api/v1/tools/demo-tool/run",
      expect.objectContaining({
        method: "POST",
        body: expect.any(FormData),
      }),
    );
    expect(clientMocks.apiGet).toHaveBeenCalledWith("/api/v1/runs/run-1");
    expect(toolRun.currentRun.value?.run_id).toBe("run-1");
    expect(toolRun.isSubmitting.value).toBe(false);
    expect(toolRun.isPolling.value).toBe(false);
  });

  it("blocks actions when session state is missing", async () => {
    const { toolRun } = mountToolRun();

    toolRun.currentRun.value = makeRunDetails({ status: "succeeded" });

    await toolRun.submitAction({ actionId: "next", input: {} });

    expect(toolRun.actionErrorMessage.value).toBe(
      "Sessionen är inte redo än. Försök igen.",
    );
    expect(clientMocks.apiFetch).not.toHaveBeenCalled();
  });

  it("maps 409 conflicts to user-friendly action errors", async () => {
    const { toolRun } = mountToolRun();

    toolRun.currentRun.value = makeRunDetails({ status: "succeeded" });
    toolRun.stateRev.value = 3;

    const conflictError = { status: 409, message: "Conflict" };
    clientMocks.apiFetch.mockRejectedValue(conflictError);
    clientMocks.isApiError.mockReturnValue(true);

    await toolRun.submitAction({ actionId: "next", input: {} });

    expect(clientMocks.apiFetch).toHaveBeenCalledWith(
      "/api/v1/start_action",
      expect.objectContaining({ method: "POST" }),
    );
    expect(toolRun.actionErrorMessage.value).toBe(
      "Din session har ändrats i en annan flik. Uppdatera och försök igen.",
    );
  });
});
