import { describe, expect, it } from "vitest";
import { nextTick } from "vue";

import { mountWithContext } from "../../test/utils";
import ChatDrawer from "./ChatDrawer.vue";

describe("ChatDrawer", () => {
  it("keeps draft on edit-ops request and clears only when clearDraftToken changes", async () => {
    const wrapper = mountWithContext(ChatDrawer, {
      props: {
        variant: "column",
        isOpen: true,
        isCollapsed: false,
        messages: [],
        isStreaming: false,
        isEditOpsLoading: false,
        disabledMessage: null,
        error: null,
        clearDraftToken: 0,
      },
    });

    const textarea = wrapper.find("textarea");
    await textarea.setValue("Fixa en bugg");
    await nextTick();

    const editButton = wrapper
      .findAll("button")
      .find((button) => button.text().includes("Edit"));

    expect(editButton, "Missing 'Edit' toggle").toBeTruthy();

    await editButton!.trigger("click");
    await nextTick();
    expect(textarea.element.value).toBe("Fixa en bugg");

    const sendButton = wrapper.find('button[aria-label="Föreslå ändringar"]');
    expect(sendButton.exists(), "Missing edit-mode send button").toBe(true);

    await sendButton.trigger("click");
    expect(textarea.element.value).toBe("Fixa en bugg");
    expect(wrapper.emitted("requestEditOps")?.[0]).toEqual(["Fixa en bugg"]);

    await wrapper.setProps({ clearDraftToken: 1 });
    await nextTick();
    expect(wrapper.find("textarea").element.value).toBe("");
  });

  it("shows a slow-request hint for edit-ops", () => {
    const wrapper = mountWithContext(ChatDrawer, {
      props: {
        variant: "column",
        isOpen: true,
        isCollapsed: false,
        messages: [],
        isStreaming: false,
        isEditOpsLoading: true,
        editOpsIsSlow: true,
        disabledMessage: null,
        error: null,
        clearDraftToken: 0,
      },
    });

    expect(wrapper.text()).toContain("Skapar förslag...");
    expect(wrapper.text()).toContain("Tar lite längre tid");
  });

  it("renders a failed assistant state with correlation-id even when content is empty", async () => {
    const wrapper = mountWithContext(ChatDrawer, {
      props: {
        variant: "column",
        isOpen: true,
        isCollapsed: false,
        messages: [
          {
            id: "user-1",
            role: "user",
            content: "Hej",
            createdAt: "2025-01-01T00:00:00Z",
            status: "complete",
          },
          {
            id: "assistant-1",
            role: "assistant",
            content: "",
            createdAt: "2025-01-01T00:00:01Z",
            status: "failed",
            correlationId: "corr-123",
          },
        ],
        isStreaming: false,
        isEditOpsLoading: false,
        disabledMessage: null,
        error: null,
        clearDraftToken: 0,
      },
    });

    expect(wrapper.text()).toContain("Misslyckades");
    expect(wrapper.text()).toContain("Misslyckades. Försök igen.");

    const debugButton = wrapper.find('button[aria-label="Visa correlation-id"]');
    expect(debugButton.exists()).toBe(true);

    await debugButton.trigger("click");
    await nextTick();

    expect(wrapper.text()).toContain("correlation-id: corr-123");
  });

  it("renders a remote fallback prompt and emits actions", async () => {
    const wrapper = mountWithContext(ChatDrawer, {
      props: {
        variant: "column",
        isOpen: true,
        isCollapsed: false,
        messages: [],
        isStreaming: false,
        isEditOpsLoading: false,
        disabledMessage: null,
        error: null,
        clearDraftToken: 0,
        remoteFallbackPrompt: {
          source: "chat",
          message: "Aktivera externa AI-API:er (OpenAI) för att fortsätta.",
        },
      },
    });

    const prompt = wrapper.find("[data-editor-remote-fallback-prompt]");
    expect(prompt.exists()).toBe(true);

    const allowButton = prompt
      .findAll("button")
      .find((button) => button.text().includes("Aktivera"));
    expect(allowButton, "Missing 'Aktivera' button").toBeTruthy();

    await allowButton!.trigger("click");
    expect(wrapper.emitted("allowRemoteFallbackPrompt")).toBeTruthy();

    const denyButton = prompt
      .findAll("button")
      .find((button) => button.text().includes("Stäng av"));
    expect(denyButton, "Missing 'Stäng av' button").toBeTruthy();

    await denyButton!.trigger("click");
    expect(wrapper.emitted("denyRemoteFallbackPrompt")).toBeTruthy();

    const dismissButton = prompt.find('button[aria-label="Stäng"]');
    expect(dismissButton.exists()).toBe(true);
    await dismissButton.trigger("click");
    expect(wrapper.emitted("dismissRemoteFallbackPrompt")).toBeTruthy();
  });
});
