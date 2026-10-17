import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiGet, apiPost } from "../api/client";
import AppDetailView from "./AppDetailView.vue";

vi.mock("vue-router", () => ({
  useRoute: () => ({ params: { appId: "test.fallback" } }),
}));
vi.mock("../api/client", () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  isApiError: () => false,
}));
vi.mock("../stores/auth", () => ({
  useAuthStore: () => ({ bootstrapped: true, isAuthenticated: true }),
}));

const run = {
  run_id: "run-1",
  status: "succeeded",
  artifacts: [],
  ui_payload: {
    outputs: [],
    next_actions: [{
      action_id: "confirm",
      label: "Confirm",
      kind: "form",
      fields: [{ name: "documents", kind: "file_ref", label: "Documents", min: 1, max: 1 }],
    }],
  },
};

function mountFallback() {
  return mount(AppDetailView, {
    global: {
      stubs: {
        RouterLink: true,
        ToolRunArtifacts: true,
        VaultPickerModal: {
          name: "VaultPickerModal",
          props: ["isOpen"],
          emits: ["confirm"],
          template: '<button v-if="isOpen" @click="$emit(\'confirm\', [\'vault:selected.pdf\'])">Select fixture file</button>',
        },
      },
    },
  });
}

describe("AppDetailView fallback actions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiGet).mockImplementation(async (path) => {
      if (path === "/api/v1/apps/test.fallback") {
        return { app_id: "test.fallback", tool_id: "tool-1", title: "Fallback" };
      }
      if (path === "/api/v1/tools/tool-1/sessions/default") {
        return { session_state: { state_rev: 7, latest_run_id: "run-1" } };
      }
      if (path === "/api/v1/runs/run-1" || path === "/api/v1/runs/run-2") {
        return { run };
      }
      if (path === "/api/v1/tools/tool-1/file-refs?context=default") {
        return {
          tool_id: "tool-1", context: "default",
          files: [{ ref: "session:source.pdf", name: "source.pdf", bytes: 100 }],
        };
      }
      throw new Error(`Unexpected request: ${path}`);
    });
    vi.mocked(apiPost).mockResolvedValue({ run_id: "run-2", state_rev: 8 });
  });

  it("sends a vault file selected through the shared action control to start_action", async () => {
    const wrapper = mountFallback();
    await flushPromises();

    const openPicker = wrapper.findAll("button").find((button) => button.text() === "Välj bland Mina filer");
    expect(openPicker).toBeDefined();
    await openPicker!.trigger("click");
    const selectFile = wrapper.findAll("button").find((button) => button.text() === "Select fixture file");
    await selectFile!.trigger("click");
    const confirm = wrapper.findAll("button").find((button) => button.text() === "Confirm");
    expect(confirm?.attributes("disabled")).toBeUndefined();
    await confirm!.trigger("click");
    await flushPromises();

    expect(apiPost).toHaveBeenCalledWith("/api/v1/start_action", {
      tool_id: "tool-1", context: "default", action_id: "confirm", input: {},
      expected_state_rev: 7,
      file_refs_by_field: { documents: ["vault:selected.pdf"] },
    });
    wrapper.unmount();
  });

  it("loads tool-scoped session files and sends the selected reference", async () => {
    const wrapper = mountFallback();
    await flushPromises();

    expect(apiGet).toHaveBeenCalledWith("/api/v1/tools/tool-1/file-refs?context=default");
    expect(wrapper.text()).toContain("source.pdf");
    await wrapper.get('input[type="checkbox"]').setValue(true);
    const confirm = wrapper.findAll("button").find((button) => button.text() === "Confirm");
    await confirm!.trigger("click");
    await flushPromises();

    expect(apiPost).toHaveBeenCalledWith("/api/v1/start_action", expect.objectContaining({
      file_refs_by_field: { documents: ["session:source.pdf"] },
      expected_state_rev: 7,
    }));
    wrapper.unmount();
  });
});
