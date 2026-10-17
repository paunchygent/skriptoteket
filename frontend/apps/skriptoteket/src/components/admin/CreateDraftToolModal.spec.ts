import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";

import CreateDraftToolModal from "./CreateDraftToolModal.vue";

function mountModal(isSubmitting = false) {
  return mount(CreateDraftToolModal, {
    props: {
      isOpen: true,
      title: "Mitt verktyg",
      summary: "",
      error: null,
      isSubmitting,
    },
    global: { stubs: { Teleport: true } },
  });
}

const attachedWrappers: ReturnType<typeof mount>[] = [];

afterEach(() => {
  attachedWrappers.forEach((wrapper) => wrapper.unmount());
  attachedWrappers.length = 0;
  document.body.replaceChildren();
});

function mountAttachedModal(isOpen = false) {
  const opener = document.createElement("button");
  opener.textContent = "Nytt verktyg";
  document.body.append(opener);
  opener.focus();
  const wrapper = mount(CreateDraftToolModal, {
    attachTo: document.body,
    props: { isOpen, title: "Mitt verktyg", summary: "", error: null, isSubmitting: false },
    global: { stubs: { Teleport: true } },
  });
  attachedWrappers.push(wrapper);
  return { opener, wrapper };
}

function pressKey(target: EventTarget, key: string, shiftKey = false) {
  const event = new KeyboardEvent("keydown", { key, shiftKey, bubbles: true, cancelable: true });
  target.dispatchEvent(event);
  return event;
}

describe("CreateDraftToolModal focus", () => {
  it("focuses the title even when mounted open", async () => {
    const { wrapper } = mountAttachedModal(true);
    await nextTick();
    expect(document.activeElement).toBe(wrapper.get("input").element);
  });

  it("contains Tab and Shift+Tab and still dismisses if focus reaches the background", async () => {
    const { opener, wrapper } = mountAttachedModal();
    await wrapper.setProps({ isOpen: true });
    await nextTick();
    const close = wrapper.get<HTMLButtonElement>('button[aria-label="Stäng"]').element;
    const create = wrapper.findAll<HTMLButtonElement>("button").find((button) => button.text() === "Skapa")!.element;
    create.focus();
    const forward = pressKey(create, "Tab");
    expect.soft(forward.defaultPrevented).toBe(true);
    expect.soft(document.activeElement).toBe(close);
    close.focus();
    const backward = pressKey(close, "Tab", true);
    expect.soft(backward.defaultPrevented).toBe(true);
    expect.soft(document.activeElement).toBe(create);

    // jsdom does not move focus for an unhandled Tab. Put focus behind the
    // dialog explicitly to reproduce the reachable pre-repair failure state.
    opener.focus();
    pressKey(opener, "Escape");
    await nextTick();
    expect.soft(wrapper.emitted("close")).toEqual([[]]);
    expect.soft(wrapper.emitted("submit")).toBeUndefined();
  });

  it("keeps keyboard focus inside while every form control is disabled", async () => {
    const { opener, wrapper } = mountAttachedModal();
    await wrapper.setProps({ isOpen: true, isSubmitting: true });
    await nextTick();
    const dialog = wrapper.get('[role="dialog"]').element;
    expect.soft(dialog.contains(document.activeElement)).toBe(true);
    opener.focus();
    const tab = pressKey(opener, "Tab");
    expect(tab.defaultPrevented).toBe(true);
    expect(dialog.contains(document.activeElement)).toBe(true);
    pressKey(document.activeElement!, "Escape");
    await nextTick();
    expect(wrapper.emitted("close")).toEqual([[]]);
  });

  it.each(["Avbryt", "Escape", "Skapa"])("returns focus after %s and supports reopening", async (action) => {
    const { opener, wrapper } = mountAttachedModal();
    for (let cycle = 1; cycle <= 2; cycle += 1) {
      opener.focus();
      await wrapper.setProps({ isOpen: true });
      await nextTick();
      expect(document.activeElement).toBe(wrapper.get("input").element);
      if (action === "Escape") {
        pressKey(document.activeElement!, "Escape");
        await nextTick();
      } else {
        await wrapper.findAll("button").find((button) => button.text() === action)!.trigger("click");
      }
      expect(wrapper.emitted(action === "Skapa" ? "submit" : "close")).toHaveLength(cycle);
      // The parent closes the modal after cancellation or successful creation.
      await wrapper.setProps({ isOpen: false });
      await nextTick();
      expect(document.activeElement).toBe(opener);
      pressKey(opener, "Escape");
      await nextTick();
      expect(wrapper.emitted(action === "Skapa" ? "submit" : "close")).toHaveLength(cycle);
    }
  });
});

describe("CreateDraftToolModal close action", () => {
  it("closes without submitting through the named icon action", async () => {
    const wrapper = mountModal();

    await wrapper.get('button[aria-label="Stäng"]').trigger("click");

    expect(wrapper.emitted("close")).toEqual([[]]);
    expect(wrapper.emitted("submit")).toBeUndefined();
    wrapper.unmount();
  });

  it("blocks the close action while creating and restores it afterwards", async () => {
    const wrapper = mountModal(true);
    const close = wrapper.get('button[aria-label="Stäng"]');

    expect(close.attributes("disabled")).toBeDefined();
    await close.trigger("click");
    expect(wrapper.emitted("close")).toBeUndefined();

    await wrapper.setProps({ isSubmitting: false });
    const restoredClose = wrapper.get('button[aria-label="Stäng"]');
    expect(restoredClose.attributes("disabled")).toBeUndefined();
    await restoredClose.trigger("click");
    expect(wrapper.emitted("close")).toEqual([[]]);
    wrapper.unmount();
  });
});
