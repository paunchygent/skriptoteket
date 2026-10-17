import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { afterEach, describe, expect, it } from "vitest";

import ReagentPrepChefSdsModal from "./ReagentPrepChefSdsModal.vue";

const wrappers: ReturnType<typeof mount>[] = [];

afterEach(() => {
  wrappers.forEach((wrapper) => wrapper.unmount());
  wrappers.length = 0;
  document.body.replaceChildren();
});

describe("ReagentPrepChefSdsModal", () => {
  it("forwards the shared close action without treating content clicks as dismissal", async () => {
    const wrapper = mount(ReagentPrepChefSdsModal, {
      props: { isOpen: true, title: "SDS: NaCl", markdown: "Säkerhetsdata" },
      global: { stubs: { teleport: true } },
    });
    wrappers.push(wrapper);

    await wrapper.get("h2").trigger("click");
    expect(wrapper.emitted("close")).toBeUndefined();

    await wrapper.get('button[aria-label="Stäng SDS"]').trigger("click");
    expect(wrapper.emitted("close")).toHaveLength(1);

    await wrapper.get('[role="dialog"]').trigger("click");
    expect(wrapper.emitted("close")).toHaveLength(1);

    wrapper.get('[role="dialog"]').element.parentElement!.click();
    await nextTick();
    expect(wrapper.emitted("close")).toHaveLength(2);
  });

  it("focuses an initially open dialog and restores each opener across repeated openings", async () => {
    const opener = document.createElement("button");
    opener.textContent = "Öppna SDS";
    document.body.append(opener);
    opener.focus();
    const wrapper = mount(ReagentPrepChefSdsModal, {
      props: { isOpen: true, title: "SDS: NaCl", markdown: "Säkerhetsdata" },
      attachTo: document.body,
      global: { stubs: { teleport: true } },
    });
    wrappers.push(wrapper);
    await nextTick();
    expect.soft(wrapper.get('[role="dialog"]').element.contains(document.activeElement)).toBe(true);
    await wrapper.setProps({ isOpen: false });
    await nextTick();
    expect.soft(document.activeElement).toBe(opener);

    const secondOpener = document.createElement("button");
    secondOpener.textContent = "Öppna annan SDS";
    document.body.append(secondOpener);
    secondOpener.focus();
    await wrapper.setProps({ isOpen: true });
    await nextTick();
    expect.soft(wrapper.get('[role="dialog"]').element.contains(document.activeElement)).toBe(true);
    await wrapper.get('button[aria-label="Stäng SDS"]').trigger("click");
    expect.soft(wrapper.emitted("close")).toHaveLength(1);
    await wrapper.setProps({ isOpen: false });
    await nextTick();
    expect.soft(document.activeElement).toBe(secondOpener);
    secondOpener.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    await nextTick();
    expect.soft(wrapper.emitted("close")).toHaveLength(1);
  });

  it("names the dialog from its visible title and returns focus after Escape dismissal", async () => {
    const opener = document.createElement("button");
    opener.textContent = "Öppna SDS";
    document.body.appendChild(opener);
    opener.focus();

    const wrapper = mount(ReagentPrepChefSdsModal, {
      props: {
        isOpen: false,
        title: "SDS: NaCl",
        markdown: "Säkerhetsdata",
        pdfUrl: "https://example.test/sds.pdf",
      },
      attachTo: document.body,
      global: { stubs: { teleport: true } },
    });
    wrappers.push(wrapper);
    await wrapper.setProps({ isOpen: true });
    await nextTick();

    const dialog = wrapper.get('[role="dialog"]');
    const heading = wrapper.get("h2");
    const labelId = dialog.attributes("aria-labelledby");
    expect.soft(dialog.attributes("aria-modal")).toBe("true");
    expect.soft(labelId).toBeTruthy();
    expect.soft(heading.attributes("id")).toBe(labelId);
    expect.soft(document.getElementById(labelId ?? "")).toBe(heading.element);

    expect.soft(dialog.element.contains(document.activeElement)).toBe(true);

    const focusable = Array.from(dialog.element.querySelectorAll<HTMLElement>(
      'button, a[href], input, select, textarea, [tabindex="0"]',
    ));
    const first = focusable[0]!;
    const last = focusable[focusable.length - 1]!;
    last.focus();
    const forwardTab = new KeyboardEvent("keydown", { key: "Tab", bubbles: true, cancelable: true });
    last.dispatchEvent(forwardTab);
    await nextTick();
    expect.soft(forwardTab.defaultPrevented).toBe(true);
    expect.soft(document.activeElement).toBe(first);

    first.focus();
    const reverseTab = new KeyboardEvent("keydown", { key: "Tab", shiftKey: true, bubbles: true, cancelable: true });
    first.dispatchEvent(reverseTab);
    await nextTick();
    expect.soft(reverseTab.defaultPrevented).toBe(true);
    expect.soft(document.activeElement).toBe(last);

    wrapper.get<HTMLButtonElement>('button[aria-label="Stäng SDS"]').element.focus();
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    await nextTick();
    expect.soft(wrapper.emitted("close")).toHaveLength(1);

    await wrapper.setProps({ isOpen: false });
    expect.soft(document.activeElement).toBe(opener);
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    await nextTick();
    expect.soft(wrapper.emitted("close")).toHaveLength(1);
  });
});
