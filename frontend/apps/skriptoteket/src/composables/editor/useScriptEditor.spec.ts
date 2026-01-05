import { beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, nextTick, reactive, ref } from "vue";
import { mount } from "@vue/test-utils";

import { useScriptEditor } from "./useScriptEditor";
import type { UiNotifier } from "../notify";

const clientMocks = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  isApiError: vi.fn(),
}));

vi.mock("../../api/client", () => ({
  apiFetch: clientMocks.apiFetch,
  apiGet: clientMocks.apiGet,
  apiPost: clientMocks.apiPost,
  isApiError: clientMocks.isApiError,
}));

type NotifyMock = {
  info: ReturnType<typeof vi.fn<(message: string) => void>>;
  success: ReturnType<typeof vi.fn<(message: string) => void>>;
  warning: ReturnType<typeof vi.fn<(message: string) => void>>;
  failure: ReturnType<typeof vi.fn<(message: string) => void>>;
};

function createNotify(): NotifyMock {
  return {
    info: vi.fn<(message: string) => void>(),
    success: vi.fn<(message: string) => void>(),
    warning: vi.fn<(message: string) => void>(),
    failure: vi.fn<(message: string) => void>(),
  };
}

async function flushPromises(): Promise<void> {
  await nextTick();
  await Promise.resolve();
}

function createEditorResponse(overrides: Record<string, unknown> = {}) {
  return {
    entrypoint: "run_tool",
    source_code: "print('hi')",
    settings_schema: [],
    input_schema: [],
    usage_instructions: null,
    tool: {
      id: "tool-1",
      title: "Tool",
      summary: null,
      slug: "tool",
    },
    save_mode: "snapshot",
    selected_version: { id: "ver-1" },
    derived_from_version_id: null,
    ...overrides,
  };
}

async function mountEditor({
  editorResponse,
  routePath = "/admin/tools/1",
}: {
  editorResponse: Record<string, unknown>;
  routePath?: string;
}) {
  const toolId = ref("tool-1");
  const versionId = ref("");
  const route = reactive({
    path: routePath,
    fullPath: routePath,
    params: {},
    query: {},
  });
  const router = {
    push: vi.fn().mockResolvedValue(undefined),
  };
  const notify = createNotify();

  clientMocks.apiGet.mockResolvedValueOnce(editorResponse);

  const TestComponent = defineComponent({
    name: "TestScriptEditor",
    setup() {
      return useScriptEditor({
        toolId,
        versionId,
        route: route as never,
        router: router as never,
        notify: notify as UiNotifier,
      });
    },
    template: "<div />",
  });

  const wrapper = mount(TestComponent);
  await flushPromises();

  return { wrapper, router, notify };
}

beforeEach(() => {
  clientMocks.apiFetch.mockReset();
  clientMocks.apiGet.mockReset();
  clientMocks.apiPost.mockReset();
  clientMocks.isApiError.mockReset();
});

describe("useScriptEditor", () => {
  it("saves snapshot versions and navigates on success", async () => {
    const { wrapper, router, notify } = await mountEditor({
      editorResponse: createEditorResponse(),
    });

    clientMocks.apiPost.mockResolvedValueOnce({ redirect_url: "/admin/tools" });

    const vm = wrapper.vm as unknown as ReturnType<typeof useScriptEditor>;
    await vm.save();

    expect(clientMocks.apiPost).toHaveBeenCalledWith(
      "/api/v1/editor/tool-versions/ver-1/save",
      expect.objectContaining({
        entrypoint: "run_tool",
        expected_parent_version_id: "ver-1",
      }),
    );
    expect(notify.success).toHaveBeenCalledWith("Sparat.");
    expect(router.push).toHaveBeenCalledWith("/admin/tools");

    wrapper.unmount();
  });

  it("surfaces conflicts for draft saves", async () => {
    const { wrapper, notify } = await mountEditor({
      editorResponse: createEditorResponse({ save_mode: "draft" }),
    });

    const conflictError = { status: 409, message: "Conflict" };
    clientMocks.apiPost.mockRejectedValueOnce(conflictError);
    clientMocks.isApiError.mockReturnValue(true);

    const vm = wrapper.vm as unknown as ReturnType<typeof useScriptEditor>;
    await vm.save();

    expect(clientMocks.apiPost).toHaveBeenCalledWith(
      "/api/v1/editor/tools/tool-1/draft",
      expect.objectContaining({ entrypoint: "run_tool" }),
    );
    expect(notify.warning).toHaveBeenCalledWith("Conflict");

    wrapper.unmount();
  });
});
