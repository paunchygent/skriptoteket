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
  aiDailyLimitFor,
  markAiDailyLimit,
  resetAiDailyLimitForTests,
} from "../../composables/aiDailyLimit";
import type { AiDailyLimit } from "../../composables/aiDailyLimit";
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

function limitRefusal(limit: AiDailyLimit, message: string): ApiError {
  return new ApiError({
    code: "AI_DAILY_LIMIT_REACHED",
    message,
    status: 429,
    details: { limit },
  });
}

function limitResponse(limit: AiDailyLimit, message: string): Response {
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
    expect(aiDailyLimitFor("full").reached.value).toBe(true);

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

function internalError(): ApiError {
  return new ApiError({ code: "INTERNAL_ERROR", message: "Något gick fel", status: 500 });
}

function serverFailureResponse(): Response {
  return mockJsonResponse(
    { error: { code: "INTERNAL_ERROR", message: "Något gick fel", details: null } },
    500,
  );
}

describe("ScriptEditorAiPanel allowance scope", () => {
  it.each(["pool", "user_share"] as const)(
    "a full-allowance %s refusal from chat blocks chat and edit-ops but not completion or exam AI",
    async (limit) => {
      globalThis.fetch = vi.fn().mockResolvedValue(limitResponse(limit, "refused"));
      vi.mocked(apiFetch).mockRejectedValue(internalError());
      const { wrapper, bindings } = mountPanel();

      await bindings().sendChatMessage("Hej");
      await bindings().requestEditOps("Gör om");

      expect(globalThis.fetch).toHaveBeenCalledTimes(1);
      expect(apiFetch).not.toHaveBeenCalled();
      expect(aiDailyLimitFor("full").reached.value).toBe(true);
      expect(aiDailyLimitFor("small").reached.value).toBe(false);
      expect(aiDailyLimitFor("small").note.value).toBeNull();
      wrapper.unmount();
    },
  );

  it.each(["pool", "user_share"] as const)(
    "a full-allowance %s refusal from edit-ops blocks edit-ops and chat but not completion or exam AI",
    async (limit) => {
      globalThis.fetch = vi.fn().mockResolvedValue(serverFailureResponse());
      vi.mocked(apiFetch).mockRejectedValue(limitRefusal(limit, "refused"));
      const { wrapper, bindings } = mountPanel();

      await bindings().requestEditOps("Gör om");
      await bindings().sendChatMessage("Hej");

      expect(apiFetch).toHaveBeenCalledTimes(1);
      expect(globalThis.fetch).not.toHaveBeenCalled();
      expect(aiDailyLimitFor("small").reached.value).toBe(false);
      wrapper.unmount();
    },
  );

  it.each(["pool", "user_share"] as const)(
    "a small-allowance %s refusal leaves chat and edit-ops able to request",
    async (limit) => {
      markAiDailyLimit("small", limit);
      globalThis.fetch = vi.fn().mockResolvedValue(serverFailureResponse());
      vi.mocked(apiFetch).mockRejectedValue(internalError());
      const { wrapper, bindings } = mountPanel();

      expect(bindings().aiBlockedNote).toBeNull();
      await bindings().sendChatMessage("Hej");
      await bindings().requestEditOps("Gör om");

      expect(globalThis.fetch).toHaveBeenCalledTimes(1);
      expect(apiFetch).toHaveBeenCalledTimes(1);
      expect(bindings().aiBlockedNote).toBeNull();
      wrapper.unmount();
    },
  );

  it("a usd_ceiling refusal from the small allowance blocks chat and edit-ops too", async () => {
    markAiDailyLimit("small", "usd_ceiling");
    globalThis.fetch = vi.fn().mockResolvedValue(serverFailureResponse());
    const { wrapper, bindings } = mountPanel();

    await bindings().sendChatMessage("Hej");
    await bindings().requestEditOps("Gör om");

    expect(globalThis.fetch).not.toHaveBeenCalled();
    expect(apiFetch).not.toHaveBeenCalled();
    expect(bindings().aiBlockedNote).toBe(AI_APP_LIMIT_NOTE);
    wrapper.unmount();
  });

  it("a usd_ceiling refusal from chat blocks the small allowance too", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(limitResponse("usd_ceiling", AI_APP_LIMIT_NOTE));
    const { wrapper, bindings } = mountPanel();

    await bindings().sendChatMessage("Hej");

    expect(aiDailyLimitFor("full").reached.value).toBe(true);
    expect(aiDailyLimitFor("small").reached.value).toBe(true);
    expect(aiDailyLimitFor("small").note.value).toBe(AI_APP_LIMIT_NOTE);
    wrapper.unmount();
  });

  it("a busy answer from chat or edit-ops latches neither allowance", async () => {
    const busy = {
      error: { code: "AI_TRY_AGAIN", message: "Försök igen om en stund.", details: { retry_after_seconds: 5 } },
    };
    globalThis.fetch = vi.fn().mockResolvedValue(mockJsonResponse(busy, 429));
    vi.mocked(apiFetch).mockRejectedValue(
      new ApiError({ code: "AI_TRY_AGAIN", message: "Försök igen om en stund.", status: 429 }),
    );
    const { wrapper, bindings } = mountPanel();

    await bindings().sendChatMessage("Hej");
    await bindings().requestEditOps("Gör om");

    expect(aiDailyLimitFor("full").reached.value).toBe(false);
    expect(aiDailyLimitFor("small").reached.value).toBe(false);
    expect(useToastStore().toasts).toHaveLength(0);
    wrapper.unmount();
  });
});
