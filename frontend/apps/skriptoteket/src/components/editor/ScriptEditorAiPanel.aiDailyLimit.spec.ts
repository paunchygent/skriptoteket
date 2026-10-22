import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, h, ref } from "vue";

import { ApiError, apiFetch } from "../../api/client";
import { useAuthStore } from "../../stores/auth";
import { mockJsonResponse } from "../../stores/authTestHelpers";
import { useToastStore } from "../../stores/toast";
import {
  AI_APP_LIMIT_NOTE,
  AI_USER_LIMIT_NOTE,
  aiDailyLimitReached,
  resetAiDailyLimitForTests,
} from "../../views/apps/exam-workspace/aiDailyLimit";
import ChatComposer from "./ChatComposer.vue";
import ScriptEditorAiPanel from "./ScriptEditorAiPanel.vue";

vi.mock("../../api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../api/client")>()),
  apiFetch: vi.fn(),
  apiGet: vi.fn(),
  resolveProtectedApiUrl: vi.fn((path: string) => path),
}));

const originalFetch = globalThis.fetch;

type PanelBindings = {
  aiBlockedNote: string | null;
  chatMessages: Array<{ role: string; content: string }>;
  chatError: string | null;
  editOpsRequestError: string | null;
  sendChatMessage: (message: string) => Promise<void>;
  requestEditOps: (message: string) => Promise<void>;
};

function limitRefusal(limit: "user_share" | "pool", message: string): ApiError {
  return new ApiError({
    code: "AI_DAILY_LIMIT_REACHED",
    message,
    status: 429,
    details: { limit },
  });
}

function limitResponse(limit: "user_share" | "pool", message: string): Response {
  return mockJsonResponse(
    { error: { code: "AI_DAILY_LIMIT_REACHED", message, details: { limit } } },
    429,
  );
}

function mountPanel() {
  const captured: { bindings: PanelBindings | null } = { bindings: null };
  const Host = defineComponent({
    setup() {
      const fields = {
        entrypoint: ref("run_tool"),
        sourceCode: ref("print('hej')\n"),
        settingsSchemaText: ref("[]"),
        inputSchemaText: ref("[]"),
        usageInstructions: ref(""),
      };
      return () =>
        h(
          ScriptEditorAiPanel,
          {
            toolId: "tool-1",
            baseVersionId: null,
            isReadOnly: false,
            editorView: null,
            compareActiveFileId: null,
            fields,
            createBeforeApplyCheckpoint: () => undefined,
            isChatDrawerOpen: false,
          },
          {
            default: (bindings: PanelBindings) => {
              captured.bindings = bindings;
              return h(ChatComposer, {
                isStreaming: false,
                isEditOpsLoading: false,
                aiBlockedNote: bindings.aiBlockedNote,
              });
            },
          },
        );
    },
  });
  const wrapper = mount(Host);
  return { wrapper, bindings: () => captured.bindings as PanelBindings };
}

beforeEach(() => {
  setActivePinia(createPinia());
  const auth = useAuthStore();
  auth.user = {
    id: "user-1",
    email: "admin@example.test",
    role: "admin",
    auth_provider: "huleedu",
  } as typeof auth.user;
  auth.csrfToken = "csrf";
  resetAiDailyLimitForTests();
  vi.mocked(apiFetch).mockReset();
});

afterEach(() => {
  globalThis.fetch = originalFetch;
});

describe("ScriptEditorAiPanel daily limit", () => {
  it("shows the app note inline and disables send when the chat POST answers 429 pool", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(limitResponse("pool", AI_APP_LIMIT_NOTE));
    const { wrapper, bindings } = mountPanel();

    await bindings().sendChatMessage("Hej");

    expect(bindings().aiBlockedNote).toBe(AI_APP_LIMIT_NOTE);
    expect(bindings().chatError).toBeNull();
    expect(bindings().chatMessages.filter((message) => message.role === "assistant")).toHaveLength(0);
    expect(useToastStore().toasts).toHaveLength(0);

    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain(AI_APP_LIMIT_NOTE);
    expect(wrapper.get("textarea").attributes("disabled")).toBeDefined();
    expect(wrapper.get('button[aria-label="Skicka"]').attributes("disabled")).toBeDefined();

    await bindings().sendChatMessage("Igen");
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
    wrapper.unmount();
  });

  it("shows the note inline when edit-ops answers 429 user_share and blocks the next request", async () => {
    vi.mocked(apiFetch).mockRejectedValue(limitRefusal("user_share", AI_USER_LIMIT_NOTE));
    const { wrapper, bindings } = mountPanel();

    await bindings().requestEditOps("Gör om");

    expect(bindings().aiBlockedNote).toBe(AI_USER_LIMIT_NOTE);
    expect(bindings().editOpsRequestError).toBeNull();
    expect(useToastStore().toasts).toHaveLength(0);
    expect(aiDailyLimitReached.value).toBe(true);

    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain(AI_USER_LIMIT_NOTE);

    await bindings().requestEditOps("Igen");
    expect(apiFetch).toHaveBeenCalledTimes(1);
    wrapper.unmount();
  });

  it("keeps a plain edit-ops failure in the error surface and leaves the AI control enabled", async () => {
    vi.mocked(apiFetch).mockRejectedValue(
      new ApiError({ code: "INTERNAL_ERROR", message: "Något gick fel", status: 500 }),
    );
    const { wrapper, bindings } = mountPanel();

    await bindings().requestEditOps("Gör om");

    expect(bindings().editOpsRequestError).toBe("Något gick fel");
    expect(bindings().aiBlockedNote).toBeNull();
    wrapper.unmount();
  });
});
