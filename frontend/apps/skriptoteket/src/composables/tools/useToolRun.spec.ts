import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, ref } from "vue";
import { mount } from "@vue/test-utils";

import { useToolRun } from "./useToolRun";

const clientMocks = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  apiGet: vi.fn(),
  isApiError: vi.fn(),
}));

const toolInputsState = vi.hoisted(() => ({
  value: null as ToolInputsMock | null,
}));

vi.mock("../../api/client", () => ({
  apiFetch: clientMocks.apiFetch,
  apiGet: clientMocks.apiGet,
  isApiError: clientMocks.isApiError,
}));

type ToolInputsMock = {
  fileError: ReturnType<typeof ref<string | null>>;
  fieldErrors: ReturnType<typeof ref<Record<string, string>>>;
  values: ReturnType<typeof ref<Record<string, unknown>>>;
  nonFileFields: ReturnType<typeof ref<unknown[]>>;
  fileField: ReturnType<typeof ref<unknown>>;
  fileAccept: ReturnType<typeof ref<string>>;
  fileLabel: ReturnType<typeof ref<string>>;
  fileMultiple: ReturnType<typeof ref<boolean>>;
  resetValues: ReturnType<typeof vi.fn>;
  buildApiValues: ReturnType<typeof vi.fn>;
};

let toolInputs: ToolInputsMock;
const mountedWrappers: Array<ReturnType<typeof mount>> = [];

function createToolInputs(): ToolInputsMock {
  return {
    fileError: ref(null),
    fieldErrors: ref({}),
    values: ref({}),
    nonFileFields: ref([]),
    fileField: ref(null),
    fileAccept: ref(""),
    fileLabel: ref(""),
    fileMultiple: ref(false),
    resetValues: vi.fn(),
    buildApiValues: vi.fn().mockReturnValue({}),
  };
}

vi.mock("./useToolInputs", () => ({
  useToolInputs: () => toolInputsState.value,
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

    toolRun.tool.value = { id: "tool-1", title: "Tool", input_schema: [] } as never;
    toolInputs.fileError.value = "File error";

    await toolRun.submitRun();

    expect(toolRun.errorMessage.value).toBe("File error");
    expect(clientMocks.apiFetch).not.toHaveBeenCalled();
  });

  it("submits a run with FormData and stores the resolved run", async () => {
    const { toolRun } = mountToolRun();

    toolRun.tool.value = { id: "tool-1", title: "Tool", input_schema: [] } as never;
    toolRun.selectFiles([new File(["test"], "test.txt")]);

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

    toolRun.currentRun.value = {
      run_id: "run-1",
      tool_id: "tool-1",
      tool_title: "Tool",
      status: "completed",
    } as never;

    await toolRun.submitAction({ actionId: "next", input: {} });

    expect(toolRun.actionErrorMessage.value).toBe(
      "Sessionen är inte redo än. Försök igen.",
    );
    expect(clientMocks.apiFetch).not.toHaveBeenCalled();
  });

  it("maps 409 conflicts to user-friendly action errors", async () => {
    const { toolRun } = mountToolRun();

    toolRun.currentRun.value = {
      run_id: "run-1",
      tool_id: "tool-1",
      tool_title: "Tool",
      status: "completed",
    } as never;
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
