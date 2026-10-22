import type { DOMWrapper, VueWrapper } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { nextTick } from "vue";

import { mountWithContext } from "../../test/utils";
import { AI_ADMIN_ONLY_NOTE } from "../../composables/useAiAccess";
import { SystemMessage } from "../ui";
import { UiGlyph } from "../ui/shared";
import ChatComposer from "./ChatComposer.vue";
import ChatDrawer from "./ChatDrawer.vue";

function findNotes(wrapper: VueWrapper): DOMWrapper<Element>[] {
  return wrapper
    .findAll("p, small, span")
    .filter((node) => node.text().trim() === AI_ADMIN_ONLY_NOTE);
}

describe("ChatDrawer", () => {
  it("keeps the assistant rail control named and its glyph decorative across collapse", async () => {
    const wrapper = mountWithContext(ChatDrawer, {
      props: {
        variant: "column",
        isOpen: true,
        isCollapsed: false,
        messages: [],
        isStreaming: false,
        isEditOpsLoading: false,
        error: null,
      },
    });
    const collapse = wrapper.get('button[aria-label="Minimera kodassistenten"]');
    const glyph = collapse.getComponent(UiGlyph);
    expect(glyph.props("meaning")).toBe("ai-assist");
    expect(glyph.get("svg").attributes("aria-hidden")).toBe("true");
    expect(glyph.attributes("aria-label")).toBeUndefined();
    expect(glyph.attributes("role")).not.toBe("img");
    expect(collapse.attributes("aria-expanded")).toBe("true");
    await collapse.trigger("click");
    expect(wrapper.emitted("toggleCollapse")).toEqual([[]]);
    expect(wrapper.emitted("close")).toBeUndefined();
    await wrapper.setProps({ isCollapsed: true });
    const expand = wrapper.get('button[aria-label="Expandera kodassistenten"]');
    expect(expand.element).toBe(collapse.element);
    expect(expand.getComponent(UiGlyph).element).toBe(glyph.element);
    expect(expand.attributes("aria-expanded")).toBe("false");
    await expand.trigger("click");
    expect(wrapper.emitted("toggleCollapse")).toEqual([[], []]);
    wrapper.unmount();
  });
  it.each([
    ["noticeMessage", "clearNotice", "Notice", "status", "polite"],
    ["error", "clearError", "Chat failed", "alert", "assertive"],
    ["editOpsError", "clearEditOpsError", "Edit failed", "alert", "assertive"],
    ["editOpsDisabledMessage", "clearEditOpsDisabled", "Edit disabled", "status", "polite"],
  ] as const)("dismisses %s through its clear handler exactly once", async (prop, event, text, role, live) => {
    const wrapper = mountWithContext(ChatDrawer, {
      props: {
        variant: "column",
        isOpen: true,
        isCollapsed: false,
        messages: [],
        isStreaming: false,
        isEditOpsLoading: false,
        noticeMessage: "Notice",
        noticeVariant: "warning",
        error: "Chat failed",
        editOpsError: "Edit failed",
        editOpsDisabledMessage: "Edit disabled",
      },
    });

    const message = wrapper.findAllComponents(SystemMessage).find((item) => item.text().includes(text));
    expect(message, `Missing ${prop} message`).toBeDefined();
    expect(message!.attributes()).toMatchObject({ role, "aria-live": live, "aria-atomic": "true" });
    await message!.get('button[aria-label="Stäng"]').trigger("click");

    for (const clearEvent of ["clearNotice", "clearError", "clearEditOpsError", "clearEditOpsDisabled"]) {
      expect(wrapper.emitted(clearEvent)).toEqual(clearEvent === event ? [[]] : undefined);
    }
    await wrapper.setProps({ [prop]: null });
    expect(wrapper.findAllComponents(SystemMessage).some((item) => item.text().includes(text))).toBe(false);
    wrapper.unmount();
  });

  it("keeps draft on edit-ops request and clears only when clearDraftToken changes", async () => {
    const wrapper = mountWithContext(ChatDrawer, {
      props: {
        variant: "column",
        isOpen: true,
        isCollapsed: false,
        messages: [],
        isStreaming: false,
        isEditOpsLoading: false,
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

  it("forwards the AI admin-only note through to the composer", () => {
    const wrapper = mountWithContext(ChatDrawer, {
      props: {
        variant: "column",
        isOpen: true,
        isCollapsed: false,
        messages: [],
        isStreaming: false,
        isEditOpsLoading: false,
        error: null,
        aiBlockedNote: AI_ADMIN_ONLY_NOTE,
      },
    });

    const composer = wrapper.findComponent(ChatComposer);
    expect(composer.props("aiBlockedNote")).toBe(AI_ADMIN_ONLY_NOTE);
    const notes = findNotes(wrapper);
    expect(notes).toHaveLength(1);
    expect(notes[0]!.text()).toBe(AI_ADMIN_ONLY_NOTE);
    wrapper.unmount();
  });
});
